from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List
from datetime import datetime

from ..schemas.news_schema import NewsSearchResponse, NewsArticle, NewsInsight

router = APIRouter(prefix="/news", tags=["News"])

@router.get("/search", response_model=NewsSearchResponse)
async def search_news(
    q: str = Query(..., description="Termo de busca para notícias"),
    max_results: int = Query(5, ge=1, le=20, description="Máximo de resultados"),
) -> NewsSearchResponse:
    """Busca notícias relacionadas a um termo específico"""
    try:
        articles_data = NewsSearchService.search_news(q, max_results)
        
        articles = [
            NewsArticle(
                title=article["title"],
                url=article["url"],
                description=article.get("description", ""),
                source=article["source"],
                published_date=article.get("published_date"),
                relevance_score=article.get("relevance_score", 0.5)
            )
            for article in articles_data
        ]
        
        sources_used = list(set([article.source for article in articles]))
        
        return NewsSearchResponse(
            query=q,
            total_results=len(articles),
            articles=articles,
            search_timestamp=datetime.now(),
            sources_used=sources_used
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca de notícias: {str(e)}")

@router.get("/sources")
async def get_available_sources() -> Dict[str, Any]:
    """Lista as fontes de notícias disponíveis"""
    return {
        "sources": [
            {"name": "G1", "status": "active"},
            {"name": "UOL", "status": "active"},
            {"name": "Folha", "status": "active"}
        ],
        "additional_sources": ["Google News", "Fallback Generator"],
        "total_sources": 5
    }