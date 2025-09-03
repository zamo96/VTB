#!/bin/bash

# Создание корневой папки
mkdir -p pg-sql-advisor-mvp
cd pg-sql-advisor-mvp || exit

# Основные файлы
touch README.md .gitignore .env.example docker-compose.yml Dockerfile pyproject.toml

# SRC
mkdir -p src/advisor src/rules/ruleset-v1 src/utils tests/golden

# Основные Python файлы
cat > src/app.py <<'EOF'
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
EOF

cat > src/models.py <<'EOF'
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Feature(BaseModel):
    nodeId: int
    kind: str
    relation: Optional[str] = None
    estRows: Optional[int] = None
    selectivity: Optional[float] = None
    memEstMB: Optional[int] = None
    workMemMB: Optional[int] = None

class StatRef(BaseModel):
    table: str
    columns: List[str]
    n_distinct: Optional[float] = None

class AdviseInput(BaseModel):
    features: List[Feature]
    statsUsed: Optional[List[StatRef]] = []
    dbSettings: Optional[Dict[str, Any]] = {}
    sqlText: Optional[str] = None

class Recommendation(BaseModel):
    id: str
    rule_id: str
    type: str
    title: str
    action: Dict[str, Any]
    expected_gain: Dict[str, Any]
    effort: str
    confidence: str
    evidence: List[Dict[str, Any]]

class Risk(BaseModel):
    score: int
    severity: str
    drivers: List[str]

class AdviseResponse(BaseModel):
    risk: Risk
    recommendations: List[Recommendation]
    explain_md: str
EOF

# Advisor Engine файлы
touch src/advisor/{rule_engine.py,risk_score.py,explainer.py,rules_loader.py,schemas.py}
touch src/utils/jsonlogic.py

# Тесты
cat > tests/test_advise_smoke.py <<'EOF'
import pytest
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] == True
EOF

# Пример входных/выходных тестовых данных
cat > tests/golden/in_case_01.json <<'EOF'
{
  "features": [
    { "nodeId": 10, "kind": "seq_scan_big_table", "relation":"sales.order_items", "estRows":48000000, "selectivity":0.03 },
    { "nodeId": 4,  "kind": "sort_spill_risk", "memEstMB":180, "workMemMB":64 }
  ],
  "statsUsed": [
    { "table":"sales.order_items", "columns":["category"], "n_distinct":-0.2 }
  ],
  "dbSettings": { "work_memMB": 64 },
  "sqlText": "SELECT ... ORDER BY s DESC LIMIT 100"
}
EOF

cat > tests/golden/out_case_01.json <<'EOF'
{
  "risk": { "score": 70, "severity": "critical", "drivers": ["R_SEQ_SCAN_BIG_TABLE","R_SORT_SPILL"] },
  "recommendations": [],
  "explain_md": "demo"
}
EOF

# Заглушки для правил
for r in R_SEQ_SCAN_BIG_TABLE.yaml R_SORT_SPILL.yaml R_ORDER_BY_LIMIT.yaml R_LIKE_LEADING_WILDCARD.yaml R_OUTDATED_STATS.yaml; do
  echo "# $r (MVP rule stub)" > src/rules/ruleset-v1/$r
done

echo "✅ Структура проекта создана."