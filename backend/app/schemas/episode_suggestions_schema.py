# app/schemas/episode_suggestions_schema.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# === ENUMS ===
class LegalStatus(str, Enum):
    """Status da análise jurídica"""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"

# === REQUEST SCHEMAS ===
class EpisodeSuggestionRequest(BaseModel):
    """Schema para requisição de geração de sugestões"""
    title: str = Field(
        ..., 
        min_length=3, 
        max_length=200, 
        description="Título base do episódio"
    )
    context: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Contexto adicional sobre o tema"
    )
    personal_input: Optional[str] = Field(
        None, 
        max_length=500, 
        description="Experiência pessoal do criador"
    )
    target_audience: str = Field(
        default="geral", 
        description="Público-alvo"
    )
    episode_format: str = Field(
        default="entrevista", 
        description="Formato do episódio"
    )

# === ANALYSIS SCHEMAS ===
class JIPTrendAnalysis(BaseModel):
    """Análise JIP de tendências"""
    trend_score: float = Field(..., ge=0, le=100, description="Score JIP de tendência")
    market_direction: str = Field(..., description="Direção do mercado")
    competition_level: str = Field(..., description="Nível de competição")
    growth_prediction: float = Field(..., description="Predição de crescimento")
    opportunity_level: str = Field(..., description="Nível de oportunidade")

class JIPLegalAnalysis(BaseModel):
    """Análise JIP de compliance"""
    status: LegalStatus = Field(..., description="Status da análise")
    confidence_score: float = Field(..., ge=0, le=1, description="Confiança da análise")
    issues_found: List[str] = Field(default=[], description="Questões identificadas")
    recommendations: List[str] = Field(default=[], description="Recomendações")
    risk_level: str = Field(..., description="Nível de risco")

class JIPMarketAnalysis(BaseModel):
    """Análise JIP de mercado"""
    audience_interest: float = Field(..., description="Interesse da audiência")
    content_saturation: str = Field(..., description="Saturação de conteúdo")
    best_timing: str = Field(..., description="Melhor timing")
    estimated_reach: int = Field(..., description="Alcance estimado")
    engagement_prediction: str = Field(..., description="Predição de engajamento")

class EpisodeNews(BaseModel):
    """Notícias relevantes para o episódio"""
    title: str = Field(..., description="Título da notícia")
    summary: str = Field(..., description="Resumo da notícia")
    relevance: str = Field(..., description="Por que é relevante")
    talking_points: List[str] = Field(..., description="Pontos para discussão")
    source_date: str = Field(..., description="Data da notícia")

class GuestSuggestion(BaseModel):
    """Sugestão de convidado por função"""
    name: str = Field(..., description="Função/cargo")
    expertise: str = Field(..., description="Área de expertise")
    relevance_score: float = Field(..., ge=0, le=100)
    justification: str = Field(..., description="Justificativa")
    contact_suggestion: str = Field(..., description="Como encontrar")

# === MAIN SCHEMAS ===
class EpisodeSuggestion(BaseModel):
    """Sugestão completa de episódio"""
    id: str = Field(..., description="ID único")
    title: str = Field(..., description="Título do episódio")
    short_description: str = Field(..., description="Descrição gerada por IA")
    keywords: List[str] = Field(..., description="Palavras-chave para conversa")
    guest_suggestions: List[GuestSuggestion] = Field(default=[], description="Convidados sugeridos")
    success_probability: float = Field(..., ge=0, le=100, description="Probabilidade de sucesso")
    
    # Análises JIP
    jip_trend_analysis: JIPTrendAnalysis = Field(..., description="Análise JIP de trends")
    jip_legal_analysis: JIPLegalAnalysis = Field(..., description="Análise JIP de compliance")
    jip_market_analysis: JIPMarketAnalysis = Field(..., description="Análise JIP de mercado")
    
    # Notícias para comentar
    episode_news: List[EpisodeNews] = Field(default=[], description="Notícias para comentar")
    
    # Metadados
    created_at: datetime = Field(default_factory=datetime.now)
    estimated_duration: int = Field(..., description="Duração em minutos")
    difficulty_level: str = Field(..., description="Nível de dificuldade")
    target_audience: str = Field(..., description="Público-alvo")

class EpisodeSuggestionsResponse(BaseModel):
    """Resposta com 12 sugestões"""
    request_title: str = Field(..., description="Título original")
    request_context: Optional[str] = Field(None, description="Contexto original")
    total_suggestions: int = Field(..., description="Total de sugestões")
    suggestions: List[EpisodeSuggestion] = Field(..., description="Lista das sugestões")
    
    # Análise geral
    overall_trend_score: float = Field(..., description="Score geral JIP")
    market_opportunity: str = Field(..., description="Oportunidade de mercado")
    recommended_timing: str = Field(..., description="Timing recomendado")
    
    # Metadados
    generated_at: datetime = Field(default_factory=datetime.now)
    processing_time_ms: float = Field(..., description="Tempo de processamento")

# === AUXILIARY SCHEMAS ===
class EpisodeAnalyticsRequest(BaseModel):
    """Request para analytics"""
    days: int = Field(default=30, ge=1, le=365)

class HealthCheckResponse(BaseModel):
    """Health check"""
    status: str
    timestamp: str
    endpoints_available: Optional[List[str]] = None