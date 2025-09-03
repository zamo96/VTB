from typing import Tuple, List, Dict, Any
from src.models import AdviseInput

def apply_rules(payload: AdviseInput, rules: List[dict]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    feats = payload.features or []
    recs: List[Dict[str, Any]] = []
    contribs: List[Dict[str, Any]] = []

    # Примерное правило: большой Seq Scan при селективности < 10%
    seq = next((f for f in feats if f.kind == "seq_scan_big_table"), None)
    if seq and (seq.selectivity or 1.0) < 0.10:
        recs.append({
            "id": "REC_IDX_1",
            "rule_id": "R_SEQ_SCAN_BIG_TABLE",
            "type": "index",
            "title": "Индекс по order_items(category)",
            "action": {"ddl": "CREATE INDEX CONCURRENTLY idx_order_items_category ON sales.order_items(category);"},
            "expected_gain": {"kind":"cost_delta","value":-0.62,"source":"estimate"},
            "effort": "low",
            "confidence": "high",
            "evidence": [{"nodeId": seq.nodeId, "relation": getattr(seq, "relation", None), "selectivity": seq.selectivity}]
        })
        contribs.append({"rule_id": "R_SEQ_SCAN_BIG_TABLE", "score": 40, "drivers": ["seq_scan_big_table"]})

    # Примерное правило: риск спилла Sort/HashAgg
    spill = next((f for f in feats if f.kind == "sort_spill_risk"), None)
    if spill and (spill.memEstMB or 0) > (spill.workMemMB or 64):
        recs.append({
            "id": "REC_MEM_1",
            "rule_id": "R_SORT_SPILL",
            "type": "db_setting",
            "title": "Поднять work_mem на сессию до 128MB",
            "action": {"alter": "SET LOCAL work_mem = '128MB';"},
            "expected_gain": {"kind":"spill_risk_drop","value":"high→low","source":"heuristic"},
            "effort": "low",
            "confidence": "medium",
            "evidence": [{"nodeId": spill.nodeId, "memEstMB": spill.memEstMB, "workMemMB": spill.workMemMB}]
        })
        contribs.append({"rule_id": "R_SORT_SPILL", "score": 30, "drivers": ["sort_spill_risk"]})

    return recs, contribs
