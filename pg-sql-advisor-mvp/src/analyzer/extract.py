import re
from typing import Any, Dict, List
from datetime import datetime, timedelta
def _emit(node_id: int, kind: str, **kw) -> Dict[str, Any]:
    d = {"nodeId": node_id, "kind": kind}
    d.update({k: v for k, v in kw.items() if v is not None})
    return d

def _detect_time_cast_features(filter_text: str, relation: str, node_id: int) -> List[Dict[str, Any]]:
    feats: List[Dict[str, Any]] = []
    if not filter_text:
        return feats

    # 1) Любая функция на колонке времени → cast_prevents_index
    m_cast = re.search(r"to_char\(\s*\"?(\w+)\"?\s*,\s*'([^']+)'", filter_text, re.I)
    if m_cast:
        col = m_cast.group(1)
        fmt = m_cast.group(2)
        feats.append(_emit(node_id, "cast_prevents_index",
                           relation=relation, col=col, func="to_char", format=fmt))

    # 2) Диапазон в форме >= ... AND <= ... на том же выражении
    m_ge = re.search(r"to_char\(\s*\"?(\w+)\"?\s*,\s*'[^']+'\s*::text\)\s*>=\s*'([\d\-: ]+)'", filter_text, re.I)
    m_le = re.search(r"to_char\(\s*\"?(\w+)\"?\s*,\s*'[^']+'\s*::text\)\s*<=\s*'([\d\-: ]+)'", filter_text, re.I)
    if m_ge and m_le and m_ge.group(1) == m_le.group(1):
        col = m_ge.group(1)
        fromDate = m_ge.group(2).strip().split()[0]
        toDate   = m_le.group(2).strip().split()[0]
        # посчитаем верхнюю границу полуинтервала
        try:
            d2 = datetime.strptime(toDate, "%Y-%m-%d")
            toDate_next = (d2 + timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            toDate_next = None
        feats.append(_emit(node_id, "range_time_query",
                           relation=relation, timeCol=col,
                           fromDate=fromDate, toDate=toDate, toDate_next=toDate_next))
    return feats

def _walk(node: Dict[str, Any], acc: List[Dict[str, Any]]):
    ntype = node.get("Node Type")
    if ntype == "Seq Scan":
        rel = node.get("Relation Name")
        plan_rows = node.get("Plan Rows") or 0
        has_filter = "Filter" in node

        # seq_scan_big_table — только если есть фильтр ИЛИ таблица заметно велика
        if has_filter or plan_rows >= 100_000:
            acc.append(_emit(id(node) % 10_000_000, "seq_scan_big_table",
                             relation=rel, estRows=plan_rows,
                             selectivity=None if has_filter else 1.0))

        # разбор фильтра
        acc.extend(_detect_time_cast_features(node.get("Filter", ""), rel, id(node) % 10_000_000))

    for ch in node.get("Plans", []) or []:
        _walk(ch, acc)

def plan_to_features(plan_root: Dict[str, Any], sql: str) -> List[Dict[str, Any]]:
    feats: List[Dict[str, Any]] = []
    root = plan_root.get("Plan", plan_root)
    _walk(root, feats)
    return feats