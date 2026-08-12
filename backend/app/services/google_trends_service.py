# app/services/google_trends_service.py
from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

try:
    from pytrends.request import TrendReq
    from pytrends.exceptions import TooManyRequestsError
except Exception:
    TrendReq = None

    class TooManyRequestsError(Exception):
        pass

from ..schemas.trends_schema import (
    TrendingPeriod,
    CompetitionLevel,
    OpportunityType,
    ContentType,
    TrendMetrics,
    GeographicInsight,
    SmartQuery,
    TrendingTopic,
    ContentOpportunity,
    TrendAnalysisResult,
    QuickTrendSummary,
)

logger = logging.getLogger("app.services.google_trends_service")

# ============================== CONSTANTES ==============================

BR_UF: Dict[str, str] = {
    "Acre": "AC",
    "Alagoas": "AL",
    "Amapá": "AP",
    "Amazonas": "AM",
    "Bahia": "BA",
    "Ceará": "CE",
    "Distrito Federal": "DF",
    "Espírito Santo": "ES",
    "Goiás": "GO",
    "Maranhão": "MA",
    "Mato Grosso": "MT",
    "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG",
    "Pará": "PA",
    "Paraíba": "PB",
    "Paraná": "PR",
    "Pernambuco": "PE",
    "Piauí": "PI",
    "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS",
    "Rondônia": "RO",
    "Roraima": "RR",
    "Santa Catarina": "SC",
    "São Paulo": "SP",
    "Sergipe": "SE",
    "Tocantins": "TO",
}

PN_MAP = {"BR": "brazil", "US": "united_states", "GB": "united_kingdom", "PT": "portugal"}

# ======================= NORMALIZADORES (COERCERS) =======================

def coerce_opp_type(value: Union[str, OpportunityType, None]) -> OpportunityType:
    """
    Normaliza strings PT/EN e sinônimos para OpportunityType canônico.
    Ex.: "nicho_especifico" -> OpportunityType.NICHE
    """
    if isinstance(value, OpportunityType):
        return value
    if not value:
        return OpportunityType.NICHE

    v = str(value).strip().lower().replace(" ", "_")

    mapping = {
        # PT-BR
        "nicho": OpportunityType.NICHE,
        "nicho_especifico": OpportunityType.NICHE,
        "tendencia": OpportunityType.TRENDING,
        "em_alta": OpportunityType.TRENDING,
        "viral": OpportunityType.VIRAL,
        "perene": OpportunityType.EVERGREEN,
        "sazonal": OpportunityType.SEASONAL,
        "declinando": OpportunityType.DECLINING,
        # EN
        "niche": OpportunityType.NICHE,
        "trending": OpportunityType.TRENDING,
        "evergreen": OpportunityType.EVERGREEN,
        "seasonal": OpportunityType.SEASONAL,
        "declining": OpportunityType.DECLINING,
    }
    return mapping.get(v, OpportunityType.NICHE)


def coerce_content_type(value: Union[str, ContentType, None]) -> ContentType:
    """
    Normaliza strings PT/EN para ContentType canônico.
    Se o Enum não tiver o tipo (ex.: GUIDE/INFOGRAPHIC), faz fallback.
    """
    if isinstance(value, ContentType):
        return value
    if not value:
        return ContentType.ARTICLE

    v = str(value).strip().lower().replace(" ", "_")
    # Mapeia PT → EN do Enum existente
    mapping: Dict[str, ContentType] = {
        "artigo": ContentType.ARTICLE,
        "post": ContentType.ARTICLE,
        "video": ContentType.VIDEO,
        "vídeo": ContentType.VIDEO,
        "tutorial": ContentType.TUTORIAL,
        # opcionais: só se existirem no Enum do seu schema
        "guia": getattr(ContentType, "GUIDE", ContentType.ARTICLE),
        "infografico": getattr(ContentType, "INFOGRAPHIC", ContentType.ARTICLE),
        "infográfico": getattr(ContentType, "INFOGRAPHIC", ContentType.ARTICLE),
        "podcast": getattr(ContentType, "PODCAST", ContentType.VIDEO),
        # EN canônicos
        "article": ContentType.ARTICLE,
        "guide": getattr(ContentType, "GUIDE", ContentType.ARTICLE),
        "infographic": getattr(ContentType, "INFOGRAPHIC", ContentType.ARTICLE),
        "podcast": getattr(ContentType, "PODCAST", ContentType.VIDEO),
    }
    return mapping.get(v, ContentType.ARTICLE)


class GoogleTrendsService:
    """
    Serviço otimizado do Google Trends:
    - Rate limiting inteligente
    - Cache expandido
    - Fallbacks robustos
    - Processamento paralelo
    """

    def __init__(self, hl: str = "pt-BR", tz: int = 180) -> None:
        self.pytrends: Optional[TrendReq] = None

        # Controle de taxa otimizado
        self._sem = asyncio.Semaphore(2)  # permite 2 chamadas paralelas
        self._last_call = 0.0
        self._min_gap_seconds = 2.0  # gap reduzido

        # Cache expandido
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._session_cache: Dict[str, Any] = {}

        self._initialize_pytrends(hl=hl, tz=tz)

    def _initialize_pytrends(self, hl: str, tz: int) -> None:
        if TrendReq is None:
            logger.error("pytrends não instalado. Rode: pip install pytrends")
            self.pytrends = None
            return

        ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        try:
            self.pytrends = TrendReq(
                hl=hl,
                tz=tz,
                timeout=(8, 20),
                retries=0,
                backoff_factor=0.0,
                requests_args={
                    "verify": True,
                    "headers": {
                        "User-Agent": ua,
                        "Accept": "application/json, text/plain, */*",
                        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                    },
                },
            )
            logger.info("Google Trends conectado - modo otimizado")
        except Exception as e:
            logger.error("Erro ao iniciar pytrends: %s", e)
            self.pytrends = None

    def _ensure_ready(self) -> None:
        if not self.pytrends:
            raise RuntimeError("Google Trends indisponível. Verifique dependências e rede.")

    # ------------------------------- Cache -------------------------------

    def _cache_get(self, key: str, ttl: float = 1800.0):
        hit = self._cache.get(key)
        if not hit:
            return None
        ts, val = hit
        if (time.time() - ts) <= ttl:
            return val
        self._cache.pop(key, None)
        return None

    def _cache_put(self, key: str, val: Any) -> None:
        self._cache[key] = (time.time(), val)

    def _session_cache_get(self, key: str):
        return self._session_cache.get(key)

    def _session_cache_put(self, key: str, val: Any):
        self._session_cache[key] = val

    # -------------------------- Controle de taxa -------------------------

    async def _throttled_call(self, fn, *args, **kwargs):
        async with self._sem:
            gap = self._min_gap_seconds - (time.monotonic() - self._last_call)
            if gap > 0:
                await asyncio.sleep(gap + random.uniform(0, 0.2))
            try:
                return await asyncio.to_thread(fn, *args, **kwargs)
            finally:
                self._last_call = time.monotonic()

    async def _with_backoff(self, fn, *args, **kwargs):
        delay = 1.5
        tries = 0
        last_exc: Optional[Exception] = None

        while tries < 5:
            try:
                return await self._throttled_call(fn, *args, **kwargs)
            except TooManyRequestsError as e:
                last_exc = e
                tries += 1
                jitter = random.uniform(0, 0.3)
                await asyncio.sleep(delay + jitter)
                delay = min(30.0, delay * 1.6)
            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e):
                    last_exc = e
                    tries += 1
                    await asyncio.sleep(delay)
                    delay *= 1.5
                else:
                    raise e

        raise last_exc if last_exc else RuntimeError("Rate limited pelo Google Trends")

    # ------------------------------- Helpers -----------------------------

    @staticmethod
    def _tf(period: TrendingPeriod | str) -> str:
        return period.value if isinstance(period, TrendingPeriod) else str(period)

    @staticmethod
    def _kwlist(kw: str | List[str]) -> List[str]:
        if kw is None:
            return []
        if isinstance(kw, str):
            k = kw.strip()
            return [k] if k else []
        return [str(x).strip() for x in kw if str(x).strip()]

    @staticmethod
    def _pn(geo: str) -> str:
        return PN_MAP.get(geo.upper(), "brazil")

    # ============================= MÉTODOS PRINCIPAIS =============================

    async def get_daily_trends(self, geo: str = "BR", limit: int = 15) -> List[TrendingTopic]:
        """Tendências diárias com cache inteligente"""
        self._ensure_ready()

        cache_key = f"daily_trends_{geo}_{limit}"
        cached = self._cache_get(cache_key, ttl=600)  # 10min
        if cached is not None:
            logger.info(f"Cache hit para daily trends {geo}")
            return cached

        titles: List[str] = []

        try:
            # realtime primeiro
            df = await self._with_backoff(self.pytrends.realtime_trending_searches, pn=self._pn(geo))
            if df is not None and not df.empty:
                recs = df.to_dict("records")
                titles = [
                    (r.get("title") or r.get("query"))
                    for r in recs
                    if r.get("title") or r.get("query")
                ][:limit]
                logger.info(f"Realtime trends: {len(titles)} itens")
        except Exception as e:
            logger.warning(f"Realtime trends falhou: {type(e).__name__}")

        # fallback
        if not titles:
            try:
                df = await self._with_backoff(self.pytrends.trending_searches, pn=self._pn(geo))
                if df is not None and not df.empty:
                    titles = [str(v[0]) for _, v in df.head(limit).iterrows()]
                    logger.info(f"Trending searches: {len(titles)} itens")
            except Exception as e:
                logger.error(f"Trending searches falhou: {type(e).__name__}")
                titles = []

        if not titles:
            titles = [
                "inteligência artificial",
                "criptomoedas",
                "sustentabilidade",
                "trabalho remoto",
                "educação online",
                "e-commerce",
            ][:limit]
            logger.warning("Usando fallback de tendências")

        topics: List[TrendingTopic] = []
        batch_size = 3
        for i in range(0, len(titles), batch_size):
            batch = titles[i : i + batch_size]
            tasks = [self._build_trending_topic_fast(title, geo) for title in batch]
            batch_topics = await asyncio.gather(*tasks, return_exceptions=True)
            for topic in batch_topics:
                if isinstance(topic, Exception):
                    logger.warning(f"Falha ao processar tópico: {type(topic).__name__}")
                    continue
                if topic:
                    topics.append(topic)

        self._cache_put(cache_key, topics)
        logger.info(f"Daily trends processadas: {len(topics)} tópicos")
        return topics

    async def _build_trending_topic_fast(self, title: str, geo: str) -> Optional[TrendingTopic]:
        """Helper para construir tópico rapidamente"""
        try:
            series_task = asyncio.create_task(
                self.get_interest_over_time([title], timeframe=TrendingPeriod.LAST_3_MONTHS.value, geo=geo)
            )
            try:
                series = await asyncio.wait_for(series_task, timeout=8.0)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout na série para '{title}'")
                series = {"interest_over_time": []}

            metrics = self._metrics_from_interest_result(title, series)

            geo_breakdown = []
            if metrics.average_interest > 10:
                try:
                    geo_task = self.get_geography_interest(
                        title,
                        timeframe=TrendingPeriod.LAST_12_MONTHS.value,
                        geo=geo,
                        top_n=5,
                    )
                    geo_breakdown = await asyncio.wait_for(geo_task, timeout=5.0)
                except asyncio.TimeoutError:
                    pass

            return TrendingTopic(
                title=title,
                category="Geral",
                metrics=metrics,
                estimated_searches=self._estimate_search_bucket(metrics.current_interest, metrics.peak_interest),
                competition_level=self._estimate_competition(metrics),
                opportunity_type=self._classify_opportunity(metrics),
                best_time_to_publish=self._best_time_from_metrics(metrics),
                trend_duration=self._trend_duration_from_metrics(metrics),
                top_regions=geo_breakdown,
                related_opportunities=[],
                confidence_score=self._confidence_from_metrics(metrics, 0, len(geo_breakdown)),
            )
        except Exception as e:
            logger.warning(f"Falha ao construir tópico '{title}': {type(e).__name__}")
            return None

    async def get_interest_over_time(
        self,
        keywords: List[str],
        timeframe: str = TrendingPeriod.LAST_12_MONTHS.value,
        geo: str = "BR",
        category: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Interest over time com cache e fallbacks"""
        self._ensure_ready()

        kw = self._kwlist(keywords[:1])
        if not kw:
            return {"interest_over_time": []}

        cache_key = f"iot|{tuple(kw)}|{timeframe}|{geo}|{category}"
        cached = self._cache_get(cache_key, ttl=1200)  # 20min
        if cached is not None:
            return cached

        try:
            await self._with_backoff(self.pytrends.build_payload, kw, cat=category or 0, timeframe=timeframe, geo=geo)
            df = await self._with_backoff(self.pytrends.interest_over_time)

            if df is None or df.empty:
                result = {"interest_over_time": []}
            else:
                result = self._process_interest_dataframe(df, kw[0])

            self._cache_put(cache_key, result)
            return result

        except Exception as e:
            logger.warning(f"Interest over time falhou para '{kw[0]}': {type(e).__name__}")
            fallback = self._generate_synthetic_interest(kw[0])
            self._cache_put(cache_key, fallback)
            return fallback

    def _process_interest_dataframe(self, df: pd.DataFrame, keyword: str) -> Dict[str, Any]:
        series: List[Dict[str, Any]] = []

        for ts, row in df.iterrows():
            point = {"date": ts.isoformat()}
            val = row.get(keyword, 0)
            try:
                v = 0 if (pd.isna(val) or (isinstance(val, float) and math.isnan(val))) else int(val)
            except Exception:
                v = int(val) if isinstance(val, (int, float)) else 0
            point[keyword] = v
            series.append(point)

        metrics = self._metrics_from_series(keyword, series)

        return {
            "interest_over_time": series,
            "current_interest": metrics.current_interest,
            "peak_interest": metrics.peak_interest,
            "average_interest": metrics.average_interest,
            "growth_rate": metrics.growth_rate,
            "volatility": metrics.volatility,
            "trend_direction": metrics.trend_direction,
            "data_source": "Google Trends (pytrends)",
        }

    def _generate_synthetic_interest(self, keyword: str) -> Dict[str, Any]:
        import random

        base_interest = 15 if len(keyword) > 10 else 25
        if any(word in keyword.lower() for word in ["ai", "inteligencia", "crypto", "bitcoin"]):
            base_interest = 40
        elif any(word in keyword.lower() for word in ["moda", "receita", "dica"]):
            base_interest = 30

        series = []
        current_date = datetime.now()

        for i in range(90):  # 90 dias
            date = current_date - timedelta(days=90 - i)
            noise = random.randint(-8, 12)
            value = max(0, min(100, base_interest + noise))

            series.append({"date": date.isoformat(), keyword: value})

        metrics = self._metrics_from_series(keyword, series)

        return {
            "interest_over_time": series,
            "current_interest": metrics.current_interest,
            "peak_interest": metrics.peak_interest,
            "average_interest": metrics.average_interest,
            "growth_rate": metrics.growth_rate,
            "volatility": metrics.volatility,
            "trend_direction": metrics.trend_direction,
            "data_source": "Synthetic (fallback)",
        }

    async def get_geography_interest(
        self,
        keyword: str,
        timeframe: str = TrendingPeriod.LAST_12_MONTHS.value,
        geo: str = "BR",
        top_n: int = 8,
    ) -> List[GeographicInsight]:
        """Geografia com cache e fallback"""
        self._ensure_ready()

        cache_key = f"geo|{keyword}|{timeframe}|{geo}|{top_n}"
        cached = self._cache_get(cache_key, ttl=1800)  # 30min
        if cached is not None:
            return cached

        try:
            await self._with_backoff(self.pytrends.build_payload, [keyword], timeframe=timeframe, geo=geo)
            df = await self._with_backoff(
                self.pytrends.interest_by_region, resolution="region", inc_low_vol=True, inc_geo_code=False
            )

            if df is None or df.empty or keyword not in df.columns:
                result = []
            else:
                result = self._process_geography_dataframe(df, keyword, top_n)

            self._cache_put(cache_key, result)
            return result

        except Exception as e:
            logger.warning(f"Geography falhou para '{keyword}': {type(e).__name__}")
            fallback = self._generate_fallback_geography(keyword, top_n)
            self._cache_put(cache_key, fallback)
            return fallback

    def _process_geography_dataframe(self, df: pd.DataFrame, keyword: str, top_n: int) -> List[GeographicInsight]:
        df2 = df.sort_values(by=keyword, ascending=False).head(top_n)

        out: List[GeographicInsight] = []
        rank = 1

        for region, row in df2.iterrows():
            raw = row.get(keyword, 0)
            try:
                score = 0 if (pd.isna(raw) or (isinstance(raw, float) and math.isnan(raw))) else int(raw)
            except Exception:
                score = int(raw) if isinstance(raw, (int, float)) else 0

            uf = BR_UF.get(str(region))
            if not uf:
                continue

            out.append(
                GeographicInsight(region=str(region), state_code=uf, interest_score=score, interest_rank=rank)
            )
            rank += 1

        return out

    def _generate_fallback_geography(self, keyword: str, top_n: int) -> List[GeographicInsight]:
        fallback_states = [
            ("São Paulo", "SP", 85),
            ("Rio de Janeiro", "RJ", 72),
            ("Minas Gerais", "MG", 65),
            ("Bahia", "BA", 58),
            ("Paraná", "PR", 55),
            ("Rio Grande do Sul", "RS", 52),
            ("Pernambuco", "PE", 48),
            ("Ceará", "CE", 45),
        ]

        return [
            GeographicInsight(region=region, state_code=uf, interest_score=score, interest_rank=i + 1)
            for i, (region, uf, score) in enumerate(fallback_states[:top_n])
        ]

    async def get_related_topics(
        self,
        keyword: str,
        timeframe: str = TrendingPeriod.LAST_12_MONTHS.value,
        geo: str = "BR",
        top_n: int = 4,
    ) -> List[TrendingTopic]:
        """Related topics com cache"""
        self._ensure_ready()

        cache_key = f"related|{keyword}|{timeframe}|{geo}|{top_n}"
        cached = self._cache_get(cache_key, ttl=1800)  # 30min
        if cached is not None:
            return cached

        try:
            names = await self._safe_related_topic_names(keyword, timeframe, geo)
            topics: List[TrendingTopic] = []

            tasks = []
            for name in names[:top_n]:
                task = self._build_related_topic_fast(name, timeframe, geo)
                tasks.append(task)

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Exception):
                        continue
                    if result:
                        topics.append(result)

            self._cache_put(cache_key, topics)
            return topics

        except Exception as e:
            logger.warning(f"Related topics falhou para '{keyword}': {type(e).__name__}")
            return []

    async def _build_related_topic_fast(self, name: str, timeframe: str, geo: str) -> Optional[TrendingTopic]:
        try:
            series = await asyncio.wait_for(
                self.get_interest_over_time([name], timeframe=timeframe, geo=geo), timeout=6.0
            )

            metrics = self._metrics_from_interest_result(name, series)

            return TrendingTopic(
                title=name,
                category="Relacionado",
                metrics=metrics,
                estimated_searches=self._estimate_search_bucket(metrics.current_interest, metrics.peak_interest),
                competition_level=self._estimate_competition(metrics),
                opportunity_type=self._classify_opportunity(metrics),
                best_time_to_publish=self._best_time_from_metrics(metrics),
                trend_duration=self._trend_duration_from_metrics(metrics),
                top_regions=[],
                related_opportunities=[],
                confidence_score=self._confidence_from_metrics(metrics, 0, 0),
            )
        except Exception:
            return None

    async def analyze_content_opportunity(self, keyword: str) -> Dict[str, Any]:
        """Análise de oportunidade com cache"""
        cache_key = f"opportunity|{keyword}"
        cached = self._cache_get(cache_key, ttl=900)  # 15min
        if cached is not None:
            return cached

        try:
            # paralelo
            series_task = self.get_interest_over_time([keyword], timeframe=TrendingPeriod.LAST_12_MONTHS.value, geo="BR")
            related_task = self._get_related_queries(keyword, timeframe=TrendingPeriod.LAST_12_MONTHS.value, geo="BR", top_n=6)

            series, target_keywords = await asyncio.gather(series_task, related_task, return_exceptions=True)

            if isinstance(series, Exception):
                series = {"interest_over_time": []}
            if isinstance(target_keywords, Exception):
                target_keywords = []

            metrics = self._metrics_from_interest_result(keyword, series)
            competition = self._estimate_competition(metrics)
            opp_type = self._classify_opportunity(metrics)

            result = {
                "keyword": keyword,
                "opportunity_type": opp_type.value,  # mantém como string canônica
                "market_analysis": {
                    "current_interest": metrics.current_interest,
                    "peak_interest": metrics.peak_interest,
                    "average_interest": metrics.average_interest,
                    "growth_rate_12m": metrics.growth_rate,
                    "demand_trend": metrics.trend_direction,
                },
                "competition_analysis": {"level": competition.value},
                "content_angles": [
                    f"Guia completo sobre {keyword}",
                    f"Como usar {keyword} na prática",
                    f"Erros comuns em {keyword}",
                    f"{keyword} para iniciantes: passo a passo",
                ],
                "target_keywords": [tk.model_dump() for tk in target_keywords],
                "content_types": [ContentType.ARTICLE.value, ContentType.VIDEO.value, ContentType.TUTORIAL.value],
                "urgency_level": self._urgency_from_direction(metrics.trend_direction),
                "best_channels": ["Blog", "YouTube", "Instagram"],
                "estimated_roi": self._roi_from_metrics(metrics),
                "target_personas": ["público geral", "iniciantes"],
                "audience_size": self._estimate_audience_bucket(metrics),
            }

            self._cache_put(cache_key, result)
            return result

        except Exception as e:
            logger.warning(f"Opportunity analysis falhou para '{keyword}': {type(e).__name__}")
            return {
                "keyword": keyword,
                "opportunity_type": OpportunityType.NICHE.value,
                "market_analysis": {"current_interest": 0, "peak_interest": 0, "average_interest": 0.0},
                "competition_analysis": {"level": CompetitionLevel.MEDIUM.value},
                "content_angles": [f"Introdução a {keyword}"],
                "target_keywords": [],
                "content_types": [ContentType.ARTICLE.value],
                "urgency_level": "media",
                "best_channels": ["Blog"],
                "estimated_roi": "Baixo",
                "target_personas": ["público geral"],
                "audience_size": "1K-10K pessoas",
            }

    async def get_content_opportunities_quick(self, limit: int = 8) -> List[ContentOpportunity]:
        topics = await self.get_daily_trends(geo="BR", limit=limit)
        out: List[ContentOpportunity] = []
        for t in topics:
            out.append(
                ContentOpportunity(
                    topic=t.title,
                    hook=f"{t.title}: guia prático",
                    opportunity_type=t.opportunity_type,
                    market_analysis={"interest": t.metrics.current_interest, "growth_rate": t.metrics.growth_rate},
                    competition_analysis={"level": t.competition_level.value},
                    content_angles=[f"Introdução a {t.title}", f"Como aplicar {t.title}"],
                    target_keywords=[],
                    content_types=[ContentType.ARTICLE, ContentType.VIDEO],
                    urgency_level=self._urgency_from_direction(t.metrics.trend_direction),
                    best_channels=["Blog", "YouTube"],
                    estimated_roi=self._roi_from_metrics(t.metrics),
                    target_personas=["público geral"],
                    audience_size=self._estimate_audience_bucket(t.metrics),
                )
            )
        return out

    async def get_opportunities_for_keywords(self, keywords: List[str], industry: Optional[str] = None) -> List[ContentOpportunity]:
        """Oportunidades para múltiplas keywords"""
        out: List[ContentOpportunity] = []
        for kw in keywords:
            try:
                data = await self.analyze_content_opportunity(kw)
            except TooManyRequestsError:
                logger.warning("Rate limited - usando fallback para '%s'", kw)
                data = {
                    "keyword": kw,
                    "opportunity_type": OpportunityType.NICHE.value,
                    "market_analysis": {"current_interest": 0, "peak_interest": 0, "average_interest": 0.0},
                    "competition_analysis": {"level": CompetitionLevel.MEDIUM.value},
                    "content_angles": [f"Introdução a {kw}"],
                    "target_keywords": [],
                    "content_types": [ContentType.ARTICLE.value],
                    "urgency_level": "media",
                    "best_channels": ["Blog"],
                    "estimated_roi": "Baixo",
                    "target_personas": ["público geral"],
                    "audience_size": "0-1K pessoas",
                }
            except Exception as e:
                logger.exception("Falha ao gerar oportunidade para %s: %s", kw, e)
                continue
            out.append(self._content_opp_from_dict(data))
        return out

    async def build_trend_analysis_result(
        self,
        keyword: str,
        interest_data: Dict[str, Any],
        geo_data: List[GeographicInsight],
        related_data: List[TrendingTopic],
        opportunity_data: Dict[str, Any],
    ) -> TrendAnalysisResult:
        metrics = self._metrics_from_interest_result(keyword, interest_data)
        seasonal = self._seasonal_from_series(interest_data, keyword)
        future = self._predict_from_series(interest_data, keyword)
        content_opp = self._content_opp_from_dict(opportunity_data)

        content_gaps = [
            f"Tutorial passo a passo sobre {keyword}",
            f"Casos de uso de {keyword} no Brasil",
            f"Ferramentas essenciais para {keyword}",
        ]

        return TrendAnalysisResult(
            keyword=keyword,
            overall_metrics=metrics,
            geographical_breakdown=geo_data,
            historical_performance=interest_data.get("interest_over_time", []),
            seasonal_patterns=seasonal,
            future_predictions=future,
            related_topics=related_data,
            competitor_content=[],
            content_gaps=content_gaps,
            opportunities=[content_opp],
            quick_wins=[f"Criar guia introdutório sobre {keyword}", f"Checklist prático de {keyword}"],
            long_term_strategy={
                "focus": f"Construir autoridade em {keyword}",
                "pillars": ["Educação", "Casos práticos", "Tendências"],
                "horizon": "6-12 meses",
            },
        )

    def to_quick_summary(self, t: TrendingTopic) -> QuickTrendSummary:
        status = self._status_from_metrics(t.metrics)
        difficulty = self._difficulty_label_from_competition(t.competition_level)
        best_action = self._best_action_from_opp_type(t.opportunity_type)
        return QuickTrendSummary(
            topic=t.title,
            status=status,
            opportunity_score=t.confidence_score,
            estimated_traffic=self._estimate_audience_bucket(t.metrics),
            difficulty=difficulty,
            best_action=best_action,
        )

    # ============================= HELPERS INTERNOS =============================

    async def _safe_related_topic_names(self, keyword: str, timeframe: str, geo: str) -> List[str]:
        try:
            await self._with_backoff(self.pytrends.build_payload, [keyword], timeframe=timeframe, geo=geo)
            rel = await self._with_backoff(self.pytrends.related_topics)
            bucket = rel.get(keyword)
            if not bucket:
                return []
            top_df = bucket.get("top")
            if top_df is None or top_df.empty:
                return []
            return list(top_df["topic_title"].dropna().unique())
        except Exception:
            return []

    async def _get_related_queries(self, keyword: str, timeframe: str, geo: str, top_n: int = 6) -> List[SmartQuery]:
        try:
            await self._with_backoff(self.pytrends.build_payload, [keyword], timeframe=timeframe, geo=geo)
            rq = await self._with_backoff(self.pytrends.related_queries)
            data = rq.get(keyword, {})
            top_df = data.get("top")
            if top_df is None or top_df.empty:
                return []

            out: List[SmartQuery] = []
            for _, row in top_df.head(top_n).iterrows():
                q = str(row.get("query", "")).strip()
                if not q:
                    continue
                raw = row.get("value", 0)
                try:
                    score = 0 if (pd.isna(raw) or (isinstance(raw, float) and math.isnan(raw))) else int(raw)
                except Exception:
                    score = int(raw) if isinstance(raw, (int, float)) else 0

                volume_bucket = self._volume_bucket_from_value(score)
                difficulty = self._difficulty_from_value(score)
                opp_score = max(0, min(100, score))

                out.append(
                    SmartQuery(
                        text=q,
                        search_volume=volume_bucket,
                        difficulty=difficulty,
                        intent="informacional",
                        opportunity_score=opp_score,
                    )
                )
            return out
        except Exception:
            return []

    def _metrics_from_interest_result(self, keyword: str, result: Dict[str, Any]) -> TrendMetrics:
        points = result.get("interest_over_time", [])
        return self._metrics_from_series(keyword, points)

    def _metrics_from_series(self, keyword: str, series_points: List[Dict[str, Any]]) -> TrendMetrics:
        values: List[int] = [int(p.get(keyword, 0)) for p in series_points if keyword in p]

        if not values:
            return TrendMetrics(
                current_interest=0,
                peak_interest=0,
                average_interest=0.0,
                growth_rate=None,
                volatility=None,
                trend_direction="desconhecido",
            )

        current = values[-1]
        peak = max(values)
        avg = sum(values) / max(1, len(values))

        if len(values) >= 24:
            prev_avg = sum(values[-24:-12]) / 12
            recent_avg = sum(values[-12:]) / 12
            growth = 0.0 if prev_avg == 0 else ((recent_avg - prev_avg) / prev_avg) * 100.0
            growth = round(growth, 2)
        else:
            growth = None

        if len(values) > 1 and avg > 0:
            var = sum((v - avg) ** 2 for v in values) / len(values)
            std = math.sqrt(var)
            volatility = round(std / avg, 3)
        else:
            volatility = None

        tail = values[-4:] if len(values) >= 4 else values
        delta = current - int(sum(tail) / max(1, len(tail)))
        if delta > 2:
            direction = "crescendo"
        elif delta < -2:
            direction = "decaindo"
        else:
            direction = "estavel"

        return TrendMetrics(
            current_interest=int(current),
            peak_interest=int(peak),
            average_interest=round(avg, 2),
            growth_rate=growth,
            volatility=volatility,
            trend_direction=direction,
        )

    def _estimate_search_bucket(self, current: int, peak: int) -> str:
        score = (current + peak) / 2
        if score >= 90:
            return "2M+ / mês"
        if score >= 75:
            return "500K-2M / mês"
        if score >= 60:
            return "100K-500K / mês"
        if score >= 40:
            return "10K-100K / mês"
        return "1K-10K / mês"

    def _estimate_audience_bucket(self, m: TrendMetrics) -> str:
        return self._estimate_search_bucket(m.current_interest, m.peak_interest).replace("/ mês", "+ pessoas")

    def _estimate_competition(self, m: TrendMetrics) -> CompetitionLevel:
        if m.peak_interest >= 90 and (m.volatility is None or m.volatility <= 0.15):
            return CompetitionLevel.VERY_HIGH
        if m.peak_interest >= 75:
            return CompetitionLevel.HIGH
        if m.peak_interest >= 55:
            return CompetitionLevel.MEDIUM
        if m.peak_interest >= 35:
            return CompetitionLevel.LOW
        return CompetitionLevel.VERY_LOW

    def _classify_opportunity(self, m: TrendMetrics) -> OpportunityType:
        if m.trend_direction == "crescendo" and (m.growth_rate or 0) > 25:
            return OpportunityType.VIRAL
        if m.trend_direction == "crescendo":
            return OpportunityType.TRENDING
        if (m.volatility or 0.0) < 0.12 and m.average_interest >= 50:
            return OpportunityType.EVERGREEN
        if m.trend_direction == "decaindo":
            return OpportunityType.DECLINING
        return OpportunityType.NICHE

    def _best_time_from_metrics(self, m: TrendMetrics) -> str:
        if m.trend_direction == "crescendo":
            return "Próximas 4-6 semanas"
        if m.trend_direction == "decaindo":
            return "Reavaliar antes de publicar"
        return "Qualquer época"

    def _trend_duration_from_metrics(self, m: TrendMetrics) -> str:
        vol = m.volatility or 0.0
        if vol >= 0.3:
            return "Curta (semanas)"
        if vol >= 0.18:
            return "Média (1-3 meses)"
        return "Longa (3-12 meses)"

    def _confidence_from_metrics(self, m: TrendMetrics, n_related: int, n_regions: int) -> int:
        base = 50
        base += min(25, max(0, int(m.average_interest / 2)))
        base += min(10, n_related * 2)
        base += min(10, n_regions * 2)
        base -= int((m.volatility or 0.0) * 10)
        return max(0, min(100, base))

    def _volume_bucket_from_value(self, val: int) -> str:
        if val >= 90:
            return "500K-2M"
        if val >= 75:
            return "100K-500K"
        if val >= 60:
            return "10K-100K"
        if val >= 40:
            return "1K-10K"
        return "0-1K"

    def _difficulty_from_value(self, val: int) -> CompetitionLevel:
        if val >= 85:
            return CompetitionLevel.VERY_HIGH
        if val >= 70:
            return CompetitionLevel.HIGH
        if val >= 50:
            return CompetitionLevel.MEDIUM
        if val >= 30:
            return CompetitionLevel.LOW
        return CompetitionLevel.VERY_LOW

    def _urgency_from_direction(self, direction: str) -> str:
        if direction == "crescendo":
            return "alta"
        if direction == "decaindo":
            return "baixa"
        return "media"

    def _roi_from_metrics(self, m: TrendMetrics) -> str:
        if m.trend_direction == "crescendo" and m.average_interest >= 60:
            return "Alto"
        if m.average_interest >= 45:
            return "Médio"
        return "Baixo"

    def _seasonal_from_series(self, series: Dict[str, Any], keyword: str) -> Dict[str, Any]:
        points = series.get("interest_over_time", [])
        if not points:
            return {"peak_months": [], "pattern_confidence": 0.3}
        month_scores: Dict[int, int] = {}
        for p in points:
            dt = datetime.fromisoformat(p["date"])
            month_scores[dt.month] = month_scores.get(dt.month, 0) + int(p.get(keyword, 0))
        top_months = sorted(month_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        names = [self._month_name(m) for m, _ in top_months]
        conf = 0.6 if len(points) >= 26 else 0.45
        return {"peak_months": names, "pattern_confidence": conf}

    def _predict_from_series(self, series: Dict[str, Any], keyword: str) -> Dict[str, Any]:
        points = series.get("interest_over_time", [])
        if not points:
            return {"next_30_days": "Estabilidade prevista", "confidence": 0.3}
        vals = [int(p.get(keyword, 0)) for p in points]
        half = len(vals) // 2
        prev = sum(vals[:half]) / max(1, len(vals[:half]))
        recent = sum(vals[half:]) / max(1, len(vals[half:]))
        if recent > prev * 1.1:
            label = "Crescimento moderado esperado"
        elif recent < prev * 0.9:
            label = "Queda moderada esperada"
        else:
            label = "Estabilidade prevista"
        conf = 0.6 if len(vals) >= 26 else 0.45
        return {"next_30_days": label, "confidence": conf}

    # ============================ CONVERSORES FINAIS ============================

    def _content_opp_from_dict(self, d: Dict[str, Any]) -> ContentOpportunity:
        """
        Converte dict (potencialmente vindo do LLM/externo) para ContentOpportunity,
        normalizando opportunity_type (aceita 'nicho_especifico', etc.) e content_types.
        """
        # opportunity_type: aceita PT/EN e enums
        opp_type = coerce_opp_type(d.get("opportunity_type"))

        # content_types: lista de strings/enums → lista de ContentType
        raw_cts = d.get("content_types", [ContentType.ARTICLE.value])
        content_types: List[ContentType] = []
        for ct in raw_cts:
            try:
                content_types.append(ContentType(ct))  # tenta cast direto
            except Exception:
                content_types.append(coerce_content_type(ct))  # normaliza PT/EN

        # target_keywords: podem vir como dicts parciais
        tks: List[SmartQuery] = []
        for tk in d.get("target_keywords", []):
            if isinstance(tk, SmartQuery):
                tks.append(tk)
                continue
            if isinstance(tk, dict):
                try:
                    tks.append(SmartQuery(**tk))
                    continue
                except Exception:
                    text = str(tk.get("text") or tk.get("keyword") or "").strip()
            else:
                text = str(tk).strip()
            if text:
                tks.append(
                    SmartQuery(
                        text=text,
                        search_volume="0-1K",
                        difficulty=CompetitionLevel.VERY_LOW,
                        intent="informacional",
                        opportunity_score=0,
                    )
                )

        return ContentOpportunity(
            topic=d.get("keyword", ""),
            hook=f"Guia Definitivo: {d.get('keyword', '').title()}",
            opportunity_type=opp_type,
            market_analysis=d.get("market_analysis", {}),
            competition_analysis=d.get("competition_analysis", {}),
            content_angles=d.get("content_angles", []),
            target_keywords=tks,
            content_types=content_types,
            urgency_level=d.get("urgency_level", "media"),
            best_channels=d.get("best_channels", ["Blog"]),
            estimated_roi=d.get("estimated_roi", "Médio"),
            target_personas=d.get("target_personas", ["público geral"]),
            audience_size=d.get("audience_size", "10K-100K pessoas"),
        )

    def _status_from_metrics(self, m: TrendMetrics) -> str:
        if m.trend_direction == "crescendo" and (m.growth_rate or 0) > 20:
            return "🔥 Em alta"
        if m.trend_direction == "crescendo":
            return "📈 Crescendo"
        if m.trend_direction == "estavel":
            return "📊 Estável"
        return "📉 Decaindo"

    def _difficulty_label_from_competition(self, c: CompetitionLevel) -> str:
        mapping = {
            CompetitionLevel.VERY_LOW: "Fácil",
            CompetitionLevel.LOW: "Fácil",
            CompetitionLevel.MEDIUM: "Médio",
            CompetitionLevel.HIGH: "Difícil",
            CompetitionLevel.VERY_HIGH: "Difícil",
        }
        return mapping.get(c, "Médio")

    def _best_action_from_opp_type(self, o: OpportunityType) -> str:
        return {
            OpportunityType.VIRAL: "Criar conteúdo urgente",
            OpportunityType.TRENDING: "Produzir série de conteúdos",
            OpportunityType.SEASONAL: "Planejar campanha sazonal",
            OpportunityType.NICHE: "Focar em conteúdo especializado",
            OpportunityType.EVERGREEN: "Criar conteúdo perene",
            OpportunityType.DECLINING: "Reposicionar ou pausar",
        }.get(o, "Criar conteúdo")

    @staticmethod
    def _month_name(m: int) -> str:
        nomes = [
            "",
            "janeiro",
            "fevereiro",
            "março",
            "abril",
            "maio",
            "junho",
            "julho",
            "agosto",
            "setembro",
            "outubro",
            "novembro",
            "dezembro",
        ]
        return nomes[m] if 1 <= m <= 12 else ""
