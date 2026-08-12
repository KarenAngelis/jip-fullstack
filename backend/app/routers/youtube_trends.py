# app/routers/youtube_trends.py
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
import logging
from datetime import datetime

from ..dependencies.auth import get_current_active_user  # Usando sua estrutura
from ..schemas.auth_schema import UserResponse  # Usando seu schema
from ..schemas.youtube_trends import (
    YouTubeTrendsResponse,
    YouTubeTrendingVideo,
    YouTubeCategoriesResponse,
    YouTubeCategoryResponse,
    YouTubeTrendsRequest,
    TrendKeywordRequest,
    TrendAnalysisResponse
)
from ..services.youtube_trends_service import YouTubeTrendsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/youtube", tags=["YouTube Trends"])

# Instância do serviço
try:
    youtube_service = YouTubeTrendsService()
except ValueError as e:
    logger.warning(f"YouTube service não inicializado: {e}")
    youtube_service = None

@router.get("/trending", response_model=YouTubeTrendsResponse)
async def get_trending_videos(
    region_code: str = Query(default="BR", description="Código da região (BR, US, etc)"),
    category_id: Optional[str] = Query(None, description="ID da categoria do YouTube"),
    max_results: int = Query(default=25, ge=1, le=50, description="Máximo de resultados"),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Busca vídeos em trending do YouTube para uma região específica
    
    - **region_code**: Código do país (BR, US, GB, etc)
    - **category_id**: Filtrar por categoria específica (opcional)
    - **max_results**: Número máximo de vídeos (1-50)
    """
    if not youtube_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YouTube API não está configurada. Verifique YOUTUBE_API_KEY"
        )
    
    try:
        logger.info(f"Buscando {max_results} vídeos trending para região {region_code}")
        
        result = await youtube_service.get_trending_videos(
            region_code=region_code,
            category_id=category_id,
            max_results=max_results
        )
        
        logger.info(f"Encontrados {result.total_results} vídeos trending")
        return result
        
    except Exception as e:
        logger.error(f"Erro ao buscar trending videos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar vídeos trending: {str(e)}"
        )

@router.get("/categories", response_model=YouTubeCategoriesResponse)
async def get_video_categories(
    region_code: str = Query(default="BR", description="Código da região"),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Lista todas as categorias de vídeo disponíveis para uma região
    
    - **region_code**: Código do país (BR, US, GB, etc)
    """
    if not youtube_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YouTube API não está configurada"
        )
    
    try:
        logger.info(f"Buscando categorias para região {region_code}")
        
        categories = await youtube_service.get_video_categories(region_code=region_code)
        
        return YouTubeCategoriesResponse(
            categories=categories,
            region_code=region_code
        )
        
    except Exception as e:
        logger.error(f"Erro ao buscar categorias: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar categorias: {str(e)}"
        )

@router.get("/search-trending", response_model=List[YouTubeTrendingVideo])
async def search_trending_by_theme(
    theme: str = Query(..., min_length=3, max_length=200, description="Tema ou título para buscar (ex: 'casamento em 2025')"),
    region_code: str = Query(default="BR", description="Código da região"),
    max_results: int = Query(default=20, ge=1, le=50, description="Máximo de resultados"),
    order: str = Query(default="relevance", regex="^(relevance|date|rating|viewCount|title)$", 
                      description="Ordem dos resultados"),
    published_after: Optional[str] = Query(None, description="Buscar apenas vídeos após esta data (YYYY-MM-DD)"),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Busca vídeos trending por tema específico
    
    - **theme**: Tema ou título personalizado (ex: "casamento em 2025", "tendências moda verão")
    - **region_code**: Código do país (BR, US, etc)
    - **max_results**: Número máximo de vídeos (1-50)
    - **order**: Ordenação (relevance, date, rating, viewCount, title)
    - **published_after**: Data mínima de publicação (opcional)
    
    Exemplo: GET /api/youtube/search-trending?theme=casamento%202025&max_results=15
    """
    if not youtube_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YouTube API não está configurada"
        )
    
    try:
        logger.info(f"Buscando vídeos trending para tema: '{theme}'")
        
        videos = await youtube_service.search_trending_by_theme(
            theme=theme,
            region_code=region_code,
            max_results=max_results,
            order=order,
            published_after=published_after
        )
        
        logger.info(f"Encontrados {len(videos)} vídeos trending para tema '{theme}'")
        return videos
        
    except Exception as e:
        logger.error(f"Erro ao buscar vídeos por tema: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar vídeos por tema: {str(e)}"
        )
async def search_videos_by_keyword(
    keyword: str = Query(..., min_length=2, max_length=100, description="Palavra-chave para buscar"),
    region_code: str = Query(default="BR", description="Código da região"),
    max_results: int = Query(default=20, ge=1, le=50, description="Máximo de resultados"),
    order: str = Query(default="relevance", regex="^(relevance|date|rating|viewCount|title)$", 
                      description="Ordem dos resultados"),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Busca vídeos por palavra-chave
    
    - **keyword**: Termo para pesquisar
    - **region_code**: Código do país
    - **max_results**: Número máximo de resultados (1-50)
    - **order**: Ordenação (relevance, date, rating, viewCount, title)
    """
    if not youtube_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YouTube API não está configurada"
        )
    
    try:
        logger.info(f"Buscando vídeos para palavra-chave: '{keyword}'")
        
        videos = await youtube_service.search_videos_by_keyword(
            keyword=keyword,
            region_code=region_code,
            max_results=max_results,
            order=order
        )
        
        logger.info(f"Encontrados {len(videos)} vídeos para '{keyword}'")
        return videos
        
    except Exception as e:
        logger.error(f"Erro ao buscar vídeos por palavra-chave: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar vídeos: {str(e)}"
        )

@router.post("/trending/bulk", response_model=YouTubeTrendsResponse)
async def get_trending_videos_bulk(
    request: YouTubeTrendsRequest,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Busca vídeos trending usando POST com parâmetros no body
    
    Útil para requisições mais complexas ou quando há muitos parâmetros
    """
    if not youtube_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YouTube API não está configurada"
        )
    
    try:
        result = await youtube_service.get_trending_videos(
            region_code=request.region_code,
            category_id=request.category_id,
            max_results=request.max_results
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Erro ao buscar trending videos (bulk): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar vídeos: {str(e)}"
        )

@router.post("/search/bulk", response_model=List[YouTubeTrendingVideo])
async def search_videos_bulk(
    request: TrendKeywordRequest,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Busca vídeos por palavra-chave usando POST
    """
    if not youtube_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YouTube API não está configurada"
        )
    
    try:
        videos = await youtube_service.search_videos_by_keyword(
            keyword=request.keyword,
            region_code=request.region_code,
            max_results=request.max_results,
            order=request.order
        )
        
        return videos
        
    except Exception as e:
        logger.error(f"Erro ao buscar vídeos (bulk): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar vídeos: {str(e)}"
        )

@router.post("/analyze", response_model=TrendAnalysisResponse)
async def analyze_trending_keywords(
    keywords: List[str] = Query(..., description="Lista de palavras-chave para analisar"),
    region_code: str = Query(default="BR", description="Código da região"),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Analisa múltiplas palavras-chave para identificar tendências
    
    - **keywords**: Lista de termos para analisar
    - **region_code**: Código do país
    
    Retorna análise comparativa das tendências
    """
    if not youtube_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YouTube API não está configurada"
        )
    
    if len(keywords) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Máximo de 10 palavras-chave por análise"
        )
    
    try:
        logger.info(f"Analisando {len(keywords)} palavras-chave: {keywords}")
        
        analysis = await youtube_service.analyze_trending_keywords(
            keywords=keywords,
            region_code=region_code
        )
        
        logger.info(f"Análise concluída para {len(analysis.analyses)} termos")
        return analysis
        
    except Exception as e:
        logger.error(f"Erro ao analisar palavras-chave: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na análise: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """Verifica se a API do YouTube está configurada e funcionando"""
    if not youtube_service:
        return {
            "status": "error",
            "message": "YouTube API não configurada",
            "configured": False,
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        # Testa uma requisição simples
        categories = await youtube_service.get_video_categories("BR")
        
        return {
            "status": "ok",
            "message": "YouTube API funcionando",
            "configured": True,
            "categories_available": len(categories),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Erro na YouTube API: {str(e)}",
            "configured": True,
            "timestamp": datetime.now().isoformat()
        }