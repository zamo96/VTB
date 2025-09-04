from fastapi import FastAPI
from src.models import AdviseInput, AdviseResponse
from src.advisor.rule_engine import apply_rules
from src.advisor.risk_score import aggregate_score
from src.advisor.explainer import render_report
from src.advisor.rules_loader import load_rules
from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Any, List, Optional, Dict
from src.db.pg import run_sql_sync, explain_sql_sync
from src.analyzer.extract import plan_to_features

app = FastAPI(title="PG SQL Advisor (MVP)")
rules = load_rules()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/advise", response_model=AdviseResponse)
def advise(payload: AdviseInput):
    recs, contributions = apply_rules(payload, rules)
    risk = aggregate_score(contributions, payload)
    md   = render_report(recs, risk, payload)
    return {"risk": risk, "recommendations": recs, "explain_md": md}


# 1) Rule Engine: вход/выход
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
    format: str = "json"   # "json" | "text"

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

@app.post("/advise/sql")
async def advise_sql(payload: AdviseSqlIn):
    # 1) получаем EXPLAIN JSON из БД
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

    # 2) извлекаем features
    feats = plan_to_features(plan_root, payload.sql)

    # 3) прогоняем Advisor
    advise_in = AdviseInput(sqlText=payload.sql, features=feats, statsUsed=[], dbSettings={})
    recs, contributions = apply_rules(advise_in, rules)
    risk = aggregate_score(contributions, advise_in)
    md = render_report(recs, risk, advise_in)
    return {"risk": risk, "recommendations": recs, "explain_md": md, "features": feats, "plan": plan_root}

@app.post("/debug/rule_engine/apply", response_model=RuleEngineOut)
def debug_rule_engine(payload: RuleEngineIn):
    recs, contribs = apply_rules(payload, rules)
    return {"recommendations": recs, "risk_contributions": contribs}

# 2) Risk Score: вход/выход
class RiskAggregateIn(BaseModel):
    contributions: List[Dict[str, Any]]
    payload: AdviseInput

class RiskOut(BaseModel):
    risk: Dict[str, Any]

@app.post("/debug/risk_score/aggregate", response_model=RiskOut)
def debug_risk(payload: RiskAggregateIn):
    risk = aggregate_score(payload.contributions, payload.payload)
    return {"risk": risk}

# 3) Explainer: вход/выход
class ExplainerIn(BaseModel):
    recommendations: List[Dict[str, Any]]
    risk: Dict[str, Any]
    payload: AdviseInput   # нужен для контекста: features/plan/dbSettings/sqlText

class ExplainerOut(BaseModel):
    explain_md: str

@app.post("/debug/explainer/render", response_model=ExplainerOut)
def debug_explainer(payload: ExplainerIn):
    md = render_report(payload.recommendations, payload.risk, payload.payload)
    return {"explain_md": md}