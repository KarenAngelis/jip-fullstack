# app/services/youtube_trends_service.py - Versão simplificada para teste
import os
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    HttpError = Exception

from ..schemas.youtube_trends import (
    YouTubeTrendingVideo, 
    YouTubeTrendsResponse, 
    YouTubeCategoryResponse,
    TrendAnalysis,
    TrendAnalysisResponse
)

logger = logging.getLogger(__name__)

class YouTubeTrendsService:
    """Serviço para integração com YouTube Data API v3"""
    
    def __init__(self):
        if not YOUTUBE_AVAILABLE:
            raise ValueError("googleapiclient não instalado. Install: pip install google-api-python-client")
        
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY não encontrada nas variáveis de ambiente")
        
        self.youtube = build("youtube", "v3", developerKey=self.api_key)
        self.cache = {}  # Cache simples (em produção, use Redis)
        self.cache_duration = 300  # 5 minutos
        
        # Mapeamento de categorias populares
        self.categories_map = {
            "1": "Film & Animation",
            "2": "Autos & Vehicles",
            "10": "Music",
            "15": "Pets & Animals",
            "17": "Sports",
            "19": "Travel & Events",
            "20": "Gaming",
            "22": "People & Blogs",
            "23": "Comedy",
            "24": "Entertainment",
            "25": "News & Politics",
            "26": "Howto & Style",
            "27": "Education",
            "28": "Science & Technology"
        }

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Verifica se o cache ainda é válido"""
        if cache_key not in self.cache:
            return False
        
        cached_time = self.cache[cache_key].get("timestamp", 0)
        return (datetime.now().timestamp() - cached_time) < self.cache_duration

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Recupera dados do cache se válidos"""
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]["data"]
        return None

    def _set_cache(self, cache_key: str, data: Any) -> None:
        """Armazena dados no cache"""
        self.cache[cache_key] = {
            "data": data,
            "timestamp": datetime.now().timestamp()
        }

    async def get_video_categories(self, region_code: str = "BR") -> List[YouTubeCategoryResponse]:
        """Busca categorias de vídeo disponíveis para a região"""
        cache_key = f"categories_{region_code}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        try:
            request = self.youtube.videoCategories().list(
                part="snippet",
                regionCode=region_code
            )
            response = request.execute()
            
            categories = []
            for item in response.get("items", []):
                categories.append(YouTubeCategoryResponse(
                    id=item["id"],
                    name=item["snippet"]["title"],
                    assignable=item["snippet"]["assignable"]
                ))
            
            self._set_cache(cache_key, categories)
            return categories
            
        except HttpError as e:
            logger.error(f"Erro ao buscar categorias: {e}")
            # Retorna categorias padrão em caso de erro
            default_categories = [
                YouTubeCategoryResponse(id=k, name=v) 
                for k, v in self.categories_map.items()
            ]
            return default_categories

    async def get_trending_videos(
        self, 
        region_code: str = "BR",
        category_id: Optional[str] = None,
        max_results: int = 50
    ) -> YouTubeTrendsResponse:
        """Busca vídeos em trending do YouTube"""
        
        cache_key = f"trending_{region_code}_{category_id}_{max_results}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        try:
            # Parâmetros da requisição
            params = {
                "part": "snippet,statistics,contentDetails",
                "chart": "mostPopular",
                "regionCode": region_code,
                "maxResults": min(max_results, 50)  # API limit
            }
            
            # CORREÇÃO: Validar category_id antes de adicionar
            if category_id and category_id.isdigit() and category_id in self.categories_map:
                params["videoCategoryId"] = category_id
            elif category_id:
                logger.warning(f"Category ID inválido ignorado: {category_id}")

            # Busca vídeos trending
            request = self.youtube.videos().list(**params)
            response = request.execute()
            
            videos = []
            for idx, item in enumerate(response.get("items", [])):
                snippet = item["snippet"]
                statistics = item.get("statistics", {})
                content_details = item.get("contentDetails", {})
                
                # Calcula score de tendência baseado em views, likes e comentários
                views = int(statistics.get("viewCount", 0))
                likes = int(statistics.get("likeCount", 0))
                comments = int(statistics.get("commentCount", 0))
                
                # Score simples baseado em engajamento
                trending_score = self._calculate_trending_score(views, likes, comments)
                
                video = YouTubeTrendingVideo(
                    id=item["id"],
                    title=snippet["title"],
                    channel_title=snippet["channelTitle"],
                    channel_id=snippet["channelId"],
                    published_at=snippet["publishedAt"],
                    view_count=views,
                    like_count=likes if likes > 0 else None,
                    comment_count=comments if comments > 0 else None,
                    duration=content_details.get("duration"),
                    thumbnail_url=snippet["thumbnails"]["high"]["url"],
                    description=snippet.get("description", "")[:500],  # Limita descrição
                    category_id=snippet["categoryId"],
                    category_name=self.categories_map.get(snippet["categoryId"], "Unknown"),
                    tags=snippet.get("tags", [])[:10],  # Limita tags
                    trending_rank=idx + 1,
                    trending_score=trending_score
                )
                videos.append(video)
            
            result = YouTubeTrendsResponse(
                videos=videos,
                region_code=region_code,
                category=category_id,
                total_results=len(videos),
                fetched_at=datetime.now(),
                next_page_token=response.get("nextPageToken")
            )
            
            self._set_cache(cache_key, result)
            return result
            
        except HttpError as e:
            logger.error(f"Erro ao buscar trending videos: {e}")
            raise Exception(f"Erro na API do YouTube: {str(e)}")
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            raise Exception(f"Erro interno: {str(e)}")

    def _calculate_trending_score(self, views: int, likes: int, comments: int) -> float:
        """Calcula um score de tendência baseado nas métricas do vídeo"""
        if views == 0:
            return 0.0
        
        # Taxa de engajamento (likes + comments) / views
        engagement_rate = (likes + comments) / views
        
        # Score normalizado (0-100)
        score = min(100.0, engagement_rate * 1000)
        return round(score, 2)

    async def search_trending_by_theme(
        self,
        theme: str,
        region_code: str = "BR",
        max_results: int = 20,
        order: str = "relevance",
        published_after: Optional[str] = None
    ) -> List[YouTubeTrendingVideo]:
        """
        Busca vídeos trending por tema específico
        Combina busca por palavra-chave com filtros de popularidade e data
        """
        
        try:
            # Parâmetros da busca
            search_params = {
                "part": "snippet",
                "q": theme,
                "type": "video",
                "regionCode": region_code,
                "maxResults": min(max_results, 50),
                "order": order,
                "relevanceLanguage": "pt" if region_code == "BR" else None
            }
            
            # Adiciona filtro de data se especificado
            if published_after:
                try:
                    # Converte data para formato RFC 3339
                    from datetime import datetime
                    date_obj = datetime.strptime(published_after, "%Y-%m-%d")
                    search_params["publishedAfter"] = date_obj.isoformat() + "Z"
                except ValueError:
                    logger.warning(f"Data inválida ignorada: {published_after}")
            
            # Remove parâmetros None
            search_params = {k: v for k, v in search_params.items() if v is not None}
            
            # Busca por tema
            search_request = self.youtube.search().list(**search_params)
            search_response = search_request.execute()
            
            # Coleta IDs dos vídeos encontrados
            video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
            
            if not video_ids:
                logger.info(f"Nenhum vídeo encontrado para tema: '{theme}'")
                return []
            
            # Busca detalhes completos dos vídeos
            videos_request = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            )
            videos_response = videos_request.execute()
            
            # Processa e filtra por popularidade
            videos = []
            for idx, item in enumerate(videos_response.get("items", [])):
                snippet = item["snippet"]
                statistics = item.get("statistics", {})
                content_details = item.get("contentDetails", {})
                
                views = int(statistics.get("viewCount", 0))
                likes = int(statistics.get("likeCount", 0))
                comments = int(statistics.get("commentCount", 0))
                
                # Filtra vídeos com pelo menos algum engajamento
                if views < 100:  # Filtro mínimo de qualidade
                    continue
                
                # Calcula score de trending
                trending_score = self._calculate_trending_score(views, likes, comments)
                
                # Adiciona boost para vídeos mais recentes
                try:
                    from datetime import datetime
                    pub_date = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
                    days_ago = (datetime.now().replace(tzinfo=pub_date.tzinfo) - pub_date).days
                    
                    # Boost para vídeos recentes (últimos 30 dias)
                    if days_ago <= 30:
                        trending_score *= 1.5
                    elif days_ago <= 90:
                        trending_score *= 1.2
                        
                except Exception:
                    pass  # Ignora erro de data
                
                video = YouTubeTrendingVideo(
                    id=item["id"],
                    title=snippet["title"],
                    channel_title=snippet["channelTitle"],
                    channel_id=snippet["channelId"],
                    published_at=snippet["publishedAt"],
                    view_count=views,
                    like_count=likes if likes > 0 else None,
                    comment_count=comments if comments > 0 else None,
                    duration=content_details.get("duration"),
                    thumbnail_url=snippet["thumbnails"]["high"]["url"],
                    description=snippet.get("description", "")[:500],
                    category_id=snippet["categoryId"],
                    category_name=self.categories_map.get(snippet["categoryId"], "Unknown"),
                    tags=snippet.get("tags", [])[:10],
                    trending_rank=idx + 1,
                    trending_score=round(trending_score, 2)
                )
                videos.append(video)
            
            # Ordena por score de trending (maior para menor)
            videos.sort(key=lambda v: v.trending_score, reverse=True)
            
            logger.info(f"Processados {len(videos)} vídeos trending para tema '{theme}'")
            return videos
            
        except HttpError as e:
            logger.error(f"Erro ao buscar vídeos por tema: {e}")
            raise Exception(f"Erro na API do YouTube: {str(e)}")
        except Exception as e:
            logger.error(f"Erro inesperado na busca por tema: {e}")
            raise Exception(f"Erro interno: {str(e)}")

    async def search_videos_by_keyword(
        self,
        keyword: str,
        region_code: str = "BR",
        max_results: int = 20,
        order: str = "relevance"
    ) -> List[YouTubeTrendingVideo]:
        """Busca vídeos por palavra-chave"""
        
        try:
            # Busca por palavra-chave
            search_request = self.youtube.search().list(
                part="snippet",
                q=keyword,
                type="video",
                regionCode=region_code,
                maxResults=min(max_results, 50),
                order=order
            )
            search_response = search_request.execute()
            
            # Coleta IDs dos vídeos encontrados
            video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
            
            if not video_ids:
                return []
            
            # Busca detalhes dos vídeos
            videos_request = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            )
            videos_response = videos_request.execute()
            
            videos = []
            for idx, item in enumerate(videos_response.get("items", [])):
                snippet = item["snippet"]
                statistics = item.get("statistics", {})
                content_details = item.get("contentDetails", {})
                
                views = int(statistics.get("viewCount", 0))
                likes = int(statistics.get("likeCount", 0))
                comments = int(statistics.get("commentCount", 0))
                
                video = YouTubeTrendingVideo(
                    id=item["id"],
                    title=snippet["title"],
                    channel_title=snippet["channelTitle"],
                    channel_id=snippet["channelId"],
                    published_at=snippet["publishedAt"],
                    view_count=views,
                    like_count=likes if likes > 0 else None,
                    comment_count=comments if comments > 0 else None,
                    duration=content_details.get("duration"),
                    thumbnail_url=snippet["thumbnails"]["high"]["url"],
                    description=snippet.get("description", "")[:500],
                    category_id=snippet["categoryId"],
                    category_name=self.categories_map.get(snippet["categoryId"], "Unknown"),
                    tags=snippet.get("tags", [])[:10],
                    trending_rank=idx + 1,
                    trending_score=self._calculate_trending_score(views, likes, comments)
                )
                videos.append(video)
            
            return videos
            
        except HttpError as e:
            logger.error(f"Erro ao buscar vídeos por palavra-chave: {e}")
            raise Exception(f"Erro na API do YouTube: {str(e)}")

    async def analyze_trending_keywords(
        self, 
        keywords: List[str],
        region_code: str = "BR"
    ) -> TrendAnalysisResponse:
        """Analisa múltiplas palavras-chave para identificar tendências"""
        
        analyses = []
        
        for keyword in keywords:
            try:
                videos = await self.search_videos_by_keyword(
                    keyword=keyword,
                    region_code=region_code,
                    max_results=20
                )
                
                if not videos:
                    continue
                
                # Calcula métricas
                total_videos = len(videos)
                avg_views = sum(v.view_count for v in videos) / total_videos
                avg_engagement = sum(v.trending_score for v in videos) / total_videos
                top_channels = list(set([v.channel_title for v in videos[:5]]))
                
                analysis = TrendAnalysis(
                    keyword=keyword,
                    total_videos=total_videos,
                    avg_views=round(avg_views, 2),
                    avg_engagement=round(avg_engagement, 2),
                    top_channels=top_channels,
                    growth_rate=None  # Pode ser calculado com dados históricos
                )
                analyses.append(analysis)
                
            except Exception as e:
                logger.warning(f"Erro ao analisar palavra-chave '{keyword}': {e}")
                continue
        
        return TrendAnalysisResponse(
            analyses=analyses,
            generated_at=datetime.now(),
            period="current"
        )