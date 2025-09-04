# src/advisor/explainer.py
from typing import List, Dict, Any, Optional
import re

# ---------- utils ----------

def _to_dict(obj: Any) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    try:
        if hasattr(obj, "model_dump"):  # pydantic v2
            return obj.model_dump(exclude_none=True)
        if hasattr(obj, "dict"):        # pydantic v1
            return obj.dict(exclude_none=True)
    except Exception:
        pass
    try:
        import dataclasses
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
    except Exception:
        pass
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
    return {}

class _SafeDict(dict):
    def __missing__(self, key):
        return "{"+key+"}"

def _fmt_with_ctx(txt: str, ctx: Dict[str, Any]) -> str:
    if not isinstance(txt, str):
        return txt
    return txt.format_map(_SafeDict(ctx))

def _human_severity(sev: str) -> str:
    s = (sev or "info").lower()
    return {
        "critical": "🛑 Critical",
        "high":     "🔴 High",
        "warning":  "🟠 Warning",
        "medium":   "🟠 Warning",
        "low":      "🟡 Low",
        "info":     "ℹ️ Info",
    }.get(s, s.title())

def _fmt_kv(label: str, val: Optional[str|int|float]) -> Optional[str]:
    if val is None or val == "":
        return None
    return f"{label}: {val}"

def _code_inline(s: str) -> str:
    return f"`{s}`"

def _code_block(s: str, lang: str="sql") -> str:
    return f"```{lang}\n{s}\n```"

def _extract_index_name(ddl: str) -> Optional[str]:
    m = re.search(r"CREATE\s+INDEX\s+(?:CONCURRENTLY\s+)?([A-Za-z0-9_\"\.]+)\s+ON", ddl, re.I)
    return m.group(1) if m else None

def _dedupe_index_recs(recs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for r in recs:
        act = (r.get("action") or {})
        ddl = (act.get("ddl") or "").strip().lower()
        key = (r.get("type"), ddl)
        if r.get("type") == "index" and ddl:
            if key in seen:
                continue
            seen.add(key)
        out.append(r)
    return out

def _ctx_by_node(payload) -> Dict[int, Dict[str, Any]]:
    ctx: Dict[int, Dict[str, Any]] = {}
    feats = getattr(payload, "features", None) or []
    for f in feats:
        d = _to_dict(f)
        nid = d.get("nodeId")
        if nid is None:
            continue
        ctx.setdefault(nid, {}).update({k: v for k, v in d.items() if v is not None})
    return ctx

def _sort_key(rec: Dict[str, Any]) -> tuple:
    kind_order = {"sql_rewrite": 0, "index": 1, "db_setting": 2, "generic": 3}
    effort_order = {"low": 0, "medium": 1, "high": 2}
    return (
        kind_order.get(rec.get("type", "generic"), 99),
        effort_order.get(rec.get("effort", "medium"), 1),
        -1 if rec.get("confidence") == "high" else (0 if rec.get("confidence") == "medium" else 1),
        rec.get("id", ""),
    )

# ---------- plan evidence ----------

def _walk_plan_nodes(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    if not plan:
        return out
    node = plan.get("Plan") or plan
    def dfs(n):
        out.append(n)
        for ch in n.get("Plans", []) or []:
            dfs(ch)
    dfs(node)
    return out

def _find_nodes_by_relation(plan: Dict[str, Any], relation: str) -> List[Dict[str, Any]]:
    if not plan or not relation:
        return []
    nodes = _walk_plan_nodes(plan)
    rel_low = relation.strip('"').split('.')[-1].lower()
    hits = []
    for n in nodes:
        rn = (n.get("Relation Name") or n.get("Alias") or "")
        if rn and rn.strip('"').split('.')[-1].lower() == rel_low:
            hits.append(n)
    return hits

def _render_plan_evidence(plan: Dict[str, Any], relation: Optional[str]) -> List[str]:
    if not plan or not relation:
        return []
    nodes = _find_nodes_by_relation(plan, relation)
    if not nodes:
        return []
    lines = ["  - Доказательства из плана:"]
    for n in nodes[:2]:  # первые 1–2 узла, чтобы не распухать
        parts = []
        for k in ("Node Type","Filter","Index Cond","Join Filter","Recheck Cond","Sort Key"):
            v = n.get(k)
            if v:
                if isinstance(v, list): v = ", ".join(map(str, v))
                parts.append(f"{k}: {v}")
        # строки/стоимость
        for k in ("Plan Rows","Actual Rows","Startup Cost","Total Cost"):
            v = n.get(k)
            if v is not None:
                parts.append(f"{k}: {v}")
        if parts:
            lines.append("    - " + " | ".join(parts))
    return lines

# ---------- rec rendering ----------

def _render_one_rec(r: Dict[str, Any], ctx_node: Dict[str, Any], full_plan: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    title = r.get("title") or "Recommendation"
    act = r.get("action") or {}
    exp = r.get("expected_gain") or {}
    ev  = r.get("evidence") or []

    # Заголовок
    lines.append(f"- {title}")

    # WHY
    why_blk: List[str] = []
    for e in ev:
        e = _to_dict(e)
        parts = [
            _fmt_kv("nodeId", e.get("nodeId") or ctx_node.get("nodeId")),
            _fmt_kv("relation", e.get("relation") or ctx_node.get("relation")),
            _fmt_kv("selectivity", e.get("selectivity") or ctx_node.get("selectivity")),
            _fmt_kv("memEstMB", e.get("memEstMB") or ctx_node.get("memEstMB")),
            _fmt_kv("workMemMB", e.get("workMemMB") or ctx_node.get("workMemMB")),
        ]
        facts = [p for p in parts if p]
        if facts:
            why_blk.append("    - " + "; ".join(facts))
    if not why_blk and ctx_node:
        parts = [
            _fmt_kv("relation", ctx_node.get("relation")),
            _fmt_kv("col", ctx_node.get("col") or ctx_node.get("timeCol")),
            _fmt_kv("estRows", ctx_node.get("estRows")),
        ]
        facts = [p for p in parts if p]
        if facts:
            why_blk.append("    - " + "; ".join(facts))
    if why_blk:
        lines.append("  - Почему:")
        lines.extend(why_blk)

    # WHAT
    # доформатируем шаблоны act с контекстом узла
    act_fmt = {k: _fmt_with_ctx(v, ctx_node) for k, v in act.items()}
    what_blk: List[str] = []
    if "rewrite_sql_hint" in act_fmt:
        what_blk.append(f"    - Переписать: {act_fmt['rewrite_sql_hint']}")
        # Отдельный код-блок с WHERE, если распознали даты/колонку
        tc = ctx_node.get("timeCol") or ctx_node.get("col")
        fd = ctx_node.get("fromDate")
        tn = ctx_node.get("toDate_next")
        if tc and fd and tn:
            rewritten_where = f"\"{tc}\" >= DATE '{fd}' AND \"{tc}\" < DATE '{tn}'"
            what_blk.append("    - Rewritten WHERE:")
            what_blk.append(_code_block(rewritten_where))
    if "ddl" in act_fmt:
        ddl = act_fmt["ddl"]
        what_blk.append(f"    - DDL: {_code_inline(ddl)}")
        idx_name = _extract_index_name(ddl)
        if idx_name:
            what_blk.append(f"      • rollback: {_code_inline(f'DROP INDEX CONCURRENTLY {idx_name};')}")
        what_blk.append("      • после создания: выполнить ANALYZE")
    if "alter" in act_fmt:
        alt = act_fmt["alter"]
        what_blk.append(f"    - ALTER/SET: {_code_inline(alt)}")
        if "work_mem" in alt:
            what_blk.append("      • rollback: `RESET work_mem;` (или закрыть транзакцию, если SET LOCAL)")
    if what_blk:
        lines.append("  - Что сделать:")
        lines.extend(what_blk)

    # HOW
    if exp:
        eff = []
        if exp.get("kind"): eff.append(f"тип: {exp['kind']}")
        if exp.get("source"): eff.append(f"оценка: {exp['source']}")
        if exp.get("value") is not None: eff.append(f"эффект: {exp['value']}")
        if eff:
            lines.append("  - Как это поможет: " + "; ".join(eff))

    # Plan evidence (по relation)
    pe = _render_plan_evidence(full_plan, ctx_node.get("relation"))
    if pe:
        lines.extend(pe)

    # meta
    tail: List[str] = []
    if r.get("effort"):
        tail.append(f"вложение: {r['effort']}")
    if r.get("confidence"):
        tail.append(f"уверенность: {r['confidence']}")
    if tail:
        lines.append("  - " + "; ".join(tail))

    return lines

# ---------- main ----------

def render_report(recs: List[Dict[str, Any]], risk: Dict[str, Any], payload) -> str:
    ctx_map = _ctx_by_node(payload)
    recs = _dedupe_index_recs(recs)
    recs = sorted(recs, key=_sort_key)
    plan = _to_dict(getattr(payload, "plan", None)) or _to_dict(getattr(payload, "plan_json", None)) or (_to_dict(payload).get("plan") or {})

    sev = _human_severity(risk.get("severity", "info"))
    score = risk.get("score", 0)
    drivers = risk.get("drivers") or []
    conf_fac = risk.get("confidence_factor")

    lines: List[str] = [
        "### Итог",
        f"- Риск: **{sev} ({score}/100)**",
        "- Драйверы: " + (", ".join(drivers) if drivers else "не выявлены"),
    ]
    if conf_fac is not None:
        lines.append(f"- Confidence factor: {conf_fac}")
    lines.append("")

    contribs = risk.get("risk_contributions") or []
    if contribs:
        lines.append("### Вклад правил в риск")
        for c in contribs:
            rid = c.get("rule_id") or "rule"
            sc  = c.get("score")
            drv = ", ".join(c.get("drivers", [])) if c.get("drivers") else ""
            extra = f" — {drv}" if drv else ""
            lines.append(f"- {rid}: +{sc}{extra}")
        lines.append("")

    if recs:
        lines.append("### Рекомендации (по приоритету)")
        for r in recs:
            node_id = None
            if r.get("evidence"):
                ev0 = _to_dict(r["evidence"][0])
                node_id = ev0.get("nodeId")
            ctx_node = ctx_map.get(node_id, {}) if node_id is not None else {}
            lines.extend(_render_one_rec(r, ctx_node, plan))
    else:
        lines.append("_Проблем не найдено._")

    # Общее примечание
    notes: List[str] = []
    if any((r.get("type") == "db_setting") for r in recs):
        notes.append("Настройки через `SET LOCAL` действуют в рамках текущей транзакции.")
    if notes:
        lines.append("")
        lines.append("### Примечания")
        for n in notes:
            lines.append(f"- {n}")

    return "\n".join(lines)
