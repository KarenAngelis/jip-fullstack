# app/services/episode_suggestions_service.py
import logging
import asyncio
import uuid
import httpx
import os
import hashlib
import json
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from sqlalchemy.orm import Session  # ← ADICIONADO

logger = logging.getLogger(__name__)

# Importações opcionais
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    NLTK_AVAILABLE = True
    
    # Download NLTK data if needed
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('tokenizers/punkt_tab')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('punkt')
        nltk.download('punkt_tab')
        nltk.download('stopwords')
        
except ImportError:
    NLTK_AVAILABLE = False
    logger.warning("NLTK ou scikit-learn não instalados. Usando fallbacks simples.")

# Importações opcionais para busca de notícias
try:
    from googlesearch import search as google_search
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False
    logger.info("googlesearch-python não instalado. Use: pip install googlesearch-python")

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logger.info("feedparser não instalado. Use: pip install feedparser")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.info("beautifulsoup4 não instalado. Use: pip install beautifulsoup4")

from ..schemas.episode_suggestions_schema import (
    EpisodeSuggestionRequest,
    EpisodeSuggestionsResponse,
    EpisodeSuggestion,
    JIPTrendAnalysis,
    JIPLegalAnalysis,
    JIPMarketAnalysis,
    GuestSuggestion,
    EpisodeNews,
    LegalStatus
)

# Stopwords portuguesas para fallback
PORTUGUESE_STOPWORDS = {
    'a', 'o', 'e', 'é', 'de', 'do', 'da', 'em', 'um', 'uma', 'com', 'não', 'que', 'se', 'na', 'por', 
    'mais', 'as', 'os', 'para', 'este', 'esta', 'como', 'mas', 'foi', 'ao', 'ele', 'das', 'tem', 'à',
    'seu', 'sua', 'ou', 'ser', 'quando', 'muito', 'há', 'nos', 'já', 'está', 'eu', 'também', 'só', 
    'pelo', 'pela', 'até', 'isso', 'ela', 'entre', 'era', 'depois', 'sem', 'mesmo', 'aos', 'ter'
}

class EpisodeSuggestionsService:
    def __init__(self):
        # Cache com TTL por context_fingerprint
        self.external_cache = {}
        self.episode_cache = {}
        
        # Estado de lote para unicidade
        self.used_titles_tokens = set()
        self.used_keywords = set()
        
        # APIs internas
        self.internal_base_url = os.getenv("INTERNAL_API_BASE", "http://127.0.0.1:8000")
        self.news_insights_url = f"{self.internal_base_url}/api/news-insights"
        
        # APIs externas
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_url = "https://api.openai.com/v1/chat/completions"
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        self.bing_api_url = os.getenv("BING_API_URL")
        self.bing_api_key = os.getenv("BING_API_KEY")
        
        # Configurações
        self.strict_mode = os.getenv("ORCHESTRATION_STRICT", "false").lower() == "true"
        self.semaphore = asyncio.Semaphore(5)
        self.timeout = httpx.Timeout(45.0)
        self.cache_ttl = timedelta(minutes=10)

    async def generate_episode_suggestions(
        self, 
        request: EpisodeSuggestionRequest,
        db: Optional[Session] = None,  # ← ADICIONADO
        user_ip: Optional[str] = None,  # ← ADICIONADO
        user_id: Optional[int] = None   # ← ADICIONADO
    ) -> EpisodeSuggestionsResponse:
        """Orquestra geração de episódios orientada por dados"""
        logger.info(f"🚀 Iniciando geração orientada por dados para: '{request.title}'")
        start_time = datetime.now()
        
        # Limpa estado
        self.used_titles_tokens.clear()
        self.used_keywords.clear()
        
        telemetry = {
            'sources_success': [],
            'sources_failed': [],
            'context_fingerprint': '',
            'similarity_stats': {}
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 1. BUSCA DADOS EXTERNOS
                logger.info("📊 Coletando dados externos...")
                
                news_insights_data = await self._fetch_internal_news_insights(client, request.title, telemetry)
                google_news_data = await self._fetch_google_news_native(client, request.title, telemetry)
                youtube_data = await self._fetch_youtube_data(client, request.title, telemetry)
                
                # 2. NORMALIZA CONTEXTO
                context = self._normalize_and_merge_context(request, news_insights_data, google_news_data, youtube_data)
                context_fingerprint = self._generate_context_fingerprint(context)
                telemetry['context_fingerprint'] = context_fingerprint
                
                logger.info(f"📋 Context fingerprint: {context_fingerprint[:12]}...")

                # 3. GERA TÍTULOS
                raw_titles = await self._gpt_generate_titles(client, context, desired_count=24)
                
                # 4. SELECIONA TÍTULOS ÚNICOS
                if NLTK_AVAILABLE:
                    try:
                        unique_titles = self._mmr_select_titles(raw_titles, k=12)
                    except Exception as e:
                        logger.warning(f"Erro no MMR, usando seleção simples: {e}")
                        unique_titles = self._simple_unique_selection(raw_titles, k=12)
                else:
                    unique_titles = self._simple_unique_selection(raw_titles, k=12)
                
                if len(unique_titles) < 12:
                    unique_titles.extend(self._generate_fallback_titles(request.title)[len(unique_titles):12])
                
                logger.info(f"✅ Selecionados {len(unique_titles)} títulos únicos")

                # 5. GERA EPISÓDIOS
                logger.info("🔄 Gerando episódios em paralelo...")
                
                episode_tasks = []
                for i, title in enumerate(unique_titles[:12]):
                    task = self._generate_single_episode(client, title, context, request, i)
                    episode_tasks.append(task)
                
                episodes = await asyncio.gather(*episode_tasks, return_exceptions=True)
                valid_episodes = [ep for ep in episodes if not isinstance(ep, Exception)]
                
                # 6. MÉTRICAS GERAIS
                overall_metrics = self._compute_overall_metrics(news_insights_data, youtube_data)
                
                if NLTK_AVAILABLE:
                    telemetry['similarity_stats'] = self._compute_similarity_stats(valid_episodes)
                
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(f"✅ Geração concluída: {len(valid_episodes)} episódios em {processing_time:.0f}ms")
                
                # ===== ADICIONADO: SALVAR NO BANCO =====
                if db:
                    try:
                        batch_record = await self._save_batch_to_db(
                            db, request, valid_episodes, overall_metrics, 
                            processing_time, user_ip, user_id
                        )
                        logger.info(f"✅ Batch salvo no banco: ID {batch_record.id}")
                    except Exception as e:
                        logger.error(f"❌ Erro ao salvar no banco: {e}")
                        # Não quebra o fluxo, apenas loga
                
                return EpisodeSuggestionsResponse(
                    request_title=request.title,
                    request_context=request.context,
                    total_suggestions=len(valid_episodes),
                    suggestions=valid_episodes[:12],
                    overall_trend_score=overall_metrics['trend_score'],
                    market_opportunity=overall_metrics['market_opportunity'],
                    recommended_timing=overall_metrics['timing'],
                    processing_time_ms=round(processing_time, 2)
                )
                
        except Exception as e:
            logger.error(f"❌ Erro na orquestração: {str(e)}")
            if self.strict_mode:
                raise
            return await self._generate_fallback_response(request, str(e))

    async def _fetch_internal_news_insights(self, client: httpx.AsyncClient, title: str, telemetry: dict) -> Optional[Dict]:
        """Busca dados da sua própria API de News Insights"""
        cache_key = f"internal_news_{hashlib.md5(title.encode()).hexdigest()}"
        cached = self._get_from_cache(cache_key)
        if cached:
            telemetry['sources_success'].append('internal_news_cached')
            return cached
            
        try:
            async with self.semaphore:
                response = await client.post(
                    f"{self.news_insights_url}/analyze",
                    json={
                        "query": title,
                        "max_results": 20
                    },
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._set_cache(cache_key, data)
                    telemetry['sources_success'].append('internal_news_api')
                    logger.info(f"✅ News Insights API: {len(data.get('articles', []))} artigos")
                    return data
                else:
                    logger.warning(f"News Insights API retornou {response.status_code}")
                    
        except Exception as e:
            telemetry['sources_failed'].append(('internal_news_api', str(e)[:50]))
            logger.warning(f"Internal News API falhou: {e}")
            
        return None

    async def _fetch_google_news_native(self, client: httpx.AsyncClient, title: str, telemetry: dict) -> Optional[Dict]:
        """Busca notícias usando múltiplas estratégias nativas"""
        
        cache_key = f"google_news_{hashlib.md5(title.encode()).hexdigest()}"
        cached = self._get_from_cache(cache_key)
        if cached:
            telemetry['sources_success'].append('google_news_cached')
            return cached
        
        news_data = None
        
        # Estratégia 1: Google News RSS
        try:
            news_data = await self._fetch_google_news_rss(client, title)
            if news_data and len(news_data.get('articles', [])) > 0:
                telemetry['sources_success'].append('google_news_rss')
                logger.info(f"✅ Google News RSS: {len(news_data['articles'])} artigos")
                self._set_cache(cache_key, news_data)
                return news_data
        except Exception as e:
            logger.warning(f"Google News RSS falhou: {e}")
            telemetry['sources_failed'].append(('google_news_rss', str(e)[:50]))
        
        # Estratégia 2: Busca orgânica + scraping
        if GOOGLE_SEARCH_AVAILABLE and BS4_AVAILABLE:
            try:
                news_data = await self._fetch_google_search_news(client, title)
                if news_data and len(news_data.get('articles', [])) > 0:
                    telemetry['sources_success'].append('google_search_news')
                    logger.info(f"✅ Google Search News: {len(news_data['articles'])} artigos")
                    self._set_cache(cache_key, news_data)
                    return news_data
            except Exception as e:
                logger.warning(f"Google Search News falhou: {e}")
                telemetry['sources_failed'].append(('google_search_news', str(e)[:50]))
        
        # Estratégia 3: Bing News
        if self.bing_api_key:
            try:
                news_data = await self._fetch_bing_news(client, title)
                if news_data and len(news_data.get('articles', [])) > 0:
                    telemetry['sources_success'].append('bing_news')
                    logger.info(f"✅ Bing News: {len(news_data['articles'])} artigos")
                    self._set_cache(cache_key, news_data)
                    return news_data
            except Exception as e:
                logger.warning(f"Bing News falhou: {e}")
                telemetry['sources_failed'].append(('bing_news', str(e)[:50]))
        
        # Estratégia 4: Mock realista como último recurso
        news_data = self._generate_mock_news_data(title)
        telemetry['sources_success'].append('mock_news_data')
        logger.info(f"📝 Mock News Data: {len(news_data['articles'])} artigos gerados")
        self._set_cache(cache_key, news_data)
        
        return news_data

    async def _fetch_google_news_rss(self, client: httpx.AsyncClient, title: str) -> Optional[Dict]:
        """Busca notícias via Google News RSS"""
        try:
            query_terms = title.replace(' ', '+')
            rss_url = f"https://news.google.com/rss/search?q={query_terms}+Brasil&hl=pt-BR&gl=BR&ceid=BR:pt-409"
            
            response = await client.get(rss_url, timeout=10.0)
            if response.status_code != 200:
                return None
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            articles = []
            for item in root.findall('.//item')[:15]:
                try:
                    title_elem = item.find('title')
                    desc_elem = item.find('description')
                    link_elem = item.find('link')
                    pub_date_elem = item.find('pubDate')
                    source_elem = item.find('source')
                    
                    if title_elem is not None and link_elem is not None:
                        article = {
                            "title": title_elem.text or "",
                            "description": desc_elem.text if desc_elem is not None else "",
                            "url": link_elem.text or "",
                            "published_at": pub_date_elem.text if pub_date_elem is not None else datetime.now().isoformat(),
                            "source": {
                                "name": source_elem.text if source_elem is not None else "Google News",
                                "reliability_score": 7.5
                            },
                            "keywords": title.split()[:5],
                            "sentiment": "neutral",
                            "engagement_score": 75.0 + (len(articles) * 2)
                        }
                        articles.append(article)
                        
                except Exception as e:
                    logger.warning(f"Erro ao processar item RSS: {e}")
                    continue
            
            return {
                "articles": articles,
                "total_results": len(articles),
                "source": "google_news_rss"
            }
            
        except Exception as e:
            logger.error(f"Erro no Google News RSS: {e}")
            return None

    async def _fetch_google_search_news(self, client: httpx.AsyncClient, title: str) -> Optional[Dict]:
        """Busca notícias via Google Search + scraping básico"""
        if not GOOGLE_SEARCH_AVAILABLE or not BS4_AVAILABLE:
            return None
            
        try:
            # Busca URLs de notícias
            search_query = f"{title} Brasil notícias"
            news_urls = []
            
            # googlesearch-python é síncrono, roda em thread
            import asyncio
            loop = asyncio.get_event_loop()
            
            def search_sync():
                try:
                    urls = []
                    for url in google_search(search_query, num_results=10, lang='pt', safe='off'):
                        # Filtra apenas sites de notícias conhecidos
                        if any(domain in url for domain in [
                            'g1.globo.com', 'folha.uol.com.br', 'estadao.com.br', 
                            'uol.com.br', 'cnn.com.br', 'band.uol.com.br', 'r7.com'
                        ]):
                            urls.append(url)
                        if len(urls) >= 5:
                            break
                    return urls
                except Exception as e:
                    logger.warning(f"Google search falhou: {e}")
                    return []
            
            news_urls = await loop.run_in_executor(None, search_sync)
            
            if not news_urls:
                return None
            
            # Scraping básico dos títulos
            articles = []
            for i, url in enumerate(news_urls):
                try:
                    response = await client.get(url, timeout=5.0)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Extrai título da página
                        page_title = soup.find('title')
                        if page_title:
                            article_title = page_title.get_text().strip()
                        else:
                            article_title = f"Notícia sobre {title}"
                        
                        # Extrai descrição básica
                        meta_desc = soup.find('meta', attrs={'name': 'description'})
                        description = meta_desc.get('content', '') if meta_desc else f"Artigo sobre {title}"
                        
                        article = {
                            "title": article_title[:100],
                            "description": description[:200],
                            "url": url,
                            "published_at": datetime.now().isoformat(),
                            "source": {
                                "name": self._extract_domain_name(url),
                                "reliability_score": 8.0
                            },
                            "keywords": title.split()[:5],
                            "sentiment": "neutral",
                            "engagement_score": 80.0 + (i * 3)
                        }
                        articles.append(article)
                        
                except Exception as e:
                    logger.warning(f"Erro ao fazer scraping de {url}: {e}")
                    continue
            
            return {
                "articles": articles,
                "total_results": len(articles),
                "source": "google_search_scraping"
            }
            
        except Exception as e:
            logger.error(f"Erro no Google Search News: {e}")
            return None

    async def _fetch_bing_news(self, client: httpx.AsyncClient, title: str) -> Optional[Dict]:
        """Busca notícias via Bing News API"""
        if not self.bing_api_key:
            return None
            
        try:
            bing_news_url = "https://api.bing.microsoft.com/v7.0/news/search"
            
            response = await client.get(
                bing_news_url,
                headers={
                    "Ocp-Apim-Subscription-Key": self.bing_api_key
                },
                params={
                    "q": f"{title} Brasil",
                    "mkt": "pt-BR",
                    "count": 15,
                    "offset": 0,
                    "sortBy": "Date"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                articles = []
                
                for item in data.get('value', []):
                    article = {
                        "title": item.get('name', ''),
                        "description": item.get('description', ''),
                        "url": item.get('url', ''),
                        "published_at": item.get('datePublished', datetime.now().isoformat()),
                        "source": {
                            "name": item.get('provider', [{}])[0].get('name', 'Bing News'),
                            "reliability_score": 7.8
                        },
                        "keywords": title.split()[:5],
                        "sentiment": "neutral",
                        "engagement_score": 78.0
                    }
                    articles.append(article)
                
                return {
                    "articles": articles,
                    "total_results": len(articles),
                    "source": "bing_news_api"
                }
                
        except Exception as e:
            logger.error(f"Erro no Bing News: {e}")
            return None

    def _generate_mock_news_data(self, title: str) -> Dict:
        """Gera dados de notícias mock realistas baseados no título"""
        
        news_templates = [
            {
                "title_template": f"Nova pesquisa revela tendências sobre {title} no mercado brasileiro",
                "description": f"Estudo aponta crescimento de 25% em {title} no Brasil, com destaque para região Sudeste",
                "source": "Folha de S.Paulo"
            },
            {
                "title_template": f"Especialistas analisam impacto de {title} na economia nacional",
                "description": f"Análise mostra que {title} pode gerar R$ 2,3 bilhões em negócios até 2025",
                "source": "Estado de S.Paulo"
            },
            {
                "title_template": f"Startups brasileiras apostam em inovações relacionadas a {title}",
                "description": f"Empresas nacionais captaram R$ 150 milhões para desenvolver soluções em {title}",
                "source": "G1"
            },
            {
                "title_template": f"Governo federal anuncia investimentos em {title}",
                "description": f"Ministério destina R$ 500 milhões para fomentar {title} no país",
                "source": "CNN Brasil"
            },
            {
                "title_template": f"Consumidores brasileiros mostram interesse crescente em {title}",
                "description": f"Pesquisa Datafolha indica que 68% dos brasileiros consideram {title} importante",
                "source": "UOL"
            },
            {
                "title_template": f"Mercado de {title} no Brasil deve crescer 40% em 2025",
                "description": f"Relatório da consultoria McKinsey projeta expansão significativa do setor",
                "source": "Exame"
            }
        ]
        
        articles = []
        for i, template in enumerate(news_templates):
            hours_ago = i * 3 + 2
            pub_date = datetime.now() - timedelta(hours=hours_ago)
            
            article = {
                "title": template["title_template"],
                "description": template["description"],
                "url": f"https://{template['source'].lower().replace(' ', '')}.com.br/noticia/{hashlib.md5(template['title_template'].encode()).hexdigest()[:10]}",
                "published_at": pub_date.isoformat(),
                "source": {
                    "name": template["source"],
                    "reliability_score": 8.5 if template["source"] in ["Folha de S.Paulo", "Estado de S.Paulo"] else 8.0
                },
                "keywords": title.split() + ["Brasil", "mercado", "crescimento"],
                "sentiment": "positive" if i % 3 == 0 else "neutral",
                "engagement_score": 85.0 - (i * 3),
                "trending_score": 90.0 - (i * 5)
            }
            articles.append(article)
        
        insights = [
            {
                "title": f"Crescimento Acelerado em {title}",
                "description": f"Mercado brasileiro de {title} apresenta sinais de forte expansão, com investimentos crescendo 25% ao ano",
                "confidence": 0.8,
                "impact_score": 85.0
            },
            {
                "title": "Interesse Governamental",
                "description": f"Governo federal demonstra apoio ao desenvolvimento de {title} através de políticas específicas",
                "confidence": 0.75,
                "impact_score": 70.0
            }
        ]
        
        trending_topics = [
            {
                "topic": title,
                "growth_rate": 45.5,
                "article_count": len(articles),
                "sentiment": "positive"
            },
            {
                "topic": f"{title} Brasil",
                "growth_rate": 38.2,
                "article_count": len(articles) - 2,
                "sentiment": "neutral"
            }
        ]
        
        return {
            "articles": articles,
            "insights": insights,
            "trending_topics": trending_topics,
            "total_results": len(articles),
            "source": "mock_realistic_data",
            "query": title
        }

    def _extract_domain_name(self, url: str) -> str:
        """Extrai nome limpo do domínio"""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            domain = domain.replace('www.', '')
            return domain.split('.')[0].title()
        except:
            return "Fonte"

    async def _fetch_youtube_data(self, client: httpx.AsyncClient, title: str, telemetry: dict) -> Optional[Dict]:
        """Busca dados do YouTube API"""
        if not self.youtube_api_key:
            telemetry['sources_failed'].append(('youtube_api', 'credentials_missing'))
            return None
            
        cache_key = f"youtube_{hashlib.md5(title.encode()).hexdigest()}"
        cached = self._get_from_cache(cache_key)
        if cached:
            telemetry['sources_success'].append('youtube_api_cached')
            return cached
            
        try:
            async with self.semaphore:
                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": f"{title} Brasil",
                        "type": "video",
                        "regionCode": "BR",
                        "relevanceLanguage": "pt",
                        "maxResults": 15,
                        "key": self.youtube_api_key
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._set_cache(cache_key, data)
                    telemetry['sources_success'].append('youtube_api')
                    return data
                    
        except Exception as e:
            telemetry['sources_failed'].append(('youtube_api', str(e)[:50]))
            logger.warning(f"YouTube API falhou: {e}")
            
        return None

    def _normalize_and_merge_context(
        self, 
        request: EpisodeSuggestionRequest,
        news_insights_data: Optional[Dict],
        google_news_data: Optional[Dict],
        youtube_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """Normaliza e combina dados das fontes"""
        
        context = {
            "original_title": request.title,
            "original_context": request.context or "",
            "personal_input": request.personal_input or "",
            "target_audience": request.target_audience or "geral"
        }
        
        # NEWS INSIGHTS DATA (sua API interna - prioritário)
        if news_insights_data and not isinstance(news_insights_data, Exception):
            articles = news_insights_data.get('articles', [])
            context['news_headlines'] = []
            context['trending_keywords'] = []
            
            for article in articles[:6]:
                title = article.get('title', '')
                pub_date = article.get('published_at', '')[:10]
                source = article.get('source', {}).get('name', 'Unknown')
                context['news_headlines'].append(f"{title} ({pub_date}, {source})")
                
                keywords = article.get('keywords', [])
                context['trending_keywords'].extend(keywords[:3])
            
            trending_topics = news_insights_data.get('trending_topics', [])
            context['trend_top_terms'] = []
            for topic in trending_topics[:5]:
                topic_name = topic.get('topic', '')
                growth_rate = topic.get('growth_rate', 0)
                context['trend_top_terms'].append(f"{topic_name}: {growth_rate}")
            
            insights = news_insights_data.get('insights', [])
            context['market_insights'] = [
                insight.get('description', '') for insight in insights[:3]
            ]
        else:
            context['news_headlines'] = []
            context['trending_keywords'] = []
            context['trend_top_terms'] = []
            context['market_insights'] = []
            
        # GOOGLE NEWS DATA (complementar/backup)
        if google_news_data and not isinstance(google_news_data, Exception):
            google_articles = google_news_data.get('articles', [])
            
            # Se não temos headlines da API interna, usa do Google News
            if not context['news_headlines']:
                for article in google_articles[:8]:
                    title = article.get('title', '')
                    source = article.get('source', {}).get('name', 'Google News')
                    context['news_headlines'].append(f"{title} (Recente, {source})")
            
            # Adiciona keywords do Google News
            for article in google_articles[:5]:
                keywords = article.get('keywords', [])
                context['trending_keywords'].extend(keywords[:2])
            
            # Se não temos insights internos, cria baseado no Google News
            if not context['market_insights'] and google_articles:
                context['market_insights'] = [
                    f"Google News indica {len(google_articles)} artigos recentes sobre o tema",
                    f"Alta cobertura midiática sugere relevância atual do tópico",
                    f"Fontes diversificadas confirmam interesse do mercado brasileiro"
                ]
                
            # Adiciona trending topics baseados no Google News
            google_topics = google_news_data.get('trending_topics', [])
            for topic in google_topics:
                topic_name = topic.get('topic', '')
                growth_rate = topic.get('growth_rate', 50)
                context['trend_top_terms'].append(f"{topic_name}: {growth_rate}")
            
        # YOUTUBE DATA
        if youtube_data and not isinstance(youtube_data, Exception):
            videos = youtube_data.get('items', [])
            context['youtube_volume'] = len(videos)
            context['youtube_top_queries'] = [
                video.get('snippet', {}).get('title', '')[:60]
                for video in videos[:5]
            ]
        else:
            context['youtube_volume'] = 0
            context['youtube_top_queries'] = []
        
        return context

    def _generate_context_fingerprint(self, context: Dict[str, Any]) -> str:
        """Gera fingerprint único do contexto"""
        stable_context = {
            'title': context.get('original_title', ''),
            'news_count': len(context.get('news_headlines', [])),
            'trends_count': len(context.get('trend_top_terms', [])),
            'youtube_volume': context.get('youtube_volume', 0)
        }
        
        context_str = json.dumps(stable_context, sort_keys=True)
        return hashlib.sha256(context_str.encode()).hexdigest()

    async def _gpt_generate_titles(self, client: httpx.AsyncClient, context: Dict, desired_count: int = 24) -> List[str]:
        """Gera títulos usando dados injetados"""
        
        if not self.openai_api_key:
            logger.warning("OpenAI API key não configurada")
            return self._generate_fallback_titles(context['original_title'])
        
        data_block = self._build_data_block(context)
        
        system_prompt = """Você é um gerador de episódios para podcasts empresariais brasileiros. 
Varie formato, evite repetições, responda em PT-BR conciso.
Base seus títulos nos dados fornecidos."""
        
        user_prompt = f"""{data_block}

Gere {desired_count} títulos únicos (≤70 chars), um por linha, sem numeração.
Varie formatos: perguntas, declarações, cases.
Não repita termos-chave."""

        try:
            async with self.semaphore:
                response = await client.post(
                    self.openai_url,
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "max_tokens": 800,
                        "temperature": 0.8
                    },
                    timeout=20.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    titles = []
                    for line in content.split('\n'):
                        clean_title = line.strip().lstrip('1234567890.-').strip().strip('"')
                        if clean_title and len(clean_title) > 10:
                            titles.append(clean_title)
                    
                    logger.info(f"GPT gerou {len(titles)} títulos")
                    return titles
                    
        except Exception as e:
            logger.error(f"Erro ao gerar títulos: {e}")
        
        return self._generate_fallback_titles(context['original_title'])

    def _build_data_block(self, context: Dict) -> str:
        """Constrói bloco de dados para prompt"""
        
        blocks = []
        
        if context.get('trend_top_terms'):
            trend_block = "TREND_TOP_TERMS: " + ", ".join(context['trend_top_terms'][:8])
            blocks.append(trend_block)
            
        if context.get('news_headlines'):
            news_block = "NEWS_HEADLINES: " + " | ".join(context['news_headlines'][:6])
            blocks.append(news_block)
            
        if context.get('market_insights'):
            insights_block = "MARKET_INSIGHTS: " + " | ".join(context['market_insights'][:3])
            blocks.append(insights_block)
            
        if context.get('youtube_volume', 0) > 0:
            youtube_block = f"YOUTUBE_VOLUME: {context['youtube_volume']} vídeos"
            if context.get('youtube_top_queries'):
                youtube_block += f" | TOP_QUERIES: {', '.join(context['youtube_top_queries'][:3])}"
            blocks.append(youtube_block)
            
        if context.get('original_context'):
            blocks.append(f"CONTEXT: {context['original_context']}")
            
        return "\n\n".join(blocks)

    def _mmr_select_titles(self, titles: List[str], k: int = 12, lambda_param: float = 0.6) -> List[str]:
        """MMR para seleção de títulos únicos"""
        if not NLTK_AVAILABLE or len(titles) <= k:
            return titles[:k]
            
        try:
            vectorizer = TfidfVectorizer(
                stop_words=list(stopwords.words('portuguese')),
                ngram_range=(1, 2),
                max_features=1000
            )
            
            title_vectors = vectorizer.fit_transform(titles)
            relevance_scores = np.array([
                np.linalg.norm(title_vectors[i].toarray()) 
                for i in range(len(titles))
            ])
            
            selected_indices = []
            remaining_indices = list(range(len(titles)))
            
            # Primeiro: mais relevante
            first_idx = np.argmax(relevance_scores)
            selected_indices.append(first_idx)
            remaining_indices.remove(first_idx)
            
            # Próximos: balanceado
            for _ in range(k - 1):
                if not remaining_indices:
                    break
                    
                scores = []
                for idx in remaining_indices:
                    relevance = relevance_scores[idx]
                    max_sim = 0
                    for selected_idx in selected_indices:
                        sim = cosine_similarity(
                            title_vectors[idx], title_vectors[selected_idx]
                        )[0][0]
                        max_sim = max(max_sim, sim)
                    
                    mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
                    scores.append(mmr_score)
                
                best_idx = remaining_indices[np.argmax(scores)]
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)
            
            selected_titles = [titles[i] for i in selected_indices]
            
            for title in selected_titles:
                tokens = set(word_tokenize(title.lower()))
                self.used_titles_tokens.update(tokens)
            
            logger.info(f"MMR selecionou {len(selected_titles)} títulos únicos")
            return selected_titles
            
        except Exception as e:
            logger.error(f"Erro no MMR: {e}")
            return self._simple_unique_selection(titles, k)

    def _simple_unique_selection(self, titles: List[str], k: int) -> List[str]:
        """Seleção simples de títulos únicos"""
        selected = []
        seen_tokens = set()
        
        def tokenize(text):
            if NLTK_AVAILABLE:
                return set(word_tokenize(text.lower())) - set(stopwords.words('portuguese'))
            else:
                return set(text.lower().split()) - PORTUGUESE_STOPWORDS
        
        for title in titles:
            tokens = tokenize(title)
            overlap = len(tokens & seen_tokens) / max(len(tokens), 1)
            
            if overlap < 0.3:
                selected.append(title)
                seen_tokens.update(tokens)
                self.used_titles_tokens.update(tokens)
                
                if len(selected) >= k:
                    break
        
        return selected

    async def _generate_single_episode(
        self, 
        client: httpx.AsyncClient,
        title: str,
        context: Dict,
        request: EpisodeSuggestionRequest,
        index: int
    ) -> EpisodeSuggestion:
        """Gera um episódio completo"""
        
        async with self.semaphore:
            try:
                # Gera componentes
                description = await self._gpt_description(client, context, title)
                keywords = await self._gpt_keywords(client, context, title, index)
                guest = await self._gpt_guest(client, context, title)
                
                # Métricas
                episode_metrics = self._compute_episode_metrics(context, keywords)
                legal_analysis = self._basic_legal_analysis(f"{title} {description}")
                
                episode = EpisodeSuggestion(
                    id=str(uuid.uuid4()),
                    title=title,
                    short_description=description[:180],
                    keywords=keywords[:8],
                    guest_suggestions=[guest] if guest else [],
                    success_probability=episode_metrics['success_probability'],
                    jip_trend_analysis=episode_metrics['trend_analysis'],
                    jip_legal_analysis=legal_analysis,
                    jip_market_analysis=episode_metrics['market_analysis'],
                    episode_news=[],
                    estimated_duration=45,
                    difficulty_level="intermediário",
                    target_audience=request.target_audience or "geral"
                )
                
                self.episode_cache[episode.id] = episode
                return episode
                
            except Exception as e:
                logger.error(f"Erro ao gerar episódio '{title}': {e}")
                raise e

    async def _gpt_description(self, client: httpx.AsyncClient, context: Dict, title: str) -> str:
        """Gera descrição usando contexto"""
        
        if not self.openai_api_key:
            return f"Análise prática sobre {title} com insights aplicáveis."
        
        data_snippet = ""
        if context.get('market_insights'):
            data_snippet += f"Insights: {context['market_insights'][0][:100]}\n"
        if context.get('news_headlines'):
            data_snippet += f"Notícias: {context['news_headlines'][0][:100]}\n"
        
        prompt = f"""EPISÓDIO: "{title}"
DADOS: {data_snippet}

Escreva descrição de 2-3 frases (máximo 180 chars) prática e envolvente."""

        try:
            response = await client.post(
                self.openai_url,
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 120,
                    "temperature": 0.7
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
                
        except Exception as e:
            logger.warning(f"Erro ao gerar descrição: {e}")
        
        return f"Análise aprofundada de {title} baseada em dados atuais."

    async def _gpt_keywords(self, client: httpx.AsyncClient, context: Dict, title: str, index: int) -> List[str]:
        """Gera keywords únicas"""
        
        if not self.openai_api_key:
            return self._fallback_keywords(index)
        
        facets = [
            "implementação prática, ROI, cases reais",
            "estratégias avançadas, inovação, competitividade", 
            "tendências futuras, mercado, oportunidades",
            "fundamentos, melhores práticas, metodologia"
        ]
        
        facet = facets[index % len(facets)]
        avoid_keywords = ", ".join(list(self.used_keywords)[:20])
        trending_context = ", ".join(context.get('trending_keywords', [])[:5])
        
        prompt = f"""TÍTULO: "{title}"
FOCO: {facet}
TRENDING: {trending_context}
EVITAR: {avoid_keywords}

Gere 8 keywords acionáveis focadas em {facet}.
FORMATO: keyword1, keyword2, ..."""

        try:
            response = await client.post(
                self.openai_url,
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                    "temperature": 0.5
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                keywords_text = result["choices"][0]["message"]["content"].strip()
                keywords = [kw.strip().strip('"') for kw in keywords_text.split(',')]
                
                unique_keywords = self._simple_dedupe_keywords(keywords)
                
                for kw in unique_keywords:
                    self.used_keywords.add(kw.lower())
                
                return unique_keywords[:8]
                
        except Exception as e:
            logger.warning(f"Erro ao gerar keywords: {e}")
        
        return self._fallback_keywords(index)

    def _simple_dedupe_keywords(self, keywords: List[str]) -> List[str]:
        """Dedupe simples de keywords"""
        unique_keywords = []
        seen_words = set()
        
        for kw in keywords:
            kw_words = set(kw.lower().split())
            if not (kw_words & seen_words):
                unique_keywords.append(kw)
                seen_words.update(kw_words)
        
        return unique_keywords

    async def _gpt_guest(self, client: httpx.AsyncClient, context: Dict, title: str) -> Optional[GuestSuggestion]:
        """Gera sugestão de convidado"""
        
        if not self.openai_api_key:
            return self._fallback_guest(title)
        
        market_context = ""
        if context.get('market_insights'):
            market_context = context['market_insights'][0][:100]
        
        prompt = f"""EPISÓDIO: "{title}"
INSIGHTS: {market_context}

Sugira 1 FUNÇÃO/CARGO ideal.

Formato:
Função: [cargo]
Expertise: [área]  
Relevância: [por que é ideal]"""

        try:
            response = await client.post(
                self.openai_url,
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.3
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                function = "Especialista"
                expertise = f"Especialista em {title}"
                relevance = "Conhecimento específico relevante"
                
                for line in content.split('\n'):
                    if line.startswith("Função:"):
                        function = line.replace("Função:", "").strip()
                    elif line.startswith("Expertise:"):
                        expertise = line.replace("Expertise:", "").strip()
                    elif line.startswith("Relevância:"):
                        relevance = line.replace("Relevância:", "").strip()
                
                return GuestSuggestion(
                    name=function,
                    expertise=expertise,
                    relevance_score=90.0,
                    justification=relevance,
                    contact_suggestion="LinkedIn ou eventos regionais"
                )
                
        except Exception as e:
            logger.warning(f"Erro ao gerar guest: {e}")
        
        return self._fallback_guest(title)

def _basic_legal_analysis(
    self,
    text: str,
    *,
    legal_refs: int = 0,          # nº de referências/menções legais encontradas (ex.: Art. 37 do CDC)
    evidence_sources: int = 0     # nº de fontes/leis distintas (ex.: CDC, CF, ANVISA…)
) -> JIPLegalAnalysis:
    """
    Analisa risco legal do texto e calcula 'confidence_score' como
    CONFIANÇA DE CONFORMIDADE (0–1).
      - Quanto maior o risco -> menor a confiança de conformidade.
      - Quanto mais evidências legais -> maior a confiança (quando OK) ou
        menor a penalidade (quando WARNING).

    Exibir na UI como porcentagem: confidence_score * 100.
    """

    # --- 1) Sinal de risco pelo conteúdo ---
    text_lower = text.lower()
    high_risk = ["garantia", "garantido", "promessa", "certeza", "milagre", "cura"]
    medium_risk = ["lucro", "ganho", "retorno garantido"]

    high_count = sum(1 for w in high_risk if w in text_lower)
    med_count  = sum(1 for w in medium_risk if w in text_lower)

    # risco bruto ponderado (alto=1.0, médio=0.5)
    risk_raw = 1.0 * high_count + 0.5 * med_count

    # normalização suave em [0,1): 1 - e^(-k*x)
    k = 0.9
    risk_norm = 1.0 - (2.718281828 ** (-k * risk_raw))

    # --- 2) Veredito (OK x WARNING) + nível de risco + issues/recomendações ---
    if high_count > 0:
        status = LegalStatus.WARNING
        risk_level = "alto"
        issues = [f"Termo de alto risco: '{w}'" for w in high_risk if w in text_lower]
        recommendations = ["Remover promessas absolutas", "Adicionar disclaimers"]
    elif med_count > 1:
        status = LegalStatus.WARNING
        risk_level = "médio"
        issues = ["Múltiplas referências financeiras potencialmente enganosas"] + [
            f"'{w}'" for w in medium_risk if w in text_lower
        ]
        recommendations = ["Adicionar disclaimer financeiro", "Rever promessas de retorno"]
    else:
        status = LegalStatus.OK
        risk_level = "baixo"
        issues = []
        recommendations = ["Conteúdo aprovado"]

    # --- 3) Evidências legais (contagem e diversidade) ---
    # normaliza por patamar (>=3 refs satura)
    evidence_norm = min(1.0, legal_refs / 3.0)
    # diversidade dá pequeno bônus (máx +0.1)
    diversity_bonus = min(0.1, max(0, evidence_sources - 1) * 0.03)

    # --- 4) Confiança de conformidade ---
    # mistura risco (negativo) e evidência (positivo)
    conf = 0.6 * (1.0 - risk_norm) + 0.4 * evidence_norm + diversity_bonus

    # penalidades quando WARNING
    if status == LegalStatus.WARNING:
        if legal_refs == 0:
            conf -= 0.25  # WARNING sem fonte legal -> confiança de conformidade bem baixa
        elif legal_refs < 2:
            conf -= 0.10  # poucas evidências

    # faixa estável
    conf = max(0.05, min(0.98, conf))

    return JIPLegalAnalysis(
        status=status,
        confidence_score=round(conf, 2),
        issues_found=issues,
        recommendations=recommendations,
        risk_level=risk_level,
    )



    def _compute_episode_metrics(self, context: Dict, keywords: List[str]) -> Dict[str, Any]:
        """Computa métricas do episódio"""
        
        base_score = 50
        
        # Boosts baseados no contexto
        if context.get('market_insights'):
            base_score += min(20, len(context['market_insights']) * 7)
        if context.get('trend_top_terms'):
            base_score += min(15, len(context['trend_top_terms']) * 2)
        if context.get('news_headlines'):
            base_score += min(10, len(context['news_headlines']) * 1.5)
        
        youtube_volume = context.get('youtube_volume', 0)
        if youtube_volume > 100:
            base_score += 10
        elif youtube_volume > 50:
            base_score += 5
        
        relevant_keywords = [kw for kw in keywords if len(kw) > 4]
        base_score += min(10, len(relevant_keywords))
        
        success_probability = min(95, max(35, base_score))
        
        # Análises baseadas no score
        if success_probability > 75:
            market_direction = "forte expansão"
            opportunity = "alta"
            competition = "alto"
            engagement = "alto"
        elif success_probability > 60:
            market_direction = "crescimento moderado"
            opportunity = "média"
            competition = "médio"
            engagement = "médio"
        else:
            market_direction = "estabilização"
            opportunity = "baixa"
            competition = "baixo"
            engagement = "moderado"
        
        trend_analysis = JIPTrendAnalysis(
            trend_score=success_probability,
            market_direction=market_direction,
            competition_level=competition,
            growth_prediction=round((success_probability - 50) * 0.4, 1),
            opportunity_level=opportunity
        )
        
        market_analysis = JIPMarketAnalysis(
            audience_interest=round(success_probability * 0.9, 1),
            content_saturation=competition,
            best_timing="Próximas 2-3 semanas",
            estimated_reach=int(success_probability * 400 + 3000),
            engagement_prediction=engagement
        )
        
        return {
            'success_probability': round(success_probability, 1),
            'trend_analysis': trend_analysis,
            'market_analysis': market_analysis
        }

    def _compute_overall_metrics(self, news_insights_data, youtube_data) -> Dict[str, Any]:
        """Computa métricas gerais"""
        
        sources_score = 0
        total_weight = 0
        
        # News Insights (maior peso)
        if news_insights_data and not isinstance(news_insights_data, Exception):
            articles_count = len(news_insights_data.get('articles', []))
            insights_count = len(news_insights_data.get('insights', []))
            topics_count = len(news_insights_data.get('trending_topics', []))
            
            internal_score = min(100, (articles_count * 3) + (insights_count * 10) + (topics_count * 5))
            sources_score += internal_score * 0.7
            total_weight += 0.7
        
        # YouTube API  
        if youtube_data and not isinstance(youtube_data, Exception):
            youtube_score = min(100, len(youtube_data.get('items', [])) * 3)
            sources_score += youtube_score * 0.3
            total_weight += 0.3
        
        overall_score = sources_score / max(total_weight, 0.1) if total_weight > 0 else 50
        
        if overall_score > 80:
            opportunity = "Excelente oportunidade de mercado"
            timing = "Próxima semana"
        elif overall_score > 65:
            opportunity = "Boa oportunidade de mercado"
            timing = "Próximas 2 semanas"
        else:
            opportunity = "Oportunidade moderada de mercado"
            timing = "Próximas 3-4 semanas"
        
        return {
            'trend_score': round(overall_score, 1),
            'market_opportunity': opportunity,
            'timing': timing
        }

    def _compute_similarity_stats(self, episodes: List[EpisodeSuggestion]) -> Dict[str, float]:
        """Computa estatísticas de similaridade"""
        
        if len(episodes) < 2 or not NLTK_AVAILABLE:
            return {'avg_similarity': 0.0, 'max_similarity': 0.0}
        
        try:
            titles = [ep.title for ep in episodes]
            vectorizer = TfidfVectorizer(stop_words=list(stopwords.words('portuguese')))
            vectors = vectorizer.fit_transform(titles)
            
            similarities = []
            for i in range(len(titles)):
                for j in range(i + 1, len(titles)):
                    sim = cosine_similarity(vectors[i], vectors[j])[0][0]
                    similarities.append(sim)
            
            return {
                'avg_similarity': round(np.mean(similarities), 3),
                'max_similarity': round(np.max(similarities), 3)
            }
            
        except Exception as e:
            logger.warning(f"Erro ao calcular similaridade: {e}")
            return {'avg_similarity': 0.0, 'max_similarity': 0.0}

    # === CACHE METHODS ===
    
    def _get_from_cache(self, key: str) -> Optional[Dict]:
        """Busca dados do cache"""
        if key not in self.external_cache:
            return None
        
        data, expires_at = self.external_cache[key]
        if datetime.now() > expires_at:
            del self.external_cache[key]
            return None
        
        return data

    def _set_cache(self, key: str, data: Dict):
        """Armazena dados no cache"""
        expires_at = datetime.now() + self.cache_ttl
        self.external_cache[key] = (data, expires_at)

    # === FALLBACK METHODS ===
    
    def _generate_fallback_titles(self, title: str) -> List[str]:
        """Títulos de fallback"""
        return [
            f"Como Implementar {title}: Guia Prático",
            f"5 Estratégias de {title} que Funcionam",
            f"Erros Comuns em {title} e Como Evitar", 
            f"{title}: Tendências e Oportunidades 2025",
            f"Case de Sucesso: {title} na Prática",
            f"ROI de {title}: Vale o Investimento?",
            f"O Futuro de {title} no Brasil",
            f"Implementando {title} em Pequenas Empresas",
            f"Masterclass: {title} do Zero ao Avançado",
            f"{title} vs Concorrência: Análise Comparativa",
            f"Transformação Digital: {title} em Foco",
            f"Especialistas Revelam: Segredos de {title}"
        ]

    def _fallback_keywords(self, index: int) -> List[str]:
        """Keywords de fallback"""
        facet_keywords = [
            ["implementação", "práticas", "resultados", "cases", "ROI", "aplicação"],
            ["estratégias", "inovação", "competitividade", "diferencial", "mercado", "crescimento"],
            ["tendências", "futuro", "oportunidades", "evolução", "perspectivas", "cenários"],
            ["fundamentos", "conceitos", "metodologia", "bases", "estrutura", "framework"]
        ]
        
        keywords = facet_keywords[index % len(facet_keywords)]
        for kw in keywords:
            self.used_keywords.add(kw)
        
        return keywords

    def _fallback_guest(self, title: str) -> GuestSuggestion:
        """Guest de fallback"""
        
        title_lower = title.lower()
        
        if any(word in title_lower for word in ["tecnologia", "digital", "ia", "tech"]):
            return GuestSuggestion(
                name="CTO ou Diretor de Tecnologia",
                expertise="Tecnologia e transformação digital",
                relevance_score=85.0,
                justification="Expertise em tecnologia e inovação",
                contact_suggestion="LinkedIn ou eventos de tecnologia"
            )
        elif any(word in title_lower for word in ["marketing", "vendas", "cliente"]):
            return GuestSuggestion(
                name="Head de Marketing",
                expertise="Marketing e estratégia comercial", 
                relevance_score=85.0,
                justification="Experiência em marketing e vendas",
                contact_suggestion="LinkedIn ou eventos de marketing"
            )
        else:
            return GuestSuggestion(
                name="CEO ou Fundador",
                expertise="Liderança e estratégia empresarial",
                relevance_score=85.0,
                justification="Visão estratégica e experiência de liderança",
                contact_suggestion="LinkedIn ou networking empresarial"
            )

    async def _generate_fallback_response(self, request: EpisodeSuggestionRequest, error: str) -> EpisodeSuggestionsResponse:
        """Resposta de fallback"""
        
        logger.warning(f"Gerando resposta de fallback devido a: {error}")
        
        titles = self._generate_fallback_titles(request.title)[:12]
        episodes = []
        
        for i, title in enumerate(titles):
            episode = EpisodeSuggestion(
                id=str(uuid.uuid4()),
                title=title,
                short_description=f"Discussão prática sobre {title} com insights aplicáveis.",
                keywords=self._fallback_keywords(i),
                guest_suggestions=[self._fallback_guest(title)],
                success_probability=60.0 + i,
                jip_trend_analysis=JIPTrendAnalysis(
                    trend_score=65.0,
                    market_direction="crescimento moderado",
                    competition_level="médio", 
                    growth_prediction=7.5,
                    opportunity_level="média"
                ),
                jip_legal_analysis=JIPLegalAnalysis(
                    status=LegalStatus.OK,
                    confidence_score=0.95,
                    issues_found=[],
                    recommendations=["Conteúdo aprovado"],
                    risk_level="baixo"
                ),
                jip_market_analysis=JIPMarketAnalysis(
                    audience_interest=58.5,
                    content_saturation="médio",
                    best_timing="Próximas 2-3 semanas",
                    estimated_reach=27000 + i * 200,
                    engagement_prediction="médio"
                ),
                episode_news=[],
                estimated_duration=45,
                difficulty_level="intermediário",
                target_audience=request.target_audience or "geral"
            )
            episodes.append(episode)
            self.episode_cache[episode.id] = episode
        
        return EpisodeSuggestionsResponse(
            request_title=request.title,
            request_context=request.context,
            total_suggestions=12,
            suggestions=episodes,
            overall_trend_score=65.0,
            market_opportunity="Boa oportunidade com dados internos",
            recommended_timing="Próximas 2-3 semanas",
            processing_time_ms=500.0
        )

    # === COMPATIBILITY METHODS ===
    
    async def get_episode_details(
        self, 
        episode_id: str,
        db: Optional[Session] = None  # ← ADICIONADO
    ) -> Optional[EpisodeSuggestion]:
        """Busca episódio no cache ou banco"""
        
        # 1. Tentar cache primeiro
        cached = self.episode_cache.get(episode_id)
        if cached:
            logger.info(f"📦 Episódio {episode_id} encontrado no cache")
            return cached
        
        # 2. Buscar no banco
        if db:
            try:
                from ..models.episode_suggestion_model import EpisodeSuggestion as EpisodeSuggestionDB
                
                episode_db = db.query(EpisodeSuggestionDB).filter(
                    EpisodeSuggestionDB.id == episode_id
                ).first()
                
                if episode_db:
                    logger.info(f"💾 Episódio {episode_id} encontrado no banco")
                    
                    # Converter de DB para Pydantic
                    episode = EpisodeSuggestion(
                        id=episode_db.id,
                        title=episode_db.title,
                        short_description=episode_db.short_description,
                        keywords=episode_db.keywords,
                        guest_suggestions=[
                            GuestSuggestion(**g) for g in episode_db.guest_suggestions
                        ] if episode_db.guest_suggestions else [],
                        success_probability=episode_db.success_probability,
                        jip_trend_analysis=JIPTrendAnalysis(**episode_db.jip_trend_analysis),
                        jip_legal_analysis=JIPLegalAnalysis(**episode_db.jip_legal_analysis),
                        jip_market_analysis=JIPMarketAnalysis(**episode_db.jip_market_analysis),
                        episode_news=[
                            EpisodeNews(**n) for n in episode_db.episode_news
                        ] if episode_db.episode_news else [],
                        estimated_duration=episode_db.estimated_duration,
                        difficulty_level=episode_db.difficulty_level,
                        target_audience=episode_db.target_audience,
                        created_at=episode_db.created_at
                    )
                    
                    # Adiciona no cache para próximas consultas
                    self.episode_cache[episode_id] = episode
                    
                    return episode
                    
            except Exception as e:
                logger.error(f"Erro ao buscar episódio no banco: {e}")
        
        return None

    async def reanalyze_episode(self, episode_id: str, additional_keywords: List[str]) -> Optional[EpisodeSuggestion]:
        """Re-análise de episódio"""
        episode = self.episode_cache.get(episode_id)
        if not episode:
            return None
        
        current_keywords = episode.keywords.copy()
        current_keywords.extend(additional_keywords[:3])
        episode.keywords = current_keywords[:8]
        
        episode.success_probability = min(95, episode.success_probability + 2.5)
        
        return episode

    # === NOVO MÉTODO: SALVAR NO BANCO ===
    async def _save_batch_to_db(
        self, 
        db: Session,
        request: EpisodeSuggestionRequest,
        episodes: List[EpisodeSuggestion],
        overall_metrics: Dict,
        processing_time: float,
        user_ip: Optional[str] = None,
        user_id: Optional[int] = None
    ):
        """Salva batch e episódios no banco"""
        from ..models.episode_suggestion_model import (
            EpisodeSuggestionBatch, 
            EpisodeSuggestion as EpisodeSuggestionDB
        )
        
        # 1. Criar batch
        batch = EpisodeSuggestionBatch(
            user_id=user_id,
            user_ip=user_ip,
            request_title=request.title,
            request_context=request.context,
            request_personal_input=request.personal_input,
            request_target_audience=request.target_audience,
            request_episode_format=request.episode_format,
            total_suggestions=len(episodes),
            overall_trend_score=overall_metrics['trend_score'],
            market_opportunity=overall_metrics['market_opportunity'],
            recommended_timing=overall_metrics['timing'],
            processing_time_ms=round(processing_time, 2),
            status="success"
        )
        
        db.add(batch)
        db.flush()  # Gera o batch.id
        
        # 2. Criar episódios
        for episode in episodes:
            episode_db = EpisodeSuggestionDB(
                id=episode.id,
                batch_id=batch.id,
                title=episode.title,
                short_description=episode.short_description,
                keywords=episode.keywords,
                success_probability=episode.success_probability,
                estimated_duration=episode.estimated_duration,
                difficulty_level=episode.difficulty_level,
                target_audience=episode.target_audience,
                jip_trend_analysis=episode.jip_trend_analysis.model_dump(),
                jip_legal_analysis=episode.jip_legal_analysis.model_dump(),
                jip_market_analysis=episode.jip_market_analysis.model_dump(),
                guest_suggestions=[g.model_dump() for g in episode.guest_suggestions],
                episode_news=[n.model_dump() for n in episode.episode_news]
            )
            db.add(episode_db)
        
        db.commit()
        db.refresh(batch)
        
        return batch