# app/schemas/news_insights_schema.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class NewsCategory(str, Enum):
    """Categorias de notícias"""
    BUSINESS = "business"
    TECHNOLOGY = "technology"
    HEALTH = "health"
    SCIENCE = "science"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    GENERAL = "general"
    POLITICS = "politics"

class SentimentType(str, Enum):
    """Tipos de sentimento"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class NewsSource(BaseModel):
    """Schema para fonte da notícia"""
    id: Optional[str] = Field(None, description="ID da fonte")
    name: str = Field(..., description="Nome da fonte")
    url: Optional[HttpUrl] = Field(None, description="URL da fonte")
    reliability_score: Optional[float] = Field(None, ge=0, le=10, description="Score de confiabilidade (0-10)")

class NewsArticle(BaseModel):
    """Schema para artigo de notícia"""
    id: str = Field(..., description="ID único da notícia")
    title: str = Field(..., description="Título da notícia")
    description: Optional[str] = Field(None, description="Descrição/resumo")
    content: Optional[str] = Field(None, description="Conteúdo completo")
    url: HttpUrl = Field(..., description="URL da notícia")
    url_to_image: Optional[HttpUrl] = Field(None, description="URL da imagem")
    published_at: datetime = Field(..., description="Data de publicação")
    source: NewsSource = Field(..., description="Fonte da notícia")
    category: NewsCategory = Field(..., description="Categoria da notícia")
    
    # Análise de sentimento
    sentiment: Optional[SentimentType] = Field(None, description="Sentimento da notícia")
    sentiment_score: Optional[float] = Field(None, ge=-1, le=1, description="Score de sentimento (-1 a 1)")
    
    # Métricas de engajamento
    engagement_score: Optional[float] = Field(None, ge=0, le=100, description="Score de engajamento")
    trending_score: Optional[float] = Field(None, ge=0, le=100, description="Score de tendência")
    
    # Análise de conteúdo
    keywords: List[str] = Field(default=[], description="Palavras-chave extraídas")
    entities: List[str] = Field(default=[], description="Entidades mencionadas")
    topics: List[str] = Field(default=[], description="Tópicos identificados")
    
    # Metadados
    read_time_minutes: Optional[int] = Field(None, description="Tempo estimado de leitura")
    language: str = Field(default="pt", description="Idioma da notícia")

class NewsInsight(BaseModel):
    """Schema para insights de notícias"""
    id: str = Field(..., description="ID do insight")
    title: str = Field(..., description="Título do insight")
    description: str = Field(..., description="Descrição do insight")
    insight_type: str = Field(..., description="Tipo do insight (trend, sentiment, pattern)")
    confidence: float = Field(..., ge=0, le=1, description="Confiança do insight (0-1)")
    
    # Dados relacionados
    related_articles: List[str] = Field(default=[], description="IDs de artigos relacionados")
    keywords: List[str] = Field(default=[], description="Palavras-chave do insight")
    time_period: str = Field(..., description="Período de análise")
    
    # Métricas
    impact_score: float = Field(..., ge=0, le=100, description="Score de impacto")
    relevance_score: float = Field(..., ge=0, le=100, description="Score de relevância")
    
    created_at: datetime = Field(default_factory=datetime.now, description="Data de criação")

class TrendingTopic(BaseModel):
    """Schema para tópicos em alta"""
    topic: str = Field(..., description="Nome do tópico")
    category: NewsCategory = Field(..., description="Categoria do tópico")
    article_count: int = Field(..., description="Número de artigos")
    growth_rate: float = Field(..., description="Taxa de crescimento (%)")
    sentiment: SentimentType = Field(..., description="Sentimento geral")
    
    # Métricas
    trending_score: float = Field(..., ge=0, le=100, description="Score de tendência")
    engagement_level: str = Field(..., description="Nível de engajamento (low, medium, high)")
    
    # Dados relacionados
    key_articles: List[NewsArticle] = Field(default=[], description="Artigos principais")
    related_keywords: List[str] = Field(default=[], description="Palavras-chave relacionadas")
    
    # Temporal
    first_seen: datetime = Field(..., description="Primeira aparição")
    peak_time: Optional[datetime] = Field(None, description="Momento de pico")

class NewsAnalysisRequest(BaseModel):
    """Schema para requisição de análise de notícias"""
    query: str = Field(..., min_length=2, max_length=200, description="Termo de busca")
    category: Optional[NewsCategory] = Field(None, description="Categoria específica")
    sources: Optional[List[str]] = Field(None, description="Fontes específicas")
    language: str = Field(default="pt", description="Idioma das notícias")
    from_date: Optional[datetime] = Field(None, description="Data inicial")
    to_date: Optional[datetime] = Field(None, description="Data final")
    sort_by: str = Field(default="publishedAt", description="Ordenar por (publishedAt, popularity, relevancy)")
    max_results: int = Field(default=20, ge=1, le=100, description="Máximo de resultados")

class NewsAnalysisResponse(BaseModel):
    """Schema de resposta da análise de notícias"""
    query: str = Field(..., description="Consulta realizada")
    total_results: int = Field(..., description="Total de resultados")
    articles: List[NewsArticle] = Field(..., description="Artigos encontrados")
    insights: List[NewsInsight] = Field(default=[], description="Insights gerados")
    trending_topics: List[TrendingTopic] = Field(default=[], description="Tópicos em alta")
    
    # Análise agregada
    overall_sentiment: SentimentType = Field(..., description="Sentimento geral")
    sentiment_distribution: Dict[str, float] = Field(..., description="Distribuição de sentimento")
    
    # Temporal
    analyzed_at: datetime = Field(default_factory=datetime.now, description="Data da análise")
    time_range: str = Field(..., description="Período analisado")

class NewsSourcesResponse(BaseModel):
    """Schema para resposta de fontes disponíveis"""
    sources: List[NewsSource] = Field(..., description="Lista de fontes")
    total_sources: int = Field(..., description="Total de fontes")
    categories: List[NewsCategory] = Field(..., description="Categorias disponíveis")

class NewsTrendsDashboard(BaseModel):
    """Schema para dashboard de tendências"""
    trending_now: List[TrendingTopic] = Field(..., description="Tendências atuais")
    hot_topics: List[str] = Field(..., description="Tópicos quentes")
    sentiment_overview: Dict[str, Any] = Field(..., description="Visão geral de sentimento")
    category_breakdown: Dict[str, int] = Field(..., description="Distribuição por categoria")
    
    # Insights rápidos
    quick_insights: List[str] = Field(..., description="Insights rápidos")
    breaking_news: List[NewsArticle] = Field(default=[], description="Notícias de última hora")
    
    # Métricas temporais
    last_updated: datetime = Field(default_factory=datetime.now, description="Última atualização")
    coverage_period: str = Field(..., description="Período de cobertura")

class NewsAlertRequest(BaseModel):
    """Schema para criação de alertas de notícias"""
    name: str = Field(..., min_length=1, max_length=100, description="Nome do alerta")
    keywords: List[str] = Field(..., description="Palavras-chave para monitorar")
    categories: Optional[List[NewsCategory]] = Field(None, description="Categorias específicas")
    sources: Optional[List[str]] = Field(None, description="Fontes específicas")
    frequency: str = Field(default="daily", description="Frequência (hourly, daily, weekly)")
    sentiment_filter: Optional[SentimentType] = Field(None, description="Filtrar por sentimento")
    active: bool = Field(default=True, description="Alerta ativo")

class NewsAlert(NewsAlertRequest):
    """Schema para alerta de notícias criado"""
    id: str = Field(..., description="ID do alerta")
    user_id: str = Field(..., description="ID do usuário")
    created_at: datetime = Field(default_factory=datetime.now, description="Data de criação")
    last_triggered: Optional[datetime] = Field(None, description="Último disparo")
    trigger_count: int = Field(default=0, description="Número de disparos")