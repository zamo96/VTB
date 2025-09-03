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
