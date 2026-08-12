# app/routers/episodes.py - COM CONTENT SAFETY
"""
Router para episódios com sistema de Content Safety integrado.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import time
from datetime import datetime

# Imports dos services
from app.services.episodes_service import EpisodesAIService
from app.services.content_safety_service import ContentSafetyService, ContentRiskLevel

router = APIRouter()
logger = logging.getLogger(__name__)

# ==================== MODELOS ====================

class EpisodeRequest(BaseModel):
    """Request com opções de safety"""
    titulo: str
    tipo_serie: str = "motivacional"
    numero_episodio: int = 1
    duracao_estimada: int = 15
    
    historia_pessoal: Optional[str] = Field(
        None, 
        description="Sua história pessoal relacionada ao tema"
    )
    
    # Opções de content safety
    enable_safety_check: bool = Field(
        default=True,
        description="Ativar verificação de conteúdo sensível"
    )
    
    risk_tolerance: str = Field(
        default="medium",
        description="low | medium | high - tolerância a temas sensíveis"
    )

class SafetyAnalysis(BaseModel):
    """Análise de segurança do conteúdo"""
    risk_level: str
    compliance_score: float
    sensitive_topics: List[str]
    disclaimers: List[str]
    improvements: List[str]
    recommendations: List[str]

class EpisodeResponse(BaseModel):
    """Response com informações de safety"""
    titulo: str
    tipo_serie: str
    numero_episodio: int
    outline: Dict[str, Any]
    roteiro: Dict[str, Any]
    metadados: Dict[str, Any]
    tempo_geracao: float
    
    # Informações de content safety
    safety_analysis: Optional[SafetyAnalysis] = None
    warnings: Optional[List[str]] = None

# ==================== SERVICES ====================

ai_service = EpisodesAIService()
content_safety = ContentSafetyService()

# ==================== ENDPOINTS PRINCIPAIS ====================

@router.post("/generate", response_model=EpisodeResponse)
async def generate_episode_with_safety(request: EpisodeRequest):
    """
    Gera episódio com análise de content safety
    """
    start_time = time.time()
    
    logger.info(f"Gerando episódio: '{request.titulo}' com safety check: {request.enable_safety_check}")
    
    try:
        # 1. ANÁLISE PRÉVIA DE SEGURANÇA (se história pessoal fornecida)
        warnings = []
        sanitized_historia = request.historia_pessoal
        
        if request.enable_safety_check and request.historia_pessoal:
            # Análise prévia da história
            pre_safety = content_safety.analyze_content_safety(
                titulo=request.titulo,
                outline={},
                roteiro={},
                historia_pessoal=request.historia_pessoal
            )
            
            # Se risco muito alto, sanitiza ou avisa
            if pre_safety["risk_level"] == ContentRiskLevel.CRITICAL.value:
                if request.risk_tolerance == "low":
                    sanitized_historia = _sanitize_critical_content(request.historia_pessoal)
                    warnings.append("História pessoal foi modificada por conter conteúdo muito sensível")
                elif request.risk_tolerance == "medium":
                    warnings.append("História contém temas muito sensíveis - disclaimers adicionados")
                # high tolerance = mantém original mas com disclaimers
        
        # 2. GERA EPISÓDIO
        episode_content = ai_service.generate_episode_content(
            titulo=request.titulo,
            tipo_serie=request.tipo_serie,
            numero_episodio=request.numero_episodio,
            contexto_insights=None,
            duracao_estimada=request.duracao_estimada,
            historia_pessoal=sanitized_historia
        )
        
        # 3. ANÁLISE COMPLETA DE SEGURANÇA
        safety_analysis = None
        if request.enable_safety_check:
            safety_data = content_safety.analyze_content_safety(
                titulo=request.titulo,
                outline=episode_content.get("outline", {}),
                roteiro=episode_content.get("roteiro", {}),
                historia_pessoal=request.historia_pessoal
            )
            
            # Adiciona disclaimers se necessário
            if safety_data["disclaimers"]:
                episode_content = _add_disclaimers_to_episode(
                    episode_content, 
                    safety_data["disclaimers"]
                )
            
            # Cria objeto de análise para response
            safety_analysis = SafetyAnalysis(
                risk_level=safety_data["risk_level"],
                compliance_score=safety_data["compliance_score"],
                sensitive_topics=safety_data["sensitive_topics"],
                disclaimers=safety_data["disclaimers"],
                improvements=safety_data["improvements"],
                recommendations=safety_data["recommendations"]
            )
            
            # Adiciona informações de safety aos metadados
            if "metadados" not in episode_content:
                episode_content["metadados"] = {}
            
            episode_content["metadados"]["content_safety"] = {
                "risk_level": safety_data["risk_level"],
                "compliance_score": safety_data["compliance_score"],
                "has_disclaimers": len(safety_data["disclaimers"]) > 0
            }
        
        generation_time = time.time() - start_time
        
        return EpisodeResponse(
            titulo=request.titulo,
            tipo_serie=request.tipo_serie,
            numero_episodio=request.numero_episodio,
            outline=episode_content["outline"],
            roteiro=episode_content["roteiro"],
            metadados=episode_content["metadados"],
            tempo_geracao=round(generation_time, 2),
            safety_analysis=safety_analysis,
            warnings=warnings if warnings else None
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar episódio: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na geração: {str(e)}")

@router.post("/analyze-safety")
async def analyze_content_safety(data: dict):
    """
    Analisa apenas a segurança do conteúdo sem gerar episódio
    """
    try:
        titulo = data.get("titulo", "")
        historia_pessoal = data.get("historia_pessoal", "")
        
        if not titulo and not historia_pessoal:
            raise HTTPException(status_code=400, detail="Forneça pelo menos título ou história pessoal")
        
        # Análise de segurança
        safety_data = content_safety.analyze_content_safety(
            titulo=titulo,
            outline={},
            roteiro={},
            historia_pessoal=historia_pessoal
        )
        
        return {
            "titulo": titulo,
            "historia_fornecida": bool(historia_pessoal),
            "safety_analysis": safety_data,
            "recommendation": _get_safety_recommendation(safety_data["risk_level"])
        }
        
    except Exception as e:
        logger.error(f"Erro na análise de segurança: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na análise: {str(e)}")

@router.get("/safety-guidelines")
async def get_safety_guidelines():
    """
    Retorna diretrizes de content safety
    """
    return {
        "risk_levels": {
            "low": "Conteúdo padrão, poucos ou nenhum tema sensível",
            "medium": "Temas sensíveis presentes, disclaimers recomendados",
            "high": "Múltiplos temas sensíveis, revisão recomendada",
            "critical": "Temas muito sensíveis, modificação necessária"
        },
        "sensitive_topics": {
            "mental_health": "Saúde mental, suicídio, depressão",
            "medical": "Conselhos médicos, diagnósticos, tratamentos", 
            "reproductive": "Gravidez, aborto, fertilidade",
            "political": "Temas políticos partidários",
            "religious": "Conteúdo religioso potencialmente divisivo",
            "violence": "Violência, abuso, agressão",
            "financial": "Conselhos financeiros, investimentos",
            "legal": "Conselhos jurídicos"
        },
        "compliance_tips": [
            "Use disclaimers apropriados para temas sensíveis",
            "Evite generalizações absolutas (sempre, nunca)",
            "Inclua recursos de ajuda quando relevante", 
            "Mantenha linguagem inclusiva e respeitosa",
            "Não forneça conselhos médicos ou jurídicos específicos"
        ]
    }

# ==================== ENDPOINTS EXISTENTES ====================

@router.get("/tipos")
async def get_tipos_serie():
    """Lista tipos de série disponíveis"""
    return [
        "motivacional", "tutorial", "tendências", 
        "review", "notícias", "entretenimento"
    ]

@router.post("/preview")
async def preview_episode(titulo: str, tipo_serie: str = "motivacional"):
    """Prévia rápida do episódio"""
    try:
        resumo = ai_service.generate_quick_summary(titulo=titulo, tipo_serie=tipo_serie)
        return {
            "titulo": titulo,
            "tipo_serie": tipo_serie, 
            "resumo": resumo,
            "tempo_estimado": "15 min"
        }
    except Exception as e:
        logger.error(f"Erro ao gerar preview: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no preview: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check com informações de safety"""
    try:
        return {
            "status": "healthy",
            "service": "episodes_with_safety",
            "features": [
                "content_safety_analysis", 
                "sensitive_topic_detection",
                "automatic_disclaimers",
                "risk_level_assessment"
            ],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "timestamp": datetime.now().isoformat()}

# ==================== FUNÇÕES AUXILIARES ====================

def _sanitize_critical_content(historia_pessoal: str) -> str:
    """Sanitiza conteúdo crítico"""
    sanitized = historia_pessoal
    
    replacements = {
        "suicídio": "momentos muito difíceis",
        "suicidio": "momentos muito difíceis",
        "matar-me": "desistir de tudo",
        "me matar": "desistir de tudo", 
        "acabar com tudo": "encontrar uma saída",
        "overdose": "uso excessivo de substâncias",
        "cortar": "autolesão"
    }
    
    for original, replacement in replacements.items():
        sanitized = sanitized.replace(original, replacement)
    
    return sanitized

def _add_disclaimers_to_episode(episode_content: dict, disclaimers: List[str]) -> dict:
    """Adiciona disclaimers ao episódio"""
    
    # Adiciona disclaimer na abertura
    if "roteiro" in episode_content and "abertura" in episode_content["roteiro"]:
        disclaimer_text = " ".join(disclaimers[:2])  # Primeiros 2 disclaimers
        
        original_abertura = episode_content["roteiro"]["abertura"]
        episode_content["roteiro"]["abertura"] = (
            f"Antes de começarmos: {disclaimer_text} "
            f"Agora vamos ao episódio. {original_abertura}"
        )
    
    # Adiciona disclaimers completos nos metadados
    if "metadados" not in episode_content:
        episode_content["metadados"] = {}
    
    episode_content["metadados"]["disclaimers"] = disclaimers
    
    return episode_content

def _get_safety_recommendation(risk_level: str) -> str:
    """Retorna recomendação baseada no nível de risco"""
    recommendations = {
        "low": "Conteúdo seguro para publicação",
        "medium": "Adicione disclaimers apropriados", 
        "high": "Revise linguagem e adicione recursos de ajuda",
        "critical": "Considere modificar o conteúdo ou consultar especialistas"
    }
    return recommendations.get(risk_level, "Análise necessária")

# ==================== ENDPOINTS DE TESTE ====================

@router.post("/test-safety")
async def test_safety_system(data: dict):
    """Testa o sistema de safety com diferentes cenários"""
    
    test_scenarios = {
        "low_risk": {
            "titulo": "Como Ser Mais Produtivo",
            "historia": "Sempre tive dificuldade em me organizar, mas encontrei métodos que funcionam"
        },
        "medium_risk": {
            "titulo": "Superando a Depressão", 
            "historia": "Passei por momentos difíceis de depressão mas encontrei ajuda"
        },
        "high_risk": {
            "titulo": "Minha Luta Mental",
            "historia": "Tive pensamentos de autolesão mas busquei tratamento profissional"
        },
        "critical_risk": {
            "titulo": "Quase Desisti de Tudo",
            "historia": "Pensei em suicídio mas Jesus me salvou quando tinha 12 anos"
        }
    }
    
    scenario = data.get("scenario", "medium_risk")
    
    if scenario not in test_scenarios:
        return {"erro": "Cenários válidos: low_risk, medium_risk, high_risk, critical_risk"}
    
    test_data = test_scenarios[scenario]
    
    try:
        # Análise de safety
        safety_analysis = content_safety.analyze_content_safety(
            titulo=test_data["titulo"],
            outline={},
            roteiro={},
            historia_pessoal=test_data["historia"]
        )
        
        return {
            "scenario": scenario,
            "test_data": test_data,
            "safety_analysis": safety_analysis,
            "sanitized_content": _sanitize_critical_content(test_data["historia"]) if safety_analysis["risk_level"] == "critical" else test_data["historia"]
        }
        
    except Exception as e:
        return {"erro": f"Erro no teste: {str(e)}"}

@router.post("/generate-safe")
async def generate_safe_episode(request: dict):
    """Endpoint específico para gerar episódios com máxima segurança"""
    
    # Force configurações de máxima segurança
    safe_request = EpisodeRequest(
        titulo=request.get("titulo", ""),
        tipo_serie=request.get("tipo_serie", "motivacional"),
        numero_episodio=request.get("numero_episodio", 1),
        duracao_estimada=request.get("duracao_estimada", 15),
        historia_pessoal=request.get("historia_pessoal"),
        enable_safety_check=True,
        risk_tolerance="low"  # Máxima segurança
    )
    
    return await generate_episode_with_safety(safe_request)

# ==================== COMPLIANCE REPORT ====================

@router.get("/compliance-report")
async def generate_compliance_report():
    """Gera relatório de compliance do sistema"""
    
    return {
        "content_safety_system": {
            "version": "1.0",
            "active": True,
            "features": [
                "Sensitive topic detection",
                "Risk level assessment",
                "Automatic disclaimers",
                "Content sanitization",
                "Compliance scoring"
            ]
        },
        "topics_monitored": [
            "Mental health (suicide, depression, anxiety)",
            "Medical advice and diagnoses", 
            "Reproductive health and abortion",
            "Political content",
            "Religious sensitivity",
            "Violence and abuse",
            "Financial advice",
            "Legal guidance"
        ],
        "safety_measures": [
            "Pre-generation content analysis",
            "Post-generation safety review",
            "Automatic disclaimer injection",
            "Critical content sanitization",
            "Risk-based content warnings"
        ],
        "compliance_standards": [
            "Platform content policies",
            "Mental health safety guidelines",
            "Medical misinformation prevention",
            "Inclusive language practices"
        ],
        "emergency_resources": {
            "suicide_prevention": "CVV: 188 (24h gratuito)",
            "mental_health": "CAPS: Centros de Atenção Psicossocial",
            "domestic_violence": "Central de Atendimento à Mulher: 180",
            "general_emergency": "SAMU: 192"
        }
    }