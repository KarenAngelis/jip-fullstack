# app/routers/compliance.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional, Dict
from datetime import datetime
import uuid

from sqlalchemy.orm import Session

# ==== seus imports existentes ====
from app.services.juridical.compliance_analyzer import LegalComplianceAnalyzer, ComplianceAnalysis
# Supondo que você tenha esses providers:
# from app.dependencies.compliance import get_compliance_analyzer, get_monitoring_service
def get_compliance_analyzer() -> LegalComplianceAnalyzer:
    # TODO: usar sua factory real
    return LegalComplianceAnalyzer()

# ==== novos imports para auth/db ====
from app.dependencies.auth import get_current_active_user
from app.database.database import get_db
from app.models.user_model import User

# ==== schemas ====
from app.schemas.compliance_schema import (
    ComplianceRequest,
    ComplianceResponse,
    ComplianceAnalysisOut,
)

# ==== service de persistência ====
from app.services.compliance_service import (
    save_compliance_analysis,
    list_user_analyses,
    get_user_analysis,
)

router = APIRouter(prefix="/api/compliance", tags=["Legal Compliance"])


@router.post("/analyze", response_model=ComplianceResponse, include_in_schema=False, deprecated=True)
async def analyze_legal_compliance(
    request: ComplianceRequest,
    analyzer: LegalComplianceAnalyzer = Depends(get_compliance_analyzer),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Analisa conformidade e **salva no banco** vinculada ao usuário autenticado.
    """
    try:
        analysis: ComplianceAnalysis = await analyzer.analyze_compliance(
            content_to_analyze=request.content,
            context_area=request.context_area,
            specific_laws=request.specific_laws,
        )

        request_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        # Monta payloads (espelhando o que você já retorna)
        analysis_dict = {
            "status": analysis.status.value if hasattr(analysis.status, "value") else analysis.status,
            "confidence_score": getattr(analysis, "confidence_score", None),
            "violations": getattr(analysis, "violations", None),
            "recommendations": getattr(analysis, "recommendations", None),
            "risk_level": getattr(analysis, "risk_level", None),
            "summary": getattr(analysis, "summary", None),
            "detailed_analysis": getattr(analysis, "detailed_analysis", None),
            "legal_sources": getattr(analysis, "legal_basis", []) or [],
        }

        # Persistência
        save_compliance_analysis(
            db,
            user_id=current_user.id,
            request_id=request_id,
            request_payload=request.model_dump(),
            analysis_payload=analysis_dict,
        )

        return ComplianceResponse(
            analysis={
                "status": analysis_dict["status"],
                "confidence_score": analysis_dict["confidence_score"],
                "violations": analysis_dict["violations"],
                "recommendations": analysis_dict["recommendations"],
                "risk_level": analysis_dict["risk_level"],
                "summary": analysis_dict["summary"],
                "detailed_analysis": analysis_dict["detailed_analysis"],
            },
            legal_sources=analysis_dict["legal_sources"],
            timestamp=timestamp,
            request_id=request_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na análise: {str(e)}")


@router.get("/history", response_model=List[ComplianceAnalysisOut])
def list_my_compliance_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Lista **somente** o histórico do usuário autenticado.
    """
    logs = list_user_analyses(db, user_id=current_user.id)
    return logs


@router.get("/history/{analysis_id}", response_model=ComplianceAnalysisOut)
def get_my_compliance_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Detalhe de uma análise específica do usuário.
    """
    log = get_user_analysis(db, user_id=current_user.id, analysis_id=analysis_id)
    if not log:
        # 404 evita vazar existência de análises de outros usuários
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    return log


# ---- Seus endpoints adicionais, com ajuste opcional de segurança/persistência ----

@router.post("/analyze-document")
async def analyze_document_compliance(
    document_type: str,
    document_content: str,
    company_sector: str = "geral",
    analyzer: LegalComplianceAnalyzer = Depends(get_compliance_analyzer),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Análise especializada por tipo de documento.
    (Se quiser, salve no banco aqui também — segue exemplo).
    """
    context_mapping = {
        "termos_uso": "consumidor e-commerce",
        "politica_privacidade": "lgpd proteção dados",
        "politica_cookies": "lgpd cookies internet",
        "contrato_trabalho": "trabalhista clt",
        "politica_trocas": "consumidor direito arrependimento",
        "politica_entrega": "consumidor prazos entrega",
    }
    context = context_mapping.get(document_type, "geral")
    analysis = await analyzer.analyze_compliance(
        content_to_analyze=document_content,
        context_area=f"{context} {company_sector}".strip(),
    )

    # exemplo de persistência (opcional)
    request_id = str(uuid.uuid4())
    analysis_dict = {
        "status": getattr(analysis, "status", None) if isinstance(getattr(analysis, "status", None), str) else getattr(getattr(analysis, "status", None), "value", None),
        "confidence_score": getattr(analysis, "confidence_score", None),
        "violations": getattr(analysis, "violations", None),
        "recommendations": getattr(analysis, "recommendations", None),
        "risk_level": getattr(analysis, "risk_level", None),
        "summary": getattr(analysis, "summary", None),
        "detailed_analysis": getattr(analysis, "detailed_analysis", None),
        "legal_sources": getattr(analysis, "legal_basis", []) or [],
    }
    save_compliance_analysis(
        db,
        user_id=current_user.id,
        request_id=request_id,
        request_payload={
            "content": document_content,
            "context_area": f"{context} {company_sector}".strip(),
            "specific_laws": None,
            "company_info": None,
        },
        analysis_payload=analysis_dict,
    )

    return {
        "analysis": analysis_dict,
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/bulk-analyze")
async def bulk_compliance_analysis(
    documents: List[Dict[str, str]],
    analyzer: LegalComplianceAnalyzer = Depends(get_compliance_analyzer),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Análise em lote com salvamento por item.
    """
    results = []
    for doc in documents:
        try:
            analysis = await analyzer.analyze_compliance(
                content_to_analyze=doc["content"],
                context_area=doc.get("type", "geral"),
            )

            request_id = str(uuid.uuid4())
            analysis_dict = {
                "status": getattr(analysis, "status", None) if isinstance(getattr(analysis, "status", None), str) else getattr(getattr(analysis, "status", None), "value", None),
                "confidence_score": getattr(analysis, "confidence_score", None),
                "violations": getattr(analysis, "violations", None),
                "recommendations": getattr(analysis, "recommendations", None),
                "risk_level": getattr(analysis, "risk_level", None),
                "summary": getattr(analysis, "summary", None),
                "detailed_analysis": getattr(analysis, "detailed_analysis", None),
                "legal_sources": getattr(analysis, "legal_basis", []) or [],
            }

            save_compliance_analysis(
                db,
                user_id=current_user.id,
                request_id=request_id,
                request_payload={
                    "content": doc["content"],
                    "context_area": doc.get("type", "geral"),
                    "specific_laws": None,
                    "company_info": None,
                },
                analysis_payload=analysis_dict,
            )

            results.append({
                "document_name": doc.get("name"),
                "request_id": request_id,
                "analysis": analysis_dict,
                "status": "success",
            })
        except Exception as e:
            results.append({
                "document_name": doc.get("name"),
                "error": str(e),
                "status": "error",
            })

    summary = {
        "total_documents": len(documents),
        "successful_analyses": len([r for r in results if r["status"] == "success"]),
        "failed_analyses": len([r for r in results if r["status"] == "error"]),
    }
    return {"summary": summary, "detailed_results": results}
