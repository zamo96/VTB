# src/advisor/feature_normalizer.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple
from datetime import date, timedelta

def _quote_ident(ident: str) -> str:
    if not ident:
        return '""'
    return ident if ident.startswith('"') and ident.endswith('"') else f'"{ident}"'

def _split_relation(rel: str, schema_hint: str | None = None, table_hint: str | None = None) -> Tuple[str, str]:
    if rel:
        if "." in rel:
            s, t = rel.split(".", 1)
            return s.strip('"'), t.strip('"')
        # rel без схемы
        return (schema_hint or "public").strip('"'), rel.strip('"')
    # rel отсутствует — пробуем hints
    return (schema_hint or "public").strip('"'), (table_hint or "").strip('"')

def _ensure_list(v) -> List[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, (list, tuple, set)):
        return [str(x) for x in v if x is not None and str(x) != ""]
    return [str(v)]

def _safe_cols(cols: List[str]) -> List[str]:
    return [_quote_ident(c.strip('"')) for c in cols]

def _clamp_selectivity(v):
    if v is None:
        return None
    try:
        v = float(v)
        if v < 0: v = 0.0
        if v > 1: v = 1.0
        return v
    except Exception:
        return None

def _compute_toDate_next(f: Dict[str, Any]) -> None:
    if f.get("fromDate") and f.get("toDate") and not f.get("toDate_next"):
        try:
            y, m, d = map(int, str(f["toDate"]).split("-"))
            f["toDate_next"] = str(date(y, m, d) + timedelta(days=1))
        except Exception:
            pass

def normalize_feature(f: Dict[str, Any]) -> Dict[str, Any]:
    nf = dict(f)

    # 1) relation/schema/table & safe placeholders
    rel = nf.get("relation") or nf.get("table")
    s, t = _split_relation(rel, nf.get("schema"), nf.get("table"))
    nf["schema"], nf["table"] = s, t
    nf["relation"] = f"{s}.{t}"
    nf["schema_safe"] = _quote_ident(s)
    nf["table_safe"] = _quote_ident(t)
    nf["relation_safe"] = f'{nf["schema_safe"]}.{nf["table_safe"]}'

    # 2) унификация ключей
    if "includeCols" in nf and "include_cols" not in nf:
        nf["include_cols"] = nf["includeCols"]

    # 3) списки колонок + safe-версии
    for key in ("cols", "include_cols", "orderByCols"):
        if key in nf:
            nf[key] = _ensure_list(nf[key])
            nf[f"{key}_safe"] = _safe_cols(nf[key])

    # 4) типы/границы
    if "selectivity" in nf:
        nf["selectivity"] = _clamp_selectivity(nf.get("selectivity"))

    for k in ("estRows", "memEstMB", "workMemMB", "limitN"):
        if k in nf and nf[k] is not None:
            try:
                nf[k] = int(nf[k])
            except Exception:
                try:
                    nf[k] = float(nf[k])
                except Exception:
                    pass

    # 5) рассчитать toDate_next при диапазоне дат
    _compute_toDate_next(nf)

    return nf

def fingerprint(nf: Dict[str, Any]) -> Tuple:
    return (
        nf.get("kind"),
        nf.get("relation"),
        tuple(nf.get("cols") or []),
        tuple(nf.get("include_cols") or []),
        nf.get("nodeId"),
    )

def normalize_features(features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for f in features or []:
        nf = normalize_feature(f)
        fp = fingerprint(nf)
        if fp in seen:
            continue
        seen.add(fp)
        out.append(nf)
    return out
