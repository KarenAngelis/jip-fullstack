# app/services/compliance_service.py
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.compliance_model import ComplianceAnalysisLog


def _to_uuid(val: Any) -> uuid.UUID:
    if isinstance(val, uuid.UUID):
        return val
    return uuid.UUID(str(val))


def save_compliance_analysis(
    db: Session,
    *,
    user_id: int,
    request_id: str | uuid.UUID,
    request_payload: Dict[str, Any],
    analysis_payload: Dict[str, Any],
) -> ComplianceAnalysisLog:
    """
    Salva no banco uma análise de conformidade vinculada ao usuário.
    Campos batem com ComplianceAnalysisLog e com os schemas de saída.
    """
    model = ComplianceAnalysisLog(
        user_id=user_id,
        request_id=_to_uuid(request_id),

        # dados da requisição
        content=request_payload.get("content", ""),
        context_area=request_payload.get("context_area", "geral"),
        specific_laws=request_payload.get("specific_laws"),
        company_info=request_payload.get("company_info"),

        # resultado
        status=analysis_payload.get("status", "needs_review"),
        confidence_score=analysis_payload.get("confidence_score"),
        risk_level=analysis_payload.get("risk_level"),
        summary=analysis_payload.get("summary"),
        violations=analysis_payload.get("violations") or [],
        recommendations=analysis_payload.get("recommendations") or [],
        detailed_analysis=analysis_payload.get("detailed_analysis"),
        legal_sources=analysis_payload.get("legal_sources") or [],
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def list_user_analyses(
    db: Session,
    *,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
) -> List[ComplianceAnalysisLog]:
    """
    Retorna o histórico do usuário, mais recentes primeiro.
    A resposta bate com ComplianceAnalysisOut (from_attributes=True).
    """
    q = (
        db.query(ComplianceAnalysisLog)
        .filter(ComplianceAnalysisLog.user_id == user_id)
        .order_by(ComplianceAnalysisLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return q.all()


def get_user_analysis(
    db: Session,
    *,
    user_id: int,
    analysis_id: str | uuid.UUID,
) -> Optional[ComplianceAnalysisLog]:
    """
    Retorna uma análise específica do usuário (ou None).
    """
    aid = _to_uuid(analysis_id)
    return (
        db.query(ComplianceAnalysisLog)
        .filter(
            ComplianceAnalysisLog.user_id == user_id,
            ComplianceAnalysisLog.id == aid,
        )
        .first()
    )
