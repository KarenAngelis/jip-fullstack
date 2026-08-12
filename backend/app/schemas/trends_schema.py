# app/schemas/trends_schema.py
from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# =================== ENUMS ===================

class TrendingPeriod(str, Enum):
    """Períodos disponíveis para análise (pytrends timeframe)."""
    LAST_HOUR = "now 1-H"
    LAST_4_HOURS = "now 4-H"
    LAST_DAY = "now 1-d"
    LAST_7_DAYS = "now 7-d"
    LAST_30_DAYS = "today 1-m"
    LAST_3_MONTHS = "today 3-m"
    LAST_12_MONTHS = "today 12-m"
    LAST_5_YEARS = "today 5-y"


class CompetitionLevel(str, Enum):
    """Níveis de competição."""
    VERY_LOW = "muito_baixa"
    LOW = "baixa"
    MEDIUM = "media"
    HIGH = "alta"
    VERY_HIGH = "muito_alta"


class OpportunityType(str, Enum):
    """Tipos de oportunidade."""
    VIRAL = "viral"
    TRENDING = "trending"
    SEASONAL = "sazonal"
    NICHE = "nicho"
    EVERGREEN = "evergreen"
    DECLINING = "decadencia"


class ContentType(str, Enum):
    """Tipos de conteúdo sugeridos."""
    ARTICLE = "artigo"
    VIDEO = "video"
    TUTORIAL = "tutorial"
    INFOGRAPHIC = "infografico"
    PODCAST = "podcast"
    SOCIAL_POST = "post_social"
    EMAIL_SEQUENCE = "sequencia_email"
    WEBINAR = "webinar"
    EBOOK = "ebook"
    COURSE = "curso"


# =================== MODELOS ===================

class TrendMetrics(BaseModel):
    """Métricas essenciais de uma tendência (0-100 para interesses)."""
    current_interest: int = Field(..., ge=0, le=100, description="Interesse atual (0-100)")
    peak_interest: int = Field(..., ge=0, le=100, description="Pico de interesse")
    average_interest: float = Field(..., ge=0, le=100, description="Interesse médio")
    # 🔒 Só preencher quando houver base real suficiente
    growth_rate: Optional[float] = Field(None, description="Variação % (janela definida)")
    volatility: Optional[float] = Field(None, ge=0, description="Volatilidade normalizada")
    trend_direction: Literal["crescendo", "estavel", "decaindo", "desconhecido"] = Field(
        "desconhecido", description="Direção da tendência"
    )

    model_config = {"extra": "forbid"}


class GeographicInsight(BaseModel):
    """Dados geográficos simplificados (apenas UF válidas e ranking por interesse)."""
    region: str = Field(..., description="Nome da região")
    state_code: Literal[
        "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
        "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"
    ] = Field(..., description="UF (SP, RJ, RN, etc)")
    interest_score: int = Field(..., ge=0, le=100, description="Interesse (0-100)")
    interest_rank: int = Field(..., description="Posição no ranking por interesse")

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "region": "São Paulo",
                "state_code": "SP",
                "interest_score": 85,
                "interest_rank": 1,
            }
        }
    }


class SmartQuery(BaseModel):
    """Query relacionada inteligente."""
    text: str = Field(..., description="Texto da query")
    search_volume: str = Field(..., description="Volume estimado (ex.: '10K-100K')")
    difficulty: CompetitionLevel = Field(..., description="Dificuldade de ranquear")
    intent: Literal["informacional", "comercial", "navegacional", "transacional"] = Field(
        ..., description="Intenção de busca"
    )
    opportunity_score: int = Field(..., ge=0, le=100, description="Score de oportunidade")

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "text": "como se inscrever no enem 2025",
                "search_volume": "100K-1M",
                "difficulty": "media",
                "intent": "informacional",
                "opportunity_score": 78,
            }
        }
    }


class TrendingTopic(BaseModel):
    """Tópico em tendência otimizado para UX."""
    title: str = Field(..., description="Título limpo e atrativo")
    category: str = Field(..., description="Categoria principal")
    metrics: TrendMetrics = Field(..., description="Métricas da tendência")

    # Dados úteis para criadores de conteúdo
    estimated_searches: str = Field(..., description="Estimativa de buscas/mês")
    competition_level: CompetitionLevel = Field(..., description="Nível de competição")
    opportunity_type: OpportunityType = Field(..., description="Tipo de oportunidade")

    # Timing
    best_time_to_publish: str = Field(..., description="Melhor momento para publicar")
    trend_duration: str = Field(..., description="Duração estimada da tendência")

    # Geografia / Related
    top_regions: List[GeographicInsight] = Field(default_factory=list, description="Top regiões")
    related_opportunities: List[SmartQuery] = Field(default_factory=list, description="Oportunidades relacionadas")

    # Metadados
    discovered_at: datetime = Field(default_factory=datetime.now, description="Quando foi descoberta")
    confidence_score: int = Field(..., ge=0, le=100, description="Confiança nos dados")

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "title": "ENEM 2025: Inscrições e Datas",
                "category": "Educação",
                "metrics": {
                    "current_interest": 75,
                    "peak_interest": 95,
                    "average_interest": 65,
                    "growth_rate": 45.2,
                    "volatility": 0.3,
                    "trend_direction": "crescendo",
                },
                "estimated_searches": "500K-2M/mês",
                "competition_level": "media",
                "opportunity_type": "sazonal",
                "best_time_to_publish": "Agosto - Outubro",
                "trend_duration": "3-4 meses",
                "confidence_score": 85,
            }
        }
    }


class ContentOpportunity(BaseModel):
    """Oportunidade de conteúdo refinada."""
    topic: str = Field(..., description="Tópico principal")
    hook: str = Field(..., description="Gancho/título sugerido")
    opportunity_type: OpportunityType = Field(..., description="Tipo de oportunidade")

    # Análise
    market_analysis: Dict[str, Any] = Field(default_factory=dict, description="Análise do mercado")
    competition_analysis: Dict[str, Any] = Field(default_factory=dict, description="Análise da competição")

    # Estratégia
    content_angles: List[str] = Field(default_factory=list, description="Ângulos de conteúdo")
    target_keywords: List[SmartQuery] = Field(default_factory=list, description="Palavras-chave alvo")
    content_types: List[ContentType] = Field(default_factory=list, description="Tipos de conteúdo")

    # Execução
    urgency_level: Literal["baixa", "media", "alta", "critica"] = Field(..., description="Urgência")
    best_channels: List[str] = Field(default_factory=list, description="Melhores canais")
    estimated_roi: str = Field(..., description="ROI estimado")

    # Audiência
    target_personas: List[str] = Field(default_factory=list, description="Personas alvo")
    audience_size: str = Field(..., description="Tamanho da audiência")

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "topic": "ENEM 2025",
                "hook": "Guia Completo ENEM 2025: Inscrições, Datas e Estratégias",
                "opportunity_type": "sazonal",
                "market_analysis": {
                    "demand": "Alta (agosto-novembro)",
                    "seasonality": "Pico em outubro",
                    "audience_behavior": "Busca informações práticas",
                },
                "content_angles": ["Cronograma de estudos", "Dicas de redação", "Simulados gratuitos"],
                "urgency_level": "alta",
                "estimated_roi": "Alto (período de alta demanda)",
                "audience_size": "2M+ estudantes",
            }
        }
    }


class TrendAnalysisResult(BaseModel):
    """Resultado completo da análise de trends (somente dados reais; sem inventar)."""
    keyword: str = Field(..., description="Palavra-chave analisada")
    analysis_date: datetime = Field(default_factory=datetime.now, description="Data da análise")

    # Dados principais
    overall_metrics: Optional[TrendMetrics] = Field(default=None, description="Métricas gerais")
    geographical_breakdown: List[GeographicInsight] = Field(default_factory=list, description="Breakdown geográfico")

    # Timeline inteligente
    historical_performance: List[Dict[str, Any]] = Field(default_factory=list, description="Performance histórica")
    seasonal_patterns: Optional[Dict[str, Any]] = Field(default=None, description="Padrões sazonais identificados")
    future_predictions: Optional[Dict[str, Any]] = Field(default=None, description="Predições baseadas em padrões")

    # Inteligência competitiva
    related_topics: List[Dict[str, Any]] = Field(default_factory=list, description="Tópicos relacionados")
    competitor_content: List[Dict[str, Any]] = Field(default_factory=list, description="Conteúdo concorrente")
    content_gaps: List[str] = Field(default_factory=list, description="Lacunas de conteúdo identificadas")

    # Recomendações estratégicas (apenas se solicitado e houver fonte)
    opportunities: List[ContentOpportunity] = Field(default_factory=list, description="Oportunidades identificadas")
    quick_wins: List[str] = Field(default_factory=list, description="Vitórias rápidas")
    long_term_strategy: Optional[Dict[str, Any]] = Field(default=None, description="Estratégia de longo prazo")

    # Proveniência (para auditar que é live)
    provenance: Optional[Dict[str, Any]] = Field(default=None, description="Metadados de proveniência da coleta")

    model_config = {"extra": "forbid"}


# ============= REQUEST MODELS =============

class TrendsSearchRequest(BaseModel):
    """Request otimizado para busca de trends (live-first)."""
    keywords: List[str] = Field(..., min_items=1, max_items=5, description="Palavras-chave (máx 5)")
    timeframe: TrendingPeriod = Field(default=TrendingPeriod.LAST_12_MONTHS, description="Período de análise")
    geo: str = Field(default="BR", description="País/região")
    category: Optional[int] = Field(None, description="ID da categoria")
    include_predictions: bool = Field(default=False, description="Incluir predições")
    include_opportunities: bool = Field(default=False, description="Incluir oportunidades")
    competitor_analysis: bool = Field(default=False, description="Análise de concorrentes")

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: List[str]) -> List[str]:
        cleaned: List[str] = []
        for keyword in v:
            k = keyword.strip()
            if len(k) < 2:
                raise ValueError("Keyword deve ter pelo menos 2 caracteres")
            if len(k) > 100:
                raise ValueError("Keyword muito longa (máx 100 caracteres)")
            cleaned.append(k.lower())
        return cleaned

    model_config = {"extra": "forbid"}


class OpportunitySearchRequest(BaseModel):
    """Request para busca de oportunidades."""
    industry: str = Field(..., description="Setor/indústria")
    target_audience: str = Field(..., description="Audiência alvo")
    content_goals: List[str] = Field(..., description="Objetivos do conteúdo")
    budget_level: Literal["baixo", "medio", "alto"] = Field(default="medio", description="Nível de orçamento")
    urgency: Literal["baixa", "media", "alta"] = Field(default="media", description="Urgência")
    preferred_content_types: List[ContentType] = Field(default_factory=list, description="Tipos de conteúdo preferidos")

    model_config = {"extra": "forbid"}


# ============= RESPOSTA SIMPLIFICADA =============

class QuickTrendSummary(BaseModel):
    """Resumo rápido para dashboard."""
    topic: str
    status: Literal["🔥 Em alta", "📈 Crescendo", "📊 Estável", "📉 Decaindo"]
    opportunity_score: int = Field(..., ge=0, le=100)
    estimated_traffic: str
    difficulty: Literal["Fácil", "Médio", "Difícil"]
    best_action: str

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "topic": "IA Generativa",
                "status": "🔥 Em alta",
                "opportunity_score": 89,
                "estimated_traffic": "500K+ visitas/mês",
                "difficulty": "Médio",
                "best_action": "Criar guia prático para iniciantes",
            }
        }
    }


class TrendsDashboard(BaseModel):
    """Dashboard simplificado."""
    trending_now: List[QuickTrendSummary] = Field(default_factory=list, description="Tendências atuais")
    opportunities: List[QuickTrendSummary] = Field(default_factory=list, description="Oportunidades identificadas")
    your_keywords: List[QuickTrendSummary] = Field(default_factory=list, description="Suas palavras-chave")
    industry_insights: Dict[str, Any] = Field(default_factory=dict, description="Insights do setor")
    last_updated: datetime = Field(default_factory=datetime.now, description="Última atualização")

    model_config = {"extra": "forbid"}


# 🔁 Corrige referências adiantadas (se necessário)
TrendAnalysisResult.model_rebuild()
