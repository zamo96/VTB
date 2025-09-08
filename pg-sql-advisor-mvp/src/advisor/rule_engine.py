# src/advisor/rule_engine.py
from typing import Tuple, List, Dict, Any, Optional
from src.models import AdviseInput
from src.advisor.feature_normalizer import normalize_features
from collections import defaultdict
import re

_PH_RE = re.compile(r"\{(\w+)\}")

try:
    from pydantic import BaseModel as _PBase
except Exception:
    class _PBase:
        pass

DEFAULT_RULE_SCORES = {
    "R_CAST_PREVENTS_INDEX": 35,
    "R_RANGE_TIME_QUERY": 5,
}
# ----------------------- Универсальные хелперы -----------------------

def coerce_feature_dict(f: Any) -> Dict[str, Any]:
    """Приводим pydantic-модель Feature к dict. Если уже dict — возвращаем как есть."""
    if isinstance(f, dict):
        return f
    dump = getattr(f, "model_dump", None)   # pydantic v2
    if callable(dump):
        return dump()
    to_dict = getattr(f, "dict", None)      # pydantic v1
    if callable(to_dict):
        return to_dict()
    # крайний случай
    try:
        return dict(f)
    except Exception:
        return {"nodeId": getattr(f, "nodeId", None), "kind": getattr(f, "kind", None)}

def _to_dict(obj: Any) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, _PBase) and hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_none=True)
    if hasattr(obj, "dict"):
        try:
            return obj.dict(exclude_none=True)
        except TypeError:
            return obj.dict()
    try:
        import dataclasses
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
    except Exception:
        pass
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
    return {}

def _safe_name(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]+', '_', s or 'obj')

class _SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'

def _fmt_safe(tmpl: str, ph: Dict[str, Any]) -> str:
    return tmpl.format_map(_SafeDict(ph))

def _all_placeholders_present(template: str, ph: Dict[str, Any]) -> bool:
    if not template:
        return True
    for key in _PH_RE.findall(template):
        if ph.get(key) in (None, "", "None"):
            return False
    return True

# ----------------------- Построение плейсхолдеров -----------------------

def _build_placeholders(feat: Any) -> Dict[str, Any]:
    """Готовим словарь плейсхолдеров для шаблонов действий."""
    f = coerce_feature_dict(feat)
    ph: Dict[str, Any] = dict(f)  # копия

    schema = ph.get("schema")
    table  = ph.get("table")
    relation = ph.get("relation")

    if not relation and schema and table:
        ph["relation"] = f"{schema}.{table}"

    if schema and "schema_safe" not in ph:
        ph["schema_safe"] = f"\"{schema}\""
    if table and "table_safe" not in ph:
        ph["table_safe"] = f"\"{table}\""
    if ph.get("relation") and "relation_safe" not in ph:
        s = ph.get("schema") or (ph["relation"].split(".", 1)[0] if "." in ph["relation"] else None)
        t = ph.get("table")  or (ph["relation"].split(".", 1)[1] if "." in ph["relation"] else ph["relation"])
        if s and t:
            ph["relation_safe"] = f"\"{s}\".\"{t}\""

    # Вспомогательно: если есть timeCol, но нет col — используем его для шаблонов.
    if "timeCol" in ph and "col" not in ph:
        ph["col"] = ph["timeCol"]

    return ph

def _norm_cols(val) -> List[str]:
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
    return [str(val)]

def _flat_for_idx(cols: List[str]) -> str:
    names = []
    for c in cols:
        nm = c.split()[0]
        nm = nm.replace('"', '')
        names.append(nm)
    return "_".join(names) if names else "col"

# ----------------------- Сопоставление rule ↔ feature -----------------------

def _match_rule_on_feature(rule: dict, feat: Dict[str, Any]) -> bool:
    m = rule.get("match", {}) or {}
    need_feature = m.get("feature")
    if need_feature and feat.get("kind") != need_feature:
        return False

    # Доп. условия из rules (если появятся)
    if "selectivity_lt" in m:
        sel = feat.get("selectivity")
        try:
            if sel is None or not (float(sel) < float(m["selectivity_lt"])):
                return False
        except Exception:
            return False

    if m.get("mem_gt_workmem"):
        mem = feat.get("memEstMB")
        wm  = feat.get("workMemMB")
        try:
            if mem is None or wm is None or not (float(mem) > float(wm)):
                return False
        except Exception:
            return False

    if "mem_ratio_gt" in m:
        mem = feat.get("memEstMB")
        wm  = feat.get("workMemMB")
        try:
            if mem is None or wm in (None, 0) or not ((float(mem) / float(wm)) > float(m["mem_ratio_gt"])):
                return False
        except Exception:
            return False

    return True

# ----------------------- Рендер рекомендаций -----------------------

def _render_action(rule: dict, feat: Any) -> Dict[str, Any]:
    """Рендер ddl/alter/rewrite_sql_hint с мягкой подстановкой плейсхолдеров."""
    ph = _build_placeholders(feat)
    action = rule.get("action", {})
    rendered: Dict[str, Any] = {}

    # ddl_template
    ddl_tmpl = action.get("ddl_template")
    if ddl_tmpl and _all_placeholders_present(ddl_tmpl, ph):
        ddl = _fmt_safe(ddl_tmpl, ph)
        if "None" not in ddl and "{" not in ddl and "}" not in ddl:
            rendered["ddl"] = ddl

    # alter_template
    alter_tmpl = action.get("alter_template")
    if alter_tmpl and _all_placeholders_present(alter_tmpl, ph):
        alter = _fmt_safe(alter_tmpl, ph)
        if "None" not in alter and "{" not in alter and "}" not in alter:
            rendered["alter"] = alter

    # rewrite_sql_hint
    hint = action.get("rewrite_sql_hint")
    if hint:
        try:
            h = _fmt_safe(hint, ph)
        except Exception:
            h = hint
        rendered["rewrite_sql_hint"] = h

    return rendered

def _make_recommendation(rule: dict, feat: Any) -> Optional[Dict[str, Any]]:
    f = coerce_feature_dict(feat)
    ph = _build_placeholders(f)

    # Жёстких обязательных полей минимум, чтобы не терять валидные кейсы:
    required = []
    if rule["id"] == "R_CAST_PREVENTS_INDEX":
        required = ["relation_safe", "col"]
    elif rule["id"] == "R_RANGE_TIME_QUERY":
        # В правилах могут использовать {col}, а в feature у нас timeCol → прокинем в _build_placeholders
        required = ["relation_safe", "timeCol"]

    if any(ph.get(r) in (None, "", "None") for r in required):
        return None

    action = _render_action(rule, f)
    if not action.get("ddl") and not action.get("alter") and not action.get("rewrite_sql_hint"):
        return None

    rec = {
        "id": f"REC_{rule['id']}_{f.get('nodeId', 0)}",
        "rule_id": rule["id"],
        "type": rule.get("type", "generic"),
        "title": rule.get("title", "Recommendation"),
        "action": action,
        "expected_gain": rule.get("expected_gain", {"kind": "estimate", "source": "heuristic", "value": None}),
        "effort": rule.get("effort", "low"),
        "confidence": rule.get("confidence", "medium"),
        "evidence": [{
            "nodeId": f.get("nodeId"),
            "relation": f.get("relation"),
            "selectivity": f.get("selectivity"),
            "memEstMB": f.get("memEstMB"),
            "workMemMB": f.get("workMemMB")
        }]
    }
    return rec

def _dedup_recommendations(recs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set(); out = []
    for r in recs:
        act = r.get("action", {})
        ddl = act.get("ddl", "")
        alter = act.get("alter", "")
        sig = (r.get("rule_id"), r.get("title"), ddl, alter, (r.get("evidence") or [{}])[0].get("relation"))
        if sig in seen:
            continue
        seen.add(sig)
        out.append(r)
    return out

# ----------------------- Точка входа -----------------------

def apply_rules(payload, rules):
    # 1) приводим фичи к dict
    raw_feats: List[Dict[str, Any]] = []
    for feat in (payload.features or []):
        raw_feats.append(coerce_feature_dict(feat))

    feats = raw_feats  # без normalize_features, раз она у тебя сейчас шумит

    recommendations: List[Dict[str, Any]] = []
    contributions: List[Dict[str, Any]] = []

    # Чтобы не дублировать вклад по одному и тому же rule/фиче
    contrib_seen = set()

    for feat in feats:
        for rule in rules:
            match = rule.get("match", {}) or {}
            need_kind = match.get("feature")
            if need_kind and feat.get("kind") != need_kind:
                continue

            rec = _make_recommendation(rule, feat)
            if rec:
                recommendations.append(rec)

                # <<< ВКЛАД В РИСК ИЗ YAML >>>
                risk_cfg = rule.get("risk") or {}
                score = int(risk_cfg.get("base") or 0)
                drivers = risk_cfg.get("drivers") or ([feat.get("kind")] if feat.get("kind") else [])
                # Ключ уникальности — по rule_id и nodeId той фичи (чтобы не дублировать вклад)
                ckey = (rule.get("id"), feat.get("nodeId"))
                if score > 0 and ckey not in contrib_seen:
                    contributions.append({
                        "rule_id": rule.get("id"),
                        "score": score,
                        "drivers": drivers,
                    })
                    contrib_seen.add(ckey)

    # дедуп рекомендаций (как у тебя)
    clean = []
    seen = set()
    for r in recommendations:
        act = r.get("action", {})
        ddl = act.get("ddl", "")
        alter = act.get("alter", "")
        if any(x in (ddl or alter) for x in ("None", "{", "}")):
            continue
        sig = (r.get("rule_id"), r.get("title"), ddl, alter,
               (r.get("evidence") or [{}])[0].get("relation"))
        if sig in seen:
            continue
        seen.add(sig)
        clean.append(r)

    return clean, contributions