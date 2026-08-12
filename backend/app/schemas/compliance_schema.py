# app/schemas/compliance_schema.py
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


# -------------------------------
# Request e Response principais
# -------------------------------
class ComplianceRequest(BaseModel):
    content: str = Field(..., min_length=1)
    context_area: str = Field(default="geral", max_length=120)
    specific_laws: Optional[List[str]] = None
    company_info: Optional[Dict[str, Any]] = None


class ComplianceResponse(BaseModel):
    analysis: Dict[str, Any]
    legal_sources: List[Dict[str, Any]]
    timestamp: str
    request_id: UUID   # ⬅️ já como UUID, mas o FastAPI converte para string no JSON


# -------------------------------
# Saída de histórico
# -------------------------------
class ComplianceAnalysisOut(BaseModel):
    id: UUID
    request_id: UUID
    context_area: str
    status: str
    risk_level: Optional[str] = None
    confidence_score: Optional[float] = None
    summary: Optional[str] = None
    violations: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    created_at: datetime

    model_config = {"from_attributes": True}
