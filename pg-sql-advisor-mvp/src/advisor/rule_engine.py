# src/advisor/rule_engine.py
from typing import Tuple, List, Dict, Any
from src.models import AdviseInput
# src/advisor/rule_engine.py
from src.advisor.feature_normalizer import normalize_features
import re

try:
    from pydantic import BaseModel as _PBase
except Exception:
    class _PBase:  # fallback если pydantic не импортируется здесь
        pass

def _to_dict(obj: Any) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    # pydantic v2
    if isinstance(obj, _PBase) and hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_none=True)
    # pydantic v1
    if hasattr(obj, "dict"):
        try:
            return obj.dict(exclude_none=True)
        except TypeError:
            return obj.dict()
    # dataclass
    try:
        import dataclasses
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
    except Exception:
        pass
    # generic
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
    return {}
# -------------------------------------------------------------------------

def _safe_name(s: str) -> str:
    # в имени индекса точка/кавычки недопустимы
    return re.sub(r'[^a-zA-Z0-9_]+', '_', s or 'obj')

class _SafeDict(dict):
    # не роняем движок, если в шаблоне есть необязательный плейсхолдер
    def __missing__(self, key):
        return '{' + key + '}'

def _fmt_safe(tmpl: str, ph: Dict[str, Any]) -> str:
    return tmpl.format_map(_SafeDict(ph))

def _build_placeholders(feat: Dict[str, Any]) -> Dict[str, Any]:
    feat = _to_dict(feat)
    ph: Dict[str, Any] = {k: v for k, v in feat.items() if v is not None}

    # table / schema / table_safe
    table = ph.get("relation") or ph.get("table")
    if table:
        tbl = table.replace('"', '')
        if '.' in tbl:
            schema, name = tbl.split('.', 1)
        else:
            schema, name = 'public', tbl
        ph.setdefault("schema", schema)
        ph.setdefault("table_name", name)
        ph.setdefault("table", f"{schema}.{name}")        # для DDL
        ph.setdefault("table_safe", _safe_name(f"{schema}_{name}"))  # для имени индекса
    else:
        ph.setdefault("schema", "public")
        ph.setdefault("table_name", "")
        ph.setdefault("table", "")
        ph.setdefault("table_safe", "tbl")

    # унифицируем списки
    if isinstance(ph.get("cols"), (list, tuple)):
        ph["cols"] = ", ".join(ph["cols"])
    if isinstance(ph.get("includeCols"), (list, tuple)):
        ph["includeCols"] = ", ".join(ph["includeCols"])
    if isinstance(ph.get("orderByCols"), (list, tuple)) and ph["orderByCols"] and isinstance(ph["orderByCols"][0], dict):
        ph["orderByCols"] = ", ".join(
            f'{c["name"]} {"DESC" if str(c.get("dir","")).upper().startswith("DESC") else "ASC"}'
            for c in ph["orderByCols"]
        )

    # общий col, если его нет, но есть timeCol/fkCol
    if "col" not in ph:
        for k in ("timeCol", "fkCol", "column"):
            if ph.get(k):
                ph["col"] = ph[k]
                break
    return ph
# --- end helpers ---

def _norm_cols(val) -> List[str]:
    """
    Нормализует список колонок:
      - "name" -> ["name"]
      - ["a","b"] -> ["a","b"]
      - [{"name":"ts","dir":"DESC"}] -> ["ts DESC"]
    """
    if val is None:
        return []
    if isinstance(val, str):
        return [val]
    if isinstance(val, (list, tuple)):
        out = []
        for v in val:
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, dict):
                nm = v.get("name") or v.get("col") or v.get("column")
                dr = v.get("dir") or v.get("direction")
                if nm:
                    out.append(f"{nm} {dr}".strip() if dr else nm)
        return out
    # всё остальное — строкой
    return [str(val)]

def _flat_for_idx(cols: List[str]) -> str:
    """Готовит часть имени индекса: 'a DESC, b' -> 'a_b'"""
    names = []
    for c in cols:
        nm = c.split()[0]  # убираем DESC/ASC
        nm = nm.replace('"', '')
        names.append(nm)
    return "_".join(names) if names else "col"

def _render_action(rule, feat):
    action = rule.get("action") or {}
    ph = _build_placeholders(feat)
    res = {}
    if "ddl_template" in action:
        res["ddl"] = _fmt_safe(action["ddl_template"], ph)
    if "alter" in action:
        res["alter"] = _fmt_safe(action["alter"], ph)
    if "rewrite_sql_hint" in action:
        res["rewrite_sql_hint"] = _fmt_safe(action["rewrite_sql_hint"], ph)
    return res

def _match_rule_on_feature(rule: dict, feat: Any) -> bool:
    m = rule.get("match", {}) or {}
    if m.get("feature") and m["feature"] != getattr(feat, "kind", None):
        return False
    # доп. условия
    if "selectivity_lt" in m:
        sel = getattr(feat, "selectivity", None)
        if sel is None or not (sel < float(m["selectivity_lt"])):
            return False
    if "mem_gt_workmem" in m and m["mem_gt_workmem"]:
        mem = getattr(feat, "memEstMB", None)
        wm = getattr(feat, "workMemMB", None)
        if mem is None or wm is None or not (mem > wm):
            return False
    if "mem_ratio_gt" in m:
        mem = getattr(feat, "memEstMB", None)
        wm = getattr(feat, "workMemMB", None)
        if mem is None or wm in (None, 0) or not ((mem / wm) > float(m["mem_ratio_gt"])):
            return False
    return True

def _make_recommendation(rule: dict, feat: Any) -> Dict[str, Any]:
    action = _render_action(rule, feat)
    rec = {
        "id": f"REC_{rule.get('id','R')}_{getattr(feat,'nodeId','X')}",
        "rule_id": rule.get("id", "RULE"),
        "type": rule.get("type", "generic"),
        "title": rule.get("title", "Recommendation"),
        "action": action,
        "expected_gain": {
            "kind": rule.get("expected_gain", {}).get("kind", "estimate"),
            "value": rule.get("expected_gain", {}).get("value", None),
            "source": rule.get("expected_gain", {}).get("source", "heuristic"),
        },
        "effort": rule.get("effort", "low"),
        "confidence": rule.get("confidence", "medium"),
        "evidence": [{
            "nodeId": getattr(feat, "nodeId", None),
            "relation": getattr(feat, "relation", None),
            "selectivity": getattr(feat, "selectivity", None),
            "memEstMB": getattr(feat, "memEstMB", None),
            "workMemMB": getattr(feat, "workMemMB", None),
        }]
    }
    return rec

def _dedup_recommendations(recs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set(); out = []
    for r in recs:
        action_key = tuple(sorted(r.get("action", {}).items()))
        key = (r.get("type"), r.get("rule_id"), action_key)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out

def apply_rules(payload: AdviseInput, rules: List[dict]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    # Pydantic → dict
    raw_feats = []
    for f in (payload.features or []):
        if isinstance(f, dict):
            raw_feats.append(f)
        else:
            # pydantic v1/v2 совместимость
            dump = getattr(f, "model_dump", None)
            raw_feats.append(dump() if dump else f.dict())
    #feats = normalize_features(raw_feats)
    feats = payload.features or []
    recommendations: List[Dict[str, Any]] = []
    contributions: List[Dict[str, Any]] = []

    for rule in rules:
        rule.setdefault("id", rule.get("id") or "RULE")
        matched = [f for f in feats if _match_rule_on_feature(rule, f)]
        if not matched:
            continue
        for feat in matched:
            recommendations.append(_make_recommendation(rule, feat))
        base = int(rule.get("risk", {}).get("base", 0))
        if base > 0:
            contributions.append({"rule_id": rule["id"], "score": base, "drivers": [rule.get("match", {}).get("feature","")]})

    return _dedup_recommendations(recommendations), contributions
