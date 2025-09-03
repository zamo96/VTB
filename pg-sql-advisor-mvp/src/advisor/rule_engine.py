# src/advisor/rule_engine.py
from typing import Tuple, List, Dict, Any
from src.models import AdviseInput
import re

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

def _render_action(rule: dict, feat: Any) -> Dict[str, Any]:
    """
    Поддержка action.* в YAML:
      - ddl_template: str с плейсхолдерами
          {table}, {col}, {cols}, {cols_flat},
          {order_by_cols}, {order_by_cols_flat}, {include_cols}
      - alter: str
      - pre_sql: [строки] — префикс к DDL
      - context:
          table_from_feature: str (имя атрибута в feature)
          col_from_feature: str | cols_from_feature: str
          order_by_cols_from_feature: str
          include_cols_from_feature: str
          col_fallback: str | cols_fallback: [..]
          include_cols_fallback: [..]
          idx_template: "idx_{table}_{cols_flat}"
    """
    action = rule.get("action", {}) or {}
    ctx = action.get("context", {}) or {}

    # table
    table_attr = ctx.get("table_from_feature", "relation")
    table = getattr(feat, table_attr, None) or getattr(feat, "relation", None) or "public.unknown_table"
    table_plain = table.split(".")[-1]

    # основной список колонок (для {cols}, {cols_flat}, {col})
    cols = []
    if "cols_from_feature" in ctx:
        cols = _norm_cols(getattr(feat, ctx["cols_from_feature"], None))
    elif "col_from_feature" in ctx:
        cols = _norm_cols(getattr(feat, ctx["col_from_feature"], None))
    if not cols:
        fb = ctx.get("cols_fallback")
        if fb:
            cols = _norm_cols(fb)
        else:
            col_fb = ctx.get("col_fallback")
            cols = _norm_cols(col_fb) if col_fb else []

    # order by cols (отдельная группа)
    ob_cols = _norm_cols(getattr(feat, ctx.get("order_by_cols_from_feature", ""), None))

    # include cols
    include_cols = _norm_cols(getattr(feat, ctx.get("include_cols_from_feature", ""), None))
    if not include_cols:
        include_cols = _norm_cols(ctx.get("include_cols_fallback", []))

    # индексное имя
    idx_tpl = ctx.get("idx_template", "idx_{table}_{cols_flat}")
    cols_flat = _flat_for_idx(cols) if cols else (_flat_for_idx(ob_cols) if ob_cols else "col")
    ob_cols_flat = _flat_for_idx(ob_cols)
    idx = idx_tpl.format(table=table_plain, col=cols_flat, cols_flat=cols_flat, order_by_cols_flat=ob_cols_flat)

    # плейсхолдеры
    ph: Dict[str, str] = {
        "table": table,
        "col": cols[0] if cols else "",
        "cols": ", ".join(cols) if cols else "",
        "cols_flat": cols_flat,
        "order_by_cols": ", ".join(ob_cols) if ob_cols else "",
        "order_by_cols_flat": ob_cols_flat,
        "include_cols": ", ".join(include_cols) if include_cols else "",
        "idx": idx,
    }

    # alter
    if "alter" in action and action["alter"]:
        return {"alter": action["alter"]}

    # ddl (с возможным префиксом pre_sql)
    if "ddl_template" in action and action["ddl_template"]:
        ddl = action["ddl_template"].format(**ph)

        # если в шаблоне было INCLUDE({include_cols}), но список пуст — удалим пустую секцию
        if "{include_cols}" in action["ddl_template"] and not ph["include_cols"]:
            ddl = re.sub(r"\s*INCLUDE\(\s*\)", "", ddl, flags=re.IGNORECASE)

        pre = action.get("pre_sql") or []
        if pre:
            ddl = "; ".join([*pre, ddl])
        return {"ddl": ddl}

    return {}

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
