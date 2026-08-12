# app/schemas/youtube_trends.py - Versão simplificada para teste
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class YouTubeVideoBase(BaseModel):
    """Schema base para vídeos do YouTube"""
    id: str = Field(..., description="ID único do vídeo")
    title: str = Field(..., description="Título do vídeo")
    channel_title: str = Field(..., description="Nome do canal")
    channel_id: str = Field(..., description="ID do canal")
    published_at: str = Field(..., description="Data de publicação")
    view_count: int = Field(..., description="Número de visualizações")
    like_count: Optional[int] = Field(None, description="Número de likes")
    comment_count: Optional[int] = Field(None, description="Número de comentários")
    duration: Optional[str] = Field(None, description="Duração do vídeo")
    thumbnail_url: str = Field(..., description="URL da thumbnail")
    description: str = Field(..., description="Descrição do vídeo")
    category_id: str = Field(..., description="ID da categoria")
    category_name: Optional[str] = Field(None, description="Nome da categoria")
    tags: List[str] = Field(default=[], description="Tags do vídeo")

class YouTubeTrendingVideo(YouTubeVideoBase):
    """Schema para vídeos em trending"""
    trending_rank: int = Field(..., description="Posição no ranking de trends")
    trending_score: Optional[float] = Field(None, description="Score de tendência calculado")

class YouTubeTrendsResponse(BaseModel):
    """Schema de resposta para trends do YouTube"""
    videos: List[YouTubeTrendingVideo]
    region_code: str = Field(default="BR", description="Código da região")
    category: Optional[str] = Field(None, description="Categoria filtrada")
    total_results: int = Field(..., description="Total de resultados")
    fetched_at: datetime = Field(..., description="Timestamp da busca")
    next_page_token: Optional[str] = Field(None, description="Token para próxima página")

class YouTubeTrendsFilter(BaseModel):
    """Schema para filtros de busca"""
    region_code: str = Field(default="BR", description="Código da região (BR, US, etc)")
    category_id: Optional[str] = Field(None, description="ID da categoria do YouTube")
    max_results: int = Field(default=50, ge=1, le=50, description="Máximo de resultados")
    chart: str = Field(default="mostPopular", description="Tipo de chart (mostPopular)")
    
class YouTubeCategoryResponse(BaseModel):
    """Schema para categorias do YouTube"""
    id: str
    name: str
    assignable: bool = True

class YouTubeCategoriesResponse(BaseModel):
    """Schema de resposta para lista de categorias"""
    categories: List[YouTubeCategoryResponse]
    region_code: str = Field(default="BR")

# Schemas para análise de tendências
class TrendAnalysis(BaseModel):
    """Schema para análise de uma tendência específica"""
    keyword: str = Field(..., description="Palavra-chave analisada")
    total_videos: int = Field(..., description="Total de vídeos relacionados")
    avg_views: float = Field(..., description="Média de visualizações")
    avg_engagement: float = Field(..., description="Taxa de engajamento média")
    top_channels: List[str] = Field(..., description="Top canais nesta tendência")
    growth_rate: Optional[float] = Field(None, description="Taxa de crescimento")

class TrendAnalysisResponse(BaseModel):
    """Schema de resposta para análise de tendências"""
    analyses: List[TrendAnalysis]
    generated_at: datetime = Field(..., description="Timestamp da análise")
    period: str = Field(..., description="Período analisado")

# Request schemas
class YouTubeTrendsRequest(BaseModel):
    """Schema para requisição de trends"""
    region_code: str = Field(default="BR")
    category_id: Optional[str] = None
    max_results: int = Field(default=25, ge=1, le=50)

class TrendKeywordRequest(BaseModel):
    """Schema para busca por palavra-chave"""
    keyword: str = Field(..., min_length=2, max_length=100)
    region_code: str = Field(default="BR")
    max_results: int = Field(default=20, ge=1, le=50)
    order: str = Field(default="relevance")