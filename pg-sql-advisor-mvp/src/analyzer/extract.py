import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

MAIN_REL_RE = re.compile(
    r"""from\s+            # FROM
        (?:(?P<schema>"?[a-zA-Z0-9_]+"?)\.)?
        (?P<table>"?[a-zA-Z0-9_]+"?)      # table or "table"
    """,
    re.IGNORECASE | re.VERBOSE
)

# ↘️ Более гибкий паттерн: допускаем "col" и без кавычек, и 'fmt'::text
_TO_CHAR_COL_RE = re.compile(
    r"""to_char\(\s*("?)(?P<col>[a-zA-Z0-9_]+)\1\s*,\s*'(?P<fmt>[^']+)'\s*(?:::text)?\s*\)""",
    re.IGNORECASE | re.VERBOSE
)

# Даты вида 'YYYY-MM-DD'
_DATE_LIT_RE = re.compile(r"""'(?P<d>\d{4}-\d{2}-\d{2})'""")

# col % mod = eq
_MODULO_RE  = re.compile(r"""(?P<col>\w+)\s*%\s*(?P<mod>\d+)\s*=\s*(?P<eq>\d+)""")

def _safe_relation(n: Dict[str, Any]) -> Dict[str, str]:
    rel = n.get("Relation Name")
    schema = n.get("Schema") or "public"
    out = {}
    if rel:
        out["relation"] = f"{schema}.{rel}"
        out["schema"] = schema
        out["table"] = rel
        out["relation_safe"] = f"\"{schema}\".\"{rel}\""
        out["schema_safe"] = f"\"{schema}\""
        out["table_safe"] = f"\"{rel}\""
    return out

def _extract_dates_from_filter(filter_text: str) -> Optional[Dict[str, str]]:
    """
    Ищем две даты (>= и <=). Возвращаем fromDate/toDate; toDate_next будем считать позже.
    """
    ds = _DATE_LIT_RE.findall(filter_text or "")
    if len(ds) >= 2:
        fromDate, toDate = ds[0], ds[1]
        return {"fromDate": fromDate, "toDate": toDate}
    return None

def _extract_cast_prevents_index(node: Dict[str, Any], feats: List[Dict[str, Any]]):
    filt = node.get("Filter")
    if not filt:
        return
    m = _TO_CHAR_COL_RE.search(filt)
    if m:
        col = m.group("col")
        fmt = m.group("fmt")
        base = _safe_relation(node)
        if base:
            feats.append({
                "nodeId": id(node),
                "kind": "cast_prevents_index",
                "col": col,
                "func": "to_char",
                "format": fmt,
                **base,
            })
            # если есть две даты в фильтре — добьём feature диапазона
            dates = _extract_dates_from_filter(filt)
            if dates:
                feats.append({
                    "nodeId": id(node),
                    "kind": "range_time_query",
                    "timeCol": col,
                    **dates,
                    **base,
                })

def _extract_order_by_random(node: Dict[str, Any], feats: List[Dict[str, Any]]):
    if node.get("Node Type") in ("Sort", "Incremental Sort"):
        keys = node.get("Sort Key") or []
        for k in keys:
            if "random()" in str(k).lower():
                feats.append({
                    "nodeId": id(node),
                    "kind": "order_by_random",
                })

def _extract_modulo_filter(node: Dict[str, Any], feats: List[Dict[str, Any]]):
    # Ищем выражения с % не только в Filter
    for key in ("Filter", "Index Cond", "Recheck Cond", "Join Filter"):
        expr = node.get(key)
        if not expr:
            continue
        m = _MODULO_RE.search(expr)
        if m:
            feats.append({
                "nodeId": id(node),
                "kind": "modulo_filter",
                "col": m.group("col"),
                "mod": int(m.group("mod")),
                "eq": int(m.group("eq")),
                **_safe_relation(node),
            })
            return  # достаточно одной записи

def _walk(n: Dict[str, Any], feats: List[Dict[str, Any]]):
    # Пример общей фичи
    if n.get("Node Type") == "Seq Scan" and n.get("Relation Name"):
        feats.append({
            "nodeId": id(n),
            "kind": "seq_scan_big_table",
            **_safe_relation(n),
            "estRows": n.get("Plan Rows"),
        })

    # Специализированные извлечения
    _extract_cast_prevents_index(n, feats)
    _extract_order_by_random(n, feats)
    _extract_modulo_filter(n, feats)

    for ch in n.get("Plans", []) or []:
        _walk(ch, feats)

def _scan_sql_for_patterns(sql: str, feats: List[Dict[str, Any]], main_rel: Optional[Dict[str, str]]):
    # 1) modulo_filter в WHERE
    # простой, но рабочий детектор
    if _MODULO_RE.search(sql):
        base = {}
        if main_rel:
            base = {
                "schema": main_rel.get("schema"),
                "table": main_rel.get("table"),
                "relation": main_rel.get("relation"),
                "schema_safe": f"\"{main_rel.get('schema')}\"" if main_rel.get("schema") else None,
                "table_safe": f"\"{main_rel.get('table')}\"" if main_rel.get("table") else None,
                "relation_safe": f"\"{main_rel.get('schema')}\".\"{main_rel.get('table')}\"" if main_rel.get("schema") and main_rel.get("table") else None
            }
        feats.append({
            "nodeId": 9999007,  # искусственный nodeId
            "kind": "modulo_filter",
            **base
        })

    # 2) ORDER BY RANDOM() как fallback, если вдруг Sort Key не подсветился
    if re.search(r"order\s+by\s+random\(\)", sql, re.I):
        base = {}
        if main_rel:
            base = {
                "schema": main_rel.get("schema"),
                "table": main_rel.get("table"),
                "relation": main_rel.get("relation"),
                "schema_safe": f"\"{main_rel.get('schema')}\"" if main_rel.get("schema") else None,
                "table_safe": f"\"{main_rel.get('table')}\"" if main_rel.get("table") else None,
                "relation_safe": f"\"{main_rel.get('schema')}\".\"{main_rel.get('table')}\"" if main_rel.get("schema") and main_rel.get("table") else None
            }
        feats.append({
            "nodeId": 9999008,
            "kind": "order_by_random",
            **base
        })

def parse_main_relation(sql: str) -> Optional[Dict[str, str]]:
    m = MAIN_REL_RE.search(sql)
    if not m:
        return None
    schema = m.group('schema') or 'public'
    table  = m.group('table')
    schema_clean = schema.strip('"')
    table_clean  = table.strip('"')
    return {"schema": schema_clean, "table": table_clean, "relation": f"{schema_clean}.{table_clean}"}


def plan_to_features(plan_root: Dict[str, Any], sql: str) -> List[Dict[str, Any]]:
    feats: List[Dict[str, Any]] = []
    root = plan_root.get("Plan", plan_root)
    _walk(root, feats)

    # Fallback: если что-то "спряталось" оптимизатором — просканируем sql
    main_rel = parse_main_relation(sql)
    _scan_sql_for_patterns(sql, feats, main_rel)

    return feats