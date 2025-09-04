from pydantic import BaseModel
from typing import List, Optional, Dict, Any


# pydantic v2
try:
    from pydantic import ConfigDict
    EXTRA_CFG = {"model_config": ConfigDict(extra="allow")}
except Exception:
    EXTRA_CFG = {}

class Feature(BaseModel):
    nodeId: int
    kind: str
    relation: Optional[str] = None
    estRows: Optional[int] = None
    selectivity: Optional[float] = None

    # Часто используемые доп.поля (необязательные)
    col: Optional[str] = None
    timeCol: Optional[str] = None
    fkCol: Optional[str] = None
    orderByCols: Optional[List[Dict[str, Any]]] = None
    includeCols: Optional[List[str]] = None
    memEstMB: Optional[float] = None
    workMemMB: Optional[float] = None

    # v1 fallback
    class Config:
        extra = "allow"

# v2 применим модельную конфигурацию, если доступна
if EXTRA_CFG:
    Feature.model_config = EXTRA_CFG["model_config"]



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
