"""
Schemas Pydantic para geração de conteúdo

Conexões rápidas
- router = content_generation.py   (usa estes schemas nas rotas)
- service = ai_service.py          (consome/produz metadados compatíveis)

Resumo
- Define contratos de entrada/saída da API: request de geração, item gerado, metadados e respostas.
- Inclui modelos MOCK para histórico de conteúdos recentes (apenas para testes/UX).
- Campos opcionais de metadados foram ampliados para cobrir títulos, roteiros e episódios.
  Em produção, os `null` serão filtrados pelo router com `response_model_exclude_none=True`.

Modelos
- ContentGenerationRequest: request para geração (títulos/roteiros/episódios).
- ContentMetadata: metadados ricos (engagement/SEO/trend, tempos, estrutura etc.).
- GeneratedContentItem: item padronizado de retorno (content, score, metadata).
- ContentGenerationResponse: envelope padrão de resposta.
- MockRecentItem & RecentContentResponse: estruturas auxiliares para histórico MOCK.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, ConfigDict


class ContentGenerationRequest(BaseModel):
    """Request para geração de conteúdo."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mainTopic: str = Field(..., description="Tópico principal")
    audience: Optional[str] = Field(None, description="Audiência alvo")
    contentType: Optional[str] = Field(None, description="Tipo de conteúdo (ou duração, conforme geração)")
    contentTone: Optional[str] = Field(None, description="Tom do conteúdo")
    generationType: Literal["titulos", "roteiros", "episodios"] = Field(
        ..., description="Tipo de geração"
    )


class ContentMetadata(BaseModel):
    """Metadados do conteúdo gerado (campos opcionais)."""
    # Config: permitir chaves extras (forward-compat)
    model_config = ConfigDict(extra="allow")

    # --- Métricas para TÍTULOS ---
    engagement_potential: Optional[float] = None
    seo_score: Optional[float] = None
    trend_relevance: Optional[float] = None
    relevance: Optional[float] = None
    len_ok: Optional[float] = None
    has_number: Optional[bool] = None
    has_brackets: Optional[bool] = None
    starts_strong: Optional[bool] = None
    originality: Optional[float] = None
    engagement_factors: Optional[Dict[str, Any]] = None
    seo_factors: Optional[Dict[str, Any]] = None
    trend_factors: Optional[Dict[str, Any]] = None

    # --- Métricas para ROTEIROS ---
    word_count: Optional[int] = None
    estimated_duration: Optional[str] = None
    estimated_duration_range: Optional[Dict[str, Any]] = None  # {wpm_min, wpm_max, min_minutes, max_minutes, words}
    topic: Optional[str] = None
    timeline_total_seconds: Optional[int] = None
    timing_accuracy: Optional[int] = None
    structure: Optional[Dict[str, Any]] = None  # {has_hook, has_intro, has_conclusion}
    sections: Optional[List[Dict[str, Any]]] = None
    readability_score: Optional[int] = None

    # --- Métricas para EPISÓDIOS ---
    episode_title: Optional[str] = None
    series_type: Optional[str] = None
    episode_number: Optional[str] = None
    completeness_score: Optional[int] = None
    detail_score: Optional[int] = None
    sections_found: Optional[int] = None
    total_sections: Optional[int] = None

    # --- Dados de geração (runtime) ---
    generation_time: Optional[float] = None
    model_used: Optional[str] = None
    generation_attempts: Optional[int] = None
    request_timestamp: Optional[int] = None
    selected_model: Optional[str] = None
    needs_review: Optional[bool] = None

    # --- Campo aberto para extensões ---
    extra: Optional[Dict[str, Any]] = None


class GeneratedContentItem(BaseModel):
    """Item de conteúdo gerado."""
    content: str
    score: int = Field(ge=0, le=100, description="Score 0-100 calculado no backend")
    metadata: Optional[ContentMetadata] = None


class ContentGenerationResponse(BaseModel):
    """Envelope de resposta da geração de conteúdo."""
    success: bool
    message: str
    data: List[GeneratedContentItem]


# --- Mock data para gerações recentes (temporário) ---
class MockRecentItem(BaseModel):
    """Item mock para histórico (para testes/UX)."""
    id: str
    type: str
    title: str
    content: str
    score: float
    status: str
    date: str
    description: Optional[str] = None


class RecentContentResponse(BaseModel):
    """Resposta mock com conteúdo recente."""
    success: bool
    message: str
    data: List[MockRecentItem]
