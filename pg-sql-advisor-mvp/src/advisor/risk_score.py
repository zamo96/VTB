from typing import List, Dict, Any

def aggregate_score(contribs: List[Dict[str, Any]], payload) -> Dict[str, Any]:
    raw = sum(min(40, c.get("score", 0)) for c in contribs)

    # confidence factor: если среди драйверов есть OUTDATED_STATS -> ×0.85
    drivers = [c.get("rule_id") for c in contribs]
    conf = 0.85 if any(d == "R_OUTDATED_STATS" for d in drivers) else 1.0

    score = min(100, round(raw * conf))
    severity = "info" if score < 25 else "warning" if score < 50 else "critical"

    return {"score": score, "severity": severity, "drivers": drivers, "confidence_factor": conf}
