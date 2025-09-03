from fastapi import FastAPI
from src.models import AdviseInput, AdviseResponse
from src.advisor.rule_engine import apply_rules
from src.advisor.risk_score import aggregate_score
from src.advisor.explainer import render_report
from src.advisor.rules_loader import load_rules

app = FastAPI(title="PG SQL Advisor (MVP)")
rules = load_rules()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/advise", response_model=AdviseResponse)
def advise(payload: AdviseInput):
    recs, contributions = apply_rules(payload, rules)
    risk = aggregate_score(contributions, payload)
    md   = render_report(recs, risk, payload)
    return {"risk": risk, "recommendations": recs, "explain_md": md}
