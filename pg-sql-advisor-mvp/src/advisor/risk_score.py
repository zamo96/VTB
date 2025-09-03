from typing import List, Dict, Any

def aggregate_score(contribs: List[Dict[str, Any]], payload) -> Dict[str, Any]:
    raw = sum(min(40, c.get("score", 0)) for c in contribs)
    score = min(100, raw)  # MVP: без коэффициентов уверенности
    severity = "info" if score < 25 else "warning" if score < 50 else "critical"
    return {
        "score": score,
        "severity": severity,
        "drivers": [c.get("rule_id") for c in contribs]
    }
