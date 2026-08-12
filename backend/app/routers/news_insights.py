# app/routers/news_insights.py
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
import logging
from datetime import datetime

from ..dependencies.auth import get_current_active_user
from ..schemas.auth_schema import UserResponse
from ..schemas.news_insights_schema import (
    NewsAnalysisRequest,
    NewsAnalysisResponse,
    NewsArticle,
    TrendingTopic,
    NewsTrendsDashboard,
    NewsSourcesResponse,
    NewsCategory,
    NewsInsight
)
from ..services.news_insights_service import NewsInsightsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news-insights", tags=["News & Insights"])

# Instância do serviço
news_service = NewsInsightsService()

@router.get("/dashboard", response_model=NewsTrendsDashboard)
async def get_news_dashboard(
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Dashboard completo de notícias e insights
    
    Retorna uma visão geral das tendências atuais, tópicos quentes,
    análise de sentimento e breaking news.
    """
    try:
        logger.info("Carregando dashboard de notícias")
        
        dashboard = await news_service.get_dashboard()
        
        logger.info(f"Dashboard carregado com {len(dashboard.trending_now)} tópicos trending")
        return dashboard
        
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao carregar dashboard: {str(e)}"
        )

@router.get("/trending", response_model=List[TrendingTopic])
async def get_trending_topics(
    limit: int = Query(default=10, ge=1, le=50, description="Número de tópicos trending"),
    category: Optional[NewsCategory] = Query(None, description="Filtrar por categoria"),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Lista tópicos trending em notícias
    
    - **limit**: Quantidade de tópicos (1-50)
    - **category**: Filtro opcional por categoria
    
    Retorna tópicos ordenados por relevância e crescimento.
    """
    try:
        logger.info(f"Buscando {limit} tópicos trending")
        
        topics = await news_service.get_trending_topics(limit=limit)
        
        # Filtra por categoria se especificada
        if category:
            topics = [t for t in topics if t.category == category]
        
        logger.info(f"Retornando {len(topics)} tópicos trending")
        return topics
        
    except Exception as e:
        logger.error(f"Erro ao buscar tópicos trending: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar tópicos: {str(e)}"
        )

@router.get("/search", response_model=List[NewsArticle])
async def search_news(
    query: str = Query(..., min_length=2, max_length=200, description="Termo de busca"),
    category: Optional[NewsCategory] = Query(None, description="Categoria específica"),
    max_results: int = Query(default=20, ge=1, le=100, description="Máximo de resultados"),
    sort_by: str = Query(default="publishedAt", regex="^(publishedAt|popularity|relevancy)$", 
                        description="Ordenação"),
    language: str = Query(default="pt", description="Idioma das notícias"),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Busca notícias por termo específico
    
    - **query**: Termo para pesquisar
    - **category**: Categoria específica (opcional)
    - **max_results**: Número máximo de resultados (1-100)
    - **sort_by**: Ordenação (publishedAt, popularity, relevancy)
    - **language**: Idioma das notícias
    
    Retorna lista de artigos com análise de sentimento e métricas.
    """
    try:
        logger.info(f"Buscando notícias para: '{query}'")
        
        articles = await news_service.search_news(
            query=query,
            category=category,
            language=language,
            max_results=max_results,
            sort_by=sort_by
        )
        
        logger.info(f"Encontradas {len(articles)} notícias para '{query}'")
        return articles
        
    except Exception as e:
        logger.error(f"Erro ao buscar notícias: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar notícias: {str(e)}"
        )

@router.post("/analyze", response_model=NewsAnalysisResponse)
async def analyze_news_topic(
    request: NewsAnalysisRequest,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Análise completa de um tópico nas notícias
    
    Realiza busca avançada e gera insights automáticos sobre o tema,
    incluindo análise de sentimento, tópicos relacionados e tendências.
    """
    try:
        logger.info(f"Iniciando análise completa para: '{request.query}'")
        
        analysis = await news_service.analyze_news(
            query=request.query,
            category=request.category,
            max_results=request.max_results
        )
        
        logger.info(f"Análise concluída: {analysis.total_results} artigos, {len(analysis.insights)} insights")
        return analysis
        
    except Exception as e:
        logger.error(f"Erro na análise de notícias: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na análise: {str(e)}"
        )

@router.get("/sources", response_model=NewsSourcesResponse)
async def get_news_sources(
    category: Optional[NewsCategory] = Query(None, description="Filtrar por categoria"),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Lista fontes de notícias disponíveis
    
    Retorna informações sobre fontes confiáveis, incluindo
    scores de confiabilidade e categorias cobertas.
    """
    try:
        logger.info("Listando fontes de notícias")
        
        sources_response = await news_service.get_news_sources(category=category)
        
        logger.info(f"Retornando {sources_response.total_sources} fontes")
        return sources_response
        
    except Exception as e:
        logger.error(f"Erro ao listar fontes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar fontes: {str(e)}"
        )

@router.get("/categories")
async def get_news_categories(
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Lista categorias de notícias disponíveis
    
    Retorna todas as categorias suportadas pelo sistema.
    """
    return {
        "categories": [
            {
                "value": category.value,
                "label": category.value.title(),
                "description": f"Notícias relacionadas a {category.value}"
            }
            for category in NewsCategory
        ],
        "total": len(NewsCategory)
    }

@router.get("/insights/{article_id}")
async def get_article_insights(
    article_id: str,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Gera insights específicos para um artigo
    
    Retorna análise detalhada de um artigo específico,
    incluindo sentimento, keywords e tópicos relacionados.
    """
    try:
        # Mock de insight para artigo específico
        insight = {
            "article_id": article_id,
            "sentiment_analysis": {
                "sentiment": "positive",
                "confidence": 0.85,
                "key_emotions": ["optimism", "confidence", "interest"]
            },
            "key_topics": ["tecnologia", "inovação", "brasil"],
            "entities": ["startups", "investimentos", "mercado"],
            "readability": {
                "score": 8.2,
                "level": "medium",
                "read_time_minutes": 4
            },
            "engagement_prediction": {
                "score": 75,
                "factors": ["título atrativo", "imagem presente", "fonte confiável"]
            },
            "related_trends": [
                "crescimento do setor tech",
                "investimentos em startups",
                "transformação digital"
            ]
        }
        
        return insight
        
    except Exception as e:
        logger.error(f"Erro ao gerar insights do artigo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar insights: {str(e)}"
        )

@router.get("/sentiment-analysis")
async def analyze_sentiment_trends(
    topic: str = Query(..., description="Tópico para análise"),
    days: int = Query(default=7, ge=1, le=30, description="Período em dias"),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Análise de evolução do sentimento sobre um tópico
    
    Mostra como o sentimento público sobre um tema evoluiu
    ao longo do tempo baseado nas notícias.
    """
    try:
        logger.info(f"Analisando sentimento para '{topic}' nos últimos {days} dias")
        
        # Mock de análise temporal de sentimento
        sentiment_evolution = {
            "topic": topic,
            "period_days": days,
            "overall_trend": "improving",
            "current_sentiment": "positive",
            "sentiment_score": 0.65,
            "daily_breakdown": [
                {
                    "date": "2025-01-20",
                    "sentiment": "neutral",
                    "score": 0.1,
                    "article_count": 5
                },
                {
                    "date": "2025-01-21", 
                    "sentiment": "positive",
                    "score": 0.4,
                    "article_count": 8
                },
                {
                    "date": "2025-01-22",
                    "sentiment": "positive", 
                    "score": 0.65,
                    "article_count": 12
                }
            ],
            "key_factors": [
                "Aumento de notícias positivas sobre o tema",
                "Redução de cobertura negativa",
                "Maior diversidade de fontes"
            ],
            "prediction": {
                "next_week_trend": "stable_positive",
                "confidence": 0.78
            }
        }
        
        return sentiment_evolution
        
    except Exception as e:
        logger.error(f"Erro na análise de sentimento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na análise: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """Verifica se o serviço de notícias está funcionando"""
    try:
        # Testa busca rápida
        test_articles = await news_service.search_news("brasil", max_results=1)
        
        return {
            "status": "ok",
            "message": "Serviço de notícias funcionando",
            "test_results": len(test_articles),
            "sources_available": len(news_service.brazilian_sources),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Erro no serviço: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }