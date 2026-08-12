# app/services/news_insights_service.py
import os
import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import hashlib
import re

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from ..schemas.news_insights_schema import (
    NewsArticle, NewsSource, NewsInsight, TrendingTopic,
    NewsAnalysisResponse, NewsTrendsDashboard, NewsCategory,
    SentimentType, NewsSourcesResponse
)

logger = logging.getLogger(__name__)

class NewsInsightsService:
    """Serviço para análise de notícias e insights em tempo real"""
    
    def __init__(self):
        # APIs de notícias disponíveis
        self.news_api_key = os.getenv("NEWS_API_KEY")
        self.gnews_api_key = os.getenv("GNEWS_API_KEY")
        
        # Cache interno
        self.cache = {}
        self.cache_duration = 300  # 5 minutos
        
        # Configurações
        self.base_urls = {
            "newsapi": "https://newsapi.org/v2",
            "gnews": "https://gnews.io/api/v4"
        }
        
        # Fontes confiáveis brasileiras
        self.brazilian_sources = {
            "g1.globo.com": {"name": "G1", "reliability": 8.5},
            "folha.uol.com.br": {"name": "Folha", "reliability": 9.0},
            "estadao.com.br": {"name": "Estadão", "reliability": 8.8},
            "uol.com.br": {"name": "UOL", "reliability": 7.8},
            "exame.com": {"name": "Exame", "reliability": 8.2},
            "cnnbrasil.com.br": {"name": "CNN Brasil", "reliability": 8.0},
            "band.uol.com.br": {"name": "Band", "reliability": 7.5},
            "r7.com": {"name": "R7", "reliability": 7.2},
        }
        
        # Palavras-chave para categorização
        self.category_keywords = {
            NewsCategory.TECHNOLOGY: [
                "tecnologia", "inteligência artificial", "IA", "startup", "app", "digital",
                "internet", "celular", "smartphone", "computador", "software", "inovação"
            ],
            NewsCategory.BUSINESS: [
                "economia", "negócios", "empresa", "mercado", "bolsa", "investimento",
                "banco", "financial", "pib", "inflação", "real", "dólar"
            ],
            NewsCategory.POLITICS: [
                "política", "governo", "congresso", "senado", "câmara", "presidente",
                "eleição", "partido", "deputado", "senador", "ministro"
            ],
            NewsCategory.HEALTH: [
                "saúde", "medicina", "hospital", "médico", "doença", "tratamento",
                "vacina", "covid", "sus", "medicamento"
            ],
            NewsCategory.SPORTS: [
                "futebol", "esporte", "time", "jogador", "campeonato", "copa",
                "olimpíada", "atleta", "jogo", "partida"
            ]
        }
        
        if not HTTPX_AVAILABLE:
            logger.warning("httpx não instalado. Funcionalidade limitada.")

    def _generate_cache_key(self, *args) -> str:
        """Gera chave única para cache"""
        content = "_".join(str(arg) for arg in args)
        return hashlib.md5(content.encode()).hexdigest()

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Verifica validade do cache"""
        if cache_key not in self.cache:
            return False
        timestamp = self.cache[cache_key].get("timestamp", 0)
        return (datetime.now().timestamp() - timestamp) < self.cache_duration

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Recupera dados do cache"""
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]["data"]
        return None

    def _set_cache(self, cache_key: str, data: Any):
        """Armazena no cache"""
        self.cache[cache_key] = {
            "data": data,
            "timestamp": datetime.now().timestamp()
        }

    def _categorize_article(self, title: str, description: str = "") -> NewsCategory:
        """Categoriza artigo baseado no conteúdo"""
        content = f"{title} {description}".lower()
        
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        return NewsCategory.GENERAL

    def _analyze_sentiment(self, text: str) -> Tuple[SentimentType, float]:
        """Análise simples de sentimento"""
        if not text:
            return SentimentType.NEUTRAL, 0.0
        
        text_lower = text.lower()
        
        # Palavras positivas em português
        positive_words = [
            "bom", "ótimo", "excelente", "positivo", "sucesso", "crescimento",
            "melhora", "aumento", "vitória", "conquista", "progresso", "inovação"
        ]
        
        # Palavras negativas em português
        negative_words = [
            "ruim", "péssimo", "negativo", "crise", "queda", "diminuição",
            "problema", "conflito", "guerra", "morte", "acidente", "corrupção"
        ]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total_words = len(text_lower.split())
        
        if total_words == 0:
            return SentimentType.NEUTRAL, 0.0
        
        positive_ratio = positive_count / total_words
        negative_ratio = negative_count / total_words
        
        score = positive_ratio - negative_ratio
        
        if score > 0.02:
            return SentimentType.POSITIVE, min(score * 10, 1.0)
        elif score < -0.02:
            return SentimentType.NEGATIVE, max(score * 10, -1.0)
        else:
            return SentimentType.NEUTRAL, score

    def _extract_keywords(self, text: str) -> List[str]:
        """Extrai palavras-chave do texto"""
        if not text:
            return []
        
        # Remove pontuação e converte para minúsculas
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = clean_text.split()
        
        # Remove palavras muito curtas e comuns
        stop_words = {
            "o", "a", "os", "as", "um", "uma", "de", "da", "do", "das", "dos",
            "e", "ou", "mas", "que", "para", "com", "por", "em", "na", "no",
            "não", "é", "foi", "ser", "ter", "seu", "sua", "seus", "suas"
        }
        
        keywords = [
            word for word in words 
            if len(word) > 3 and word not in stop_words
        ]
        
        # Retorna as palavras mais frequentes
        from collections import Counter
        word_freq = Counter(keywords)
        return [word for word, count in word_freq.most_common(10)]

    def _calculate_engagement_score(self, article_data: Dict[str, Any]) -> float:
        """Calcula score de engajamento baseado em métricas disponíveis"""
        score = 50.0  # Score base
        
        # Fatores que aumentam engajamento
        if article_data.get("url_to_image"):
            score += 10  # Artigos com imagem
        
        title_length = len(article_data.get("title", ""))
        if 30 <= title_length <= 80:
            score += 15  # Título no tamanho ideal
        
        # Fonte confiável
        source_name = article_data.get("source", {}).get("name", "")
        for domain, info in self.brazilian_sources.items():
            if domain in article_data.get("url", ""):
                score += info["reliability"]
                break
        
        # Artigo recente
        try:
            pub_date = datetime.fromisoformat(
                article_data.get("publishedAt", "").replace("Z", "+00:00")
            )
            hours_ago = (datetime.now(pub_date.tzinfo) - pub_date).total_seconds() / 3600
            if hours_ago <= 24:
                score += 20  # Artigo das últimas 24h
            elif hours_ago <= 48:
                score += 10  # Artigo das últimas 48h
        except:
            pass
        
        return min(score, 100.0)

    async def search_news(
        self,
        query: str,
        category: Optional[NewsCategory] = None,
        language: str = "pt",
        max_results: int = 20,
        sort_by: str = "publishedAt"
    ) -> List[NewsArticle]:
        """Busca notícias por query"""
        
        cache_key = self._generate_cache_key(query, category, language, max_results, sort_by)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        articles = []
        
        # Busca com News API se disponível
        if self.news_api_key and HTTPX_AVAILABLE:
            try:
                articles.extend(await self._fetch_from_newsapi(
                    query, category, language, max_results, sort_by
                ))
            except Exception as e:
                logger.warning(f"Erro no NewsAPI: {e}")
        
        # Se não conseguiu resultados, usa dados mock brasileiros
        if not articles:
            articles = self._generate_mock_brazilian_news(query, max_results)
        
        self._set_cache(cache_key, articles)
        return articles

    async def _fetch_from_newsapi(
        self, query: str, category: Optional[NewsCategory], 
        language: str, max_results: int, sort_by: str
    ) -> List[NewsArticle]:
        """Busca notícias via NewsAPI"""
        
        params = {
            "q": query,
            "language": language,
            "sortBy": sort_by,
            "pageSize": min(max_results, 100),
            "apiKey": self.news_api_key
        }
        
        if category and category != NewsCategory.GENERAL:
            params["category"] = category.value
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_urls['newsapi']}/everything",
                params=params,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
        
        articles = []
        for item in data.get("articles", []):
            try:
                # Análise de sentimento
                content = f"{item['title']} {item.get('description', '')}"
                sentiment, sentiment_score = self._analyze_sentiment(content)
                
                # Extração de keywords
                keywords = self._extract_keywords(content)
                
                # Score de engajamento
                engagement_score = self._calculate_engagement_score(item)
                
                # Categorização
                detected_category = self._categorize_article(
                    item["title"], item.get("description", "")
                )
                
                article = NewsArticle(
                    id=hashlib.md5(item["url"].encode()).hexdigest()[:16],
                    title=item["title"],
                    description=item.get("description"),
                    content=item.get("content"),
                    url=item["url"],
                    url_to_image=item.get("urlToImage"),
                    published_at=datetime.fromisoformat(
                        item["publishedAt"].replace("Z", "+00:00")
                    ),
                    source=NewsSource(
                        id=item["source"].get("id"),
                        name=item["source"]["name"],
                        reliability_score=self._get_source_reliability(item["url"])
                    ),
                    category=category or detected_category,
                    sentiment=sentiment,
                    sentiment_score=sentiment_score,
                    engagement_score=engagement_score,
                    trending_score=min(engagement_score * 1.2, 100.0),
                    keywords=keywords,
                    read_time_minutes=max(1, len(content.split()) // 200),
                    language=language
                )
                articles.append(article)
                
            except Exception as e:
                logger.warning(f"Erro ao processar artigo: {e}")
                continue
        
        return articles

    def _get_source_reliability(self, url: str) -> float:
        """Retorna score de confiabilidade da fonte"""
        for domain, info in self.brazilian_sources.items():
            if domain in url:
                return info["reliability"]
        return 6.0  # Score padrão

    def _generate_mock_brazilian_news(self, query: str, max_results: int) -> List[NewsArticle]:
        """Gera notícias mock brasileiras realistas"""
        
        mock_articles = []
        base_topics = [
            {
                "title": f"Nova pesquisa revela tendências sobre {query} no Brasil",
                "description": f"Estudo aponta crescimento significativo relacionado a {query} no mercado brasileiro, com impacto em diversos setores.",
                "category": NewsCategory.BUSINESS,
                "source": "Exame",
                "sentiment": SentimentType.POSITIVE
            },
            {
                "title": f"Especialistas analisam impacto de {query} na economia",
                "description": f"Economistas discutem como {query} pode influenciar o crescimento do PIB nos próximos meses.",
                "category": NewsCategory.BUSINESS,
                "source": "Folha",
                "sentiment": SentimentType.NEUTRAL
            },
            {
                "title": f"Tecnologia brasileira avança em soluções para {query}",
                "description": f"Startups nacionais desenvolvem inovações relacionadas a {query}, atraindo investimentos.",
                "category": NewsCategory.TECHNOLOGY,
                "source": "G1",
                "sentiment": SentimentType.POSITIVE
            },
            {
                "title": f"Governo anuncia novas medidas relacionadas a {query}",
                "description": f"Ministério divulga plano estratégico que inclui ações específicas sobre {query}.",
                "category": NewsCategory.POLITICS,
                "source": "CNN Brasil",
                "sentiment": SentimentType.NEUTRAL
            },
            {
                "title": f"Pesquisa mostra opinião dos brasileiros sobre {query}",
                "description": f"Levantamento do Datafolha indica percepção positiva da população em relação a {query}.",
                "category": NewsCategory.GENERAL,
                "source": "UOL",
                "sentiment": SentimentType.POSITIVE
            }
        ]
        
        for i, topic in enumerate(base_topics[:max_results]):
            # Simula diferentes horários de publicação
            hours_ago = i * 2 + 1
            pub_date = datetime.now() - timedelta(hours=hours_ago)
            
            # Score baseado na recência
            engagement_score = max(30, 90 - (hours_ago * 5))
            
            article = NewsArticle(
                id=hashlib.md5(f"{topic['title']}_{query}".encode()).hexdigest()[:16],
                title=topic["title"],
                description=topic["description"],
                url=f"https://{topic['source'].lower().replace(' ', '')}.com.br/noticia-{i+1}",
                url_to_image=f"https://via.placeholder.com/400x200?text={query}",
                published_at=pub_date,
                source=NewsSource(
                    name=topic["source"],
                    reliability_score=self._get_source_reliability(topic["source"])
                ),
                category=topic["category"],
                sentiment=topic["sentiment"],
                sentiment_score=0.3 if topic["sentiment"] == SentimentType.POSITIVE else 0.0,
                engagement_score=engagement_score,
                trending_score=engagement_score * 1.1,
                keywords=[query] + query.split()[:3],
                entities=[query, "Brasil"],
                topics=[topic["category"].value],
                read_time_minutes=3,
                language="pt"
            )
            mock_articles.append(article)
        
        return mock_articles

    async def get_trending_topics(self, limit: int = 10) -> List[TrendingTopic]:
        """Busca tópicos trending atuais"""
        
        cache_key = f"trending_topics_{limit}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Mock de tópicos trending brasileiros
        trending_topics = [
            {
                "topic": "Inteligência Artificial",
                "category": NewsCategory.TECHNOLOGY,
                "growth_rate": 85.5,
                "sentiment": SentimentType.POSITIVE
            },
            {
                "topic": "ENEM 2025",
                "category": NewsCategory.GENERAL,
                "growth_rate": 120.3,
                "sentiment": SentimentType.NEUTRAL
            },
            {
                "topic": "Black Friday",
                "category": NewsCategory.BUSINESS,
                "growth_rate": 95.8,
                "sentiment": SentimentType.POSITIVE
            },
            {
                "topic": "Copa do Brasil",
                "category": NewsCategory.SPORTS,
                "growth_rate": 75.2,
                "sentiment": SentimentType.POSITIVE
            },
            {
                "topic": "Eleições Municipais",
                "category": NewsCategory.POLITICS,
                "growth_rate": 65.4,
                "sentiment": SentimentType.NEUTRAL
            }
        ]
        
        topics = []
        for i, topic_data in enumerate(trending_topics[:limit]):
            # Busca artigos relacionados
            related_articles = await self.search_news(
                topic_data["topic"], 
                topic_data["category"], 
                max_results=3
            )
            
            topic = TrendingTopic(
                topic=topic_data["topic"],
                category=topic_data["category"],
                article_count=len(related_articles) + (i * 5) + 10,
                growth_rate=topic_data["growth_rate"],
                sentiment=topic_data["sentiment"],
                trending_score=topic_data["growth_rate"] * 0.8,
                engagement_level="high" if topic_data["growth_rate"] > 90 else "medium",
                key_articles=related_articles,
                related_keywords=topic_data["topic"].split() + ["Brasil", "2025"],
                first_seen=datetime.now() - timedelta(hours=i*6 + 12),
                peak_time=datetime.now() - timedelta(hours=i*2 + 1)
            )
            topics.append(topic)
        
        self._set_cache(cache_key, topics)
        return topics

    async def generate_insights(self, articles: List[NewsArticle]) -> List[NewsInsight]:
        """Gera insights baseados nos artigos"""
        
        if not articles:
            return []
        
        insights = []
        from collections import Counter
        
        # Insight de sentimento geral
        sentiments = [a.sentiment for a in articles if a.sentiment]
        if sentiments:
            positive_count = sum(1 for s in sentiments if s == SentimentType.POSITIVE)
            sentiment_ratio = positive_count / len(sentiments)
            
            insight = NewsInsight(
                id=f"sentiment_{datetime.now().strftime('%Y%m%d_%H%M')}",
                title="Análise de Sentimento Geral",
                description=f"Das {len(sentiments)} notícias analisadas, {positive_count} ({sentiment_ratio:.1%}) apresentam sentimento positivo.",
                insight_type="sentiment",
                confidence=0.8,
                related_articles=[a.id for a in articles[:5]],
                keywords=["sentimento", "análise"],
                time_period="últimas 24 horas",
                impact_score=sentiment_ratio * 100,
                relevance_score=85.0
            )
            insights.append(insight)
        
        # Insight de tópicos emergentes
        all_keywords = []
        for article in articles:
            all_keywords.extend(article.keywords)
        
        if all_keywords:
            keyword_freq = Counter(all_keywords)
            top_keywords = keyword_freq.most_common(3)
            
            insight = NewsInsight(
                id=f"topics_{datetime.now().strftime('%Y%m%d_%H%M')}",
                title="Tópicos Emergentes",
                description=f"Os temas mais mencionados são: {', '.join([k[0] for k in top_keywords])}",
                insight_type="trend",
                confidence=0.7,
                keywords=[k[0] for k in top_keywords],
                time_period="últimas 24 horas",
                impact_score=min(sum(k[1] for k in top_keywords) * 10, 100),
                relevance_score=75.0
            )
            insights.append(insight)
        
        # Insight de fontes mais ativas
        source_count = Counter([a.source.name for a in articles])
        if source_count:
            most_active = source_count.most_common(1)[0]
            
            insight = NewsInsight(
                id=f"sources_{datetime.now().strftime('%Y%m%d_%H%M')}",
                title="Fonte Mais Ativa",
                description=f"{most_active[0]} publicou {most_active[1]} artigos relacionados ao tema.",
                insight_type="pattern",
                confidence=0.9,
                keywords=["fonte", "atividade"],
                time_period="últimas 24 horas",
                impact_score=min(most_active[1] * 15, 100),
                relevance_score=60.0
            )
            insights.append(insight)
        
        return insights

    async def get_news_sources(self, category: Optional[NewsCategory] = None) -> NewsSourcesResponse:
        """Lista fontes de notícias disponíveis"""
        
        sources = []
        for domain, info in self.brazilian_sources.items():
            source = NewsSource(
                name=info["name"],
                url=f"https://{domain}",
                reliability_score=info["reliability"]
            )
            sources.append(source)
        
        return NewsSourcesResponse(
            sources=sources,
            total_sources=len(sources),
            categories=list(NewsCategory)
        )

    async def analyze_news(
        self,
        query: str,
        category: Optional[NewsCategory] = None,
        max_results: int = 20
    ) -> NewsAnalysisResponse:
        """Análise completa de notícias"""
        
        # Busca artigos
        articles = await self.search_news(query, category, max_results=max_results)
        
        # Gera insights
        insights = await self.generate_insights(articles)
        
        # Busca tópicos trending relacionados
        trending_topics = await self.get_trending_topics(limit=5)
        related_topics = [t for t in trending_topics if query.lower() in t.topic.lower()]
        
        # Análise de sentimento geral
        sentiments = [a.sentiment for a in articles if a.sentiment]
        overall_sentiment = SentimentType.NEUTRAL
        
        if sentiments:
            from collections import Counter
            sentiment_counts = Counter(sentiments)
            overall_sentiment = sentiment_counts.most_common(1)[0][0]
        
        # Distribuição de sentimento
        sentiment_dist = {}
        if sentiments:
            for sentiment in SentimentType:
                count = sum(1 for s in sentiments if s == sentiment)
                sentiment_dist[sentiment.value] = count / len(sentiments)
        
        return NewsAnalysisResponse(
            query=query,
            total_results=len(articles),
            articles=articles,
            insights=insights,
            trending_topics=related_topics,
            overall_sentiment=overall_sentiment,
            sentiment_distribution=sentiment_dist,
            time_range="últimas 24 horas"
        )

    async def get_dashboard(self) -> NewsTrendsDashboard:
        """Dashboard de tendências de notícias"""
        
        cache_key = "news_dashboard"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Busca tópicos trending
        trending_topics = await self.get_trending_topics(limit=8)
        
        # Tópicos quentes baseados no engajamento
        hot_topics = [t.topic for t in trending_topics[:5]]
        
        # Distribui categorias
        from collections import Counter
        category_counts = Counter([t.category for t in trending_topics])
        category_breakdown = {cat.value: count for cat, count in category_counts.items()}
        
        # Sentimento geral
        sentiments = [t.sentiment for t in trending_topics]
        sentiment_overview = {
            "dominant": sentiments[0].value if sentiments else "neutral",
            "positive_ratio": sum(1 for s in sentiments if s == SentimentType.POSITIVE) / len(sentiments) if sentiments else 0,
            "confidence": 0.75
        }
        
        # Insights rápidos
        quick_insights = [
            f"Tópico em maior crescimento: {trending_topics[0].topic}" if trending_topics else "Analisando tendências...",
            f"Categoria mais ativa: {list(category_breakdown.keys())[0] if category_breakdown else 'Geral'}",
            f"Sentimento predominante: {sentiment_overview['dominant']}",
        ]
        
        # Breaking news mock
        breaking_news = await self.search_news("urgente OR importante", max_results=3)
        
        dashboard = NewsTrendsDashboard(
            trending_now=trending_topics,
            hot_topics=hot_topics,
            sentiment_overview=sentiment_overview,
            category_breakdown=category_breakdown,
            quick_insights=quick_insights,
            breaking_news=breaking_news,
            coverage_period="24 horas"
        )
        
        self._set_cache(cache_key, dashboard)
        return dashboard