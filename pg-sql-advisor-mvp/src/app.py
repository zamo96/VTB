from fastapi import FastAPI, Query, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from src.db.pg import _conn_source  # вверху
from typing import Any, List, Optional, Dict, Set
import re
import logging

from src.models import AdviseInput, AdviseResponse
from src.advisor.rule_engine import apply_rules
from src.advisor.risk_score import aggregate_score
from src.advisor.explainer import render_report
from src.advisor.rules_loader import load_rules
from src.db.pg import run_sql_sync, explain_sql_sync
from src.db.pg import test_conn_with_params
from src.analyzer.extract import plan_to_features
from src.advisor.feature_normalizer import normalize_features
from src.presentation.formatter import format_adviser_human


app = FastAPI(title="PG SQL Advisor (MVP)")
rules = load_rules()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("pg_sql_advisor")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

@app.get("/health")
def health():
    return {"ok": True}


@app.post("/advise", response_model=AdviseResponse)
def advise(payload: AdviseInput):
    recs, contributions = apply_rules(payload, rules)
    risk = aggregate_score(contributions, payload)
    md = render_report(recs, risk, payload)
    return {"risk": risk, "recommendations": recs, "explain_md": md}


# ---------- Models для debug-эндпоинтов ----------
class RuleEngineIn(AdviseInput):
    pass


class RuleEngineOut(BaseModel):
    recommendations: List[Dict[str, Any]]
    risk_contributions: List[Dict[str, Any]]


class SqlRunIn(BaseModel):
    sql: str
    params: Optional[Dict[str, Any]] = None
    timeout_ms: int = 5000
    searchPath: Optional[str] = "public"
    allow_write: bool = False


class SqlExplainIn(BaseModel):
    sql: str
    analyze: bool = False
    buffers: bool = True
    verbose: bool = False
    settings: bool = False
    timeout_ms: int = 5000
    searchPath: Optional[str] = "public"
    format: str = "json"  # "json" | "text"


@app.post("/sql/run")
async def sql_run(payload: SqlRunIn):
    try:
        res = await run_in_threadpool(
            run_sql_sync,
            payload.sql,
            payload.params,
            timeout_ms=payload.timeout_ms,
            search_path=payload.searchPath,
            allow_write=payload.allow_write,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sql/explain")
async def sql_explain(payload: SqlExplainIn):
    try:
        res = await run_in_threadpool(
            explain_sql_sync,
            payload.sql,
            analyze=payload.analyze,
            buffers=payload.buffers,
            verbose=payload.verbose,
            settings=payload.settings,
            timeout_ms=payload.timeout_ms,
            search_path=payload.searchPath,
            fmt=payload.format,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class AdviseSqlIn(BaseModel):
    sql: str
    analyze: bool = False
    timeout_ms: int = 5000
    searchPath: Optional[str] = "public"


# ---------- Helpers: план → relations ----------
def _extract_relations(plan_root: dict) -> Set[str]:
    rels: Set[str] = set()

    def walk(n: dict):
        rn = n.get("Relation Name")
        if rn:
            schema = (n.get("Schema") or "public")
            rels.add(f"{schema}.{rn}" if "." not in rn else rn)
        for ch in (n.get("Plans") or []):
            walk(ch)

    walk(plan_root.get("Plan") or plan_root)
    return rels

def _fetch_pg_stats_sync(relations: Set[str]) -> List[Dict[str, Any]]:
    """
    Возвращает список элементов формата, ожидаемого AdviseInput.statsUsed:
    [
      { "table": "schema.table", "columns": ["col"], "n_distinct": -0.2, "correlation": 0.98 },
      ...
    ]
    Одна запись = одна колонка.
    """
    if not relations:
        return []

    out: List[Dict[str, Any]] = []

    for rel in relations:
        sch, tbl = rel.split(".", 1) if "." in rel else ("public", rel)
        q = """
        SELECT schemaname, tablename, attname, n_distinct, correlation
        FROM pg_stats
        WHERE schemaname = %s AND tablename = %s
        LIMIT 500
        """
        rows = run_sql_sync(q, (sch, tbl), timeout_ms=2000, search_path="public")
        if not rows:
            continue

        for r in rows:
            table_name = f"{r.get('schemaname')}.{r.get('tablename')}"
            out.append({
                "table": table_name,
                "columns": [r.get("attname")],        # <-- Список строк (ожидается моделью)
                "n_distinct": r.get("n_distinct"),
                "correlation": r.get("correlation"),
            })

    return out


# ---------- Helpers: настройки БД из pg_settings (нормализованные) ----------
def _kb_to_mb(val: str | int | float) -> int:
    try:
        kb = int(val)
        return max(1, kb // 1024)
    except Exception:
        return 0


def _normalize_pg_setting(name: str, setting: str, unit: Optional[str]) -> Any:
    lname = name.lower()

    # memory в MB
    if lname in {"work_mem", "effective_cache_size", "shared_buffers", "maintenance_work_mem"}:
        if unit and unit.lower() == "kb":
            return _kb_to_mb(setting)
        m = re.match(r"^\s*(\d+)\s*([kKmMgG][bB])?\s*$", str(setting))
        if m:
            num = int(m.group(1))
            suf = (m.group(2) or "").lower()
            if suf == "kb":
                return max(1, num // 1024)
            if suf in ("mb", ""):
                return num
            if suf == "gb":
                return num * 1024
        return _kb_to_mb(setting)

    if lname == "random_page_cost":
        try:
            return float(setting)
        except Exception:
            return 4.0

    if lname in {"enable_parallel", "jit"}:
        return str(setting).strip().lower() in {"on", "true", "1"}

    if lname == "max_parallel_workers_per_gather":
        try:
            return int(setting)
        except Exception:
            return 0

    return setting

def _fetch_db_settings_sync() -> dict:
    """
    Возвращает ключевые параметры БД в виде словаря, безопасно для любой версии PG.
    Используем current_setting(name, true), чтобы неизвестные GUC не падали, а давали NULL.
    """
    out = {}

    # Базовые параметры, которые есть практически всегда
    base_params = ["work_mem", "effective_cache_size", "random_page_cost"]

    # Параметры параллелизма, зависят от версии PG: берем то, что есть
    parallel_candidates = [
        "max_parallel_workers_per_gather",  # основной лимит паралл. воркеров на gather-операцию
        "force_parallel_mode",              # может быть on|off
        "parallel_leader_participation",    # on|off
        # Опционально, если хотите отслеживать конкретные enable_*:
        # "enable_parallel_append",
        # "enable_parallel_hash",
    ]

    # Читаем базовые
    for name in base_params:
        rows = run_sql_sync("SELECT current_setting(%s, true) AS v", (name,))
        if rows and isinstance(rows, list):
            val = rows[0].get("v") if isinstance(rows[0], dict) else (rows[0][0] if rows[0] else None)
            if val is not None:
                out[name] = val

    # Читаем параметры параллелизма (что найдется в текущей версии)
    for name in parallel_candidates:
        rows = run_sql_sync("SELECT current_setting(%s, true) AS v", (name,))
        if rows and isinstance(rows, list):
            val = rows[0].get("v") if isinstance(rows[0], dict) else (rows[0][0] if rows[0] else None)
            if val is not None:
                out[name] = val

    return out


# сразу после rules = load_rules()
rules = load_rules()
print(f"[boot] rules loaded: {len(rules)}")  # будет видно 0 или >0


@app.get("/debug/db_source")
def debug_db_source():
    src, val = _conn_source()
    # покажем и текущее окружение PG*
    pg_env = {k: os.getenv(k) for k in ["PGHOST","PGPORT","PGUSER","PGPASSWORD","PGDATABASE","PGSERVICE"] if os.getenv(k) is not None}
    return {"source": src, "value": val, "pg_env": pg_env}

@app.get("/debug/rules")
def debug_rules():
    return {
        "count": len(rules),
        "ids": [r.get("id") for r in rules],
        "first_rule": (rules[0] if rules else None)
    }

# ---------- Основной эндпойнт: анализ SQL ----------
@app.post("/advise/sql")
async def advise_sql(
    payload: AdviseSqlIn,
    out_format: str = Query("json", pattern="^(json|md)$"),
    verbosity: str = Query("short", pattern="^(short|full)$"),
    include_plan: bool = True,
    include_features: bool = True
):
    # 1) EXPLAIN JSON
    exp = await run_in_threadpool(
        explain_sql_sync,
        payload.sql,
        analyze=payload.analyze,
        buffers=True,
        verbose=False,
        settings=False,
        timeout_ms=payload.timeout_ms,
        search_path=payload.searchPath,
        fmt="json",
    )
    plan_list = exp.get("plan") or []
    if not plan_list:
        raise HTTPException(status_code=400, detail="Empty plan")
    plan_root = plan_list[0]

    # 2) features → normalize
    feats_raw = plan_to_features(plan_root, payload.sql)
    feats = normalize_features(feats_raw)

    # 3) доп. контекст: статистика и настройки БД
    rels = _extract_relations(plan_root)
    stats_used = await run_in_threadpool(_fetch_pg_stats_sync, rels)
    db_settings = await run_in_threadpool(_fetch_db_settings_sync)

    # 4) Advisor
    advise_in = AdviseInput(
        sqlText=payload.sql,
        features=feats,
        statsUsed=stats_used,
        dbSettings=db_settings
    )
    recs, contributions = apply_rules(advise_in, rules)
    risk = aggregate_score(contributions, advise_in)

    # 5) Представление
    if out_format == "md":
        text = format_adviser_human(
            {"risk": risk, "recommendations": recs},
            style="md", verbosity=verbosity
        )
        return {
            "text": text,
            "risk": risk,
            "recommendations": recs,
            **({"features": feats} if include_features else {}),
            **({"plan": plan_root} if include_plan else {})
        }

    # JSON по умолчанию
    md = render_report(recs, risk, advise_in)
    return {
        "risk": risk,
        "recommendations": recs,
        "explain_md": md,
        "dbSettings": db_settings,
        **({"features": feats} if include_features else {}),
        **({"plan": plan_root} if include_plan else {})
    }


# ---------- Debug endpoints ----------
@app.post("/debug/rule_engine/apply", response_model=RuleEngineOut)
def debug_rule_engine(payload: RuleEngineIn):
    recs, contribs = apply_rules(payload, rules)
    return {"recommendations": recs, "risk_contributions": contribs}


class RiskAggregateIn(BaseModel):
    contributions: List[Dict[str, Any]]
    payload: AdviseInput


class RiskOut(BaseModel):
    risk: Dict[str, Any]


@app.post("/debug/risk_score/aggregate", response_model=RiskOut)
def debug_risk(payload: RiskAggregateIn):
    risk = aggregate_score(payload.contributions, payload.payload)
    return {"risk": risk}


class ExplainerIn(BaseModel):
    recommendations: List[Dict[str, Any]]
    risk: Dict[str, Any]
    payload: AdviseInput  # нужен контекст


class ExplainerOut(BaseModel):
    explain_md: str


@app.post("/debug/explainer/render", response_model=ExplainerOut)
def debug_explainer(payload: ExplainerIn):
    md = render_report(payload.recommendations, payload.risk, payload.payload)
    return {"explain_md": md}

class DbTestInput(BaseModel):
    host: str
    port: int
    database: str
    user: str
    password: str


@app.post("/api/settings/db/test")
async def settings_db_test(payload: DbTestInput):
    try:
        logger.info(
            "DB test request: host=%s port=%s db=%s user=%s password=%s",
            payload.host, payload.port, payload.database, payload.user, "***" if payload.password else "",
        )
        res = await run_in_threadpool(
            test_conn_with_params,
            {
                "host": payload.host,
                "port": payload.port,
                "database": payload.database,
                "user": payload.user,
                "password": payload.password,
            },
        )
        logger.info(
            "DB test success: user=%s db=%s",
            res.get("current_user"), res.get("database"),
        )
        return res
    except Exception as e:
        logger.exception("DB test failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e))