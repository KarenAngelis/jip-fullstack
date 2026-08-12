"""
RealMetricsService — Métricas objetivas + Google Trends para títulos e conteúdo

Conexões rápidas
- usado por: ai_service.py (opcional) para enriquecer metadados com breakdown real
- routers: content_generation.py chama para preencher métricas/fatores e estatísticas de tendência

Resumo
- Calcula métricas **reprodutíveis** de ENGAGEMENT, SEO e TENDÊNCIA para títulos (heurísticas locais).
- Integra **Google Trends** para o tópico (nível atual, pico, média 30d, momentum, score).
- Oferece helpers para consolidar tudo e **normalizar chaves** no formato esperado pelo app.

Principais métodos
- analyze_title_engagement(title, topic) -> { engagement_score, factors, recommendations }
- analyze_seo_potential(title, topic) -> { seo_score, factors, estimated_monthly_searches, recommendations }
- analyze_trend_relevance(title, topic) -> { trend_score, factors, trending_elements, recommendations }
- fetch_trends(query, timeframe, geo) -> { trend_current, trend_peak, trend_30d_avg, trend_momentum_pct, trend_score, ... }
- enrich_title_with_trends(title, topic, geo) -> merge(heurísticas locais + Google Trends)
- analyze_title_all(title, topic) -> { engagement_potential, seo_score, trend_relevance, ... }

Pontos de atenção
- Pesos/heurísticas são ajustáveis; pontuações são capadas em 0–100.
- Google Trends via `pytrends` não requer API key, mas está sujeito a limitações de rede.
- Se Trends retornar vazio, mantemos apenas as métricas locais sem quebrar o fluxo.
"""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from pytrends.request import TrendReq

logger = logging.getLogger(__name__)


class RealMetricsService:
    """Serviço para análise real de métricas de conteúdo (heurísticas + Trends)."""

    def __init__(
        self,
        trends_geo: str = "BR",
        trends_lang: str = "pt-BR",
        trends_timeframe: str = "today 12-m",
        retries: int = 2,
        backoff_factor: float = 0.1,
    ) -> None:
        # Palavras de alto engajamento (pesos heurísticos)
        self.engagement_keywords: Dict[str, int] = {
            "ultimate": 15,
            "complete": 12,
            "best": 10,
            "worst": 10,
            "secrets": 14,
            "hack": 12,
            "trick": 10,
            "guide": 8,
            "amazing": 8,
            "incredible": 9,
            "shocking": 12,
            "surprising": 10,
            "free": 11,
            "exclusive": 13,
            "limited": 9,
            "new": 6,
            "proven": 10,
            "guaranteed": 11,
            "instant": 9,
            "fast": 7,
        }

        # Palavras trending tech 2024/2025
        self.trending_tech_keywords: Dict[str, int] = {
            "ai": 20,
            "ia": 20,
            "chatgpt": 18,
            "gpt": 15,
            "automation": 12,
            "react": 10,
            "next.js": 8,
            "typescript": 7,
            "python": 8,
            "javascript": 6,
            "node.js": 5,
            "crypto": 10,
            "blockchain": 8,
            "nft": 6,
            "web3": 7,
            "startup": 9,
            "remote": 8,
            "productivity": 10,
            "youtube": 12,
            "tiktok": 10,
            "instagram": 8,
        }

        # Stop words (penalizam levemente SEO)
        self.seo_stop_words: set[str] = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "very",
            "really",
            "just",
            "only",
        }

        # Google Trends
        self.trends_geo = trends_geo
        self.trends_timeframe = trends_timeframe
        self._pytrends = TrendReq(hl=trends_lang, tz=0, retries=retries, backoff_factor=backoff_factor)

    # ------------------------
    # ENGAGEMENT
    # ------------------------
    def analyze_title_engagement(self, title: str, topic: str) -> Dict[str, Any]:
        """Análise de engajamento baseada em padrões de performance."""
        title_lower = title.lower()
        factors: Dict[str, int] = {}

        # 1) números
        numbers = re.findall(r"\b\d+\b", title)
        factors["numbers"] = len(numbers) * 12 if numbers else 0

        # 2) pergunta
        factors["question"] = 15 if title.strip().endswith("?") else 0

        # 3) power words
        power_word_score = 0
        for word, score in self.engagement_keywords.items():
            if word in title_lower:
                power_word_score += score
        factors["power_words"] = min(30, power_word_score)

        # 4) comprimento
        length = len(title)
        if 50 <= length <= 70:
            factors["optimal_length"] = 20
        elif 40 <= length <= 80:
            factors["optimal_length"] = 10
        else:
            factors["optimal_length"] = max(0, 20 - abs(length - 60) // 3)

        # 5) urgência/temporalidade
        urgency_words = ["now", "today", "2024", "2025", "new", "latest", "this year"]
        urgency_count = sum(1 for w in urgency_words if w in title_lower)
        factors["urgency"] = urgency_count * 8

        # 6) relevância ao tópico
        topic_words = topic.lower().split()
        topic_matches = sum(1 for w in topic_words if w and w in title_lower)
        factors["topic_relevance"] = min(25, topic_matches * 8)

        # 7) estrutura de lista
        list_pattern = r"\b\d+\s+(ways?|tips?|steps?|methods?|tricks?|hacks?|reasons?)\b"
        factors["list_structure"] = 15 if re.search(list_pattern, title_lower) else 0

        total_score = sum(factors.values())
        engagement_score = max(0, min(100, total_score))

        return {
            "engagement_score": engagement_score,
            "factors": factors,
            "recommendations": self._generate_engagement_recommendations(factors, title),
        }

    # ------------------------
    # SEO
    # ------------------------
    def analyze_seo_potential(self, title: str, topic: str) -> Dict[str, Any]:
        """Análise SEO baseada em boas práticas."""
        factors: Dict[str, int] = {}

        title_words = re.findall(r"\b\w+\b", title.lower())
        topic_words = topic.lower().split()

        # 1) presença de keywords
        keyword_density = sum(1 for w in title_words if w in topic_words)
        factors["keyword_presence"] = min(25, keyword_density * 8)

        # 2) comprimento SEO
        length = len(title)
        if 40 <= length <= 60:
            factors["seo_length"] = 25
        elif 30 <= length <= 70:
            factors["seo_length"] = 15
        else:
            factors["seo_length"] = max(0, 25 - abs(length - 50) // 2)

        # 3) long-tail
        word_count = len(title_words)
        if 6 <= word_count <= 12:
            factors["long_tail"] = 20
        elif 4 <= word_count <= 15:
            factors["long_tail"] = 10
        else:
            factors["long_tail"] = 0

        # 4) stop words
        stop_word_count = sum(1 for w in title_words if w in self.seo_stop_words)
        factors["stop_words"] = max(0, 15 - stop_word_count * 2)

        # 5) unicidade
        unique_words = len(set(title_words))
        factors["uniqueness"] = min(15, unique_words * 2)

        total_score = sum(factors.values())
        seo_score = max(0, min(100, total_score))

        return {
            "seo_score": seo_score,
            "factors": factors,
            "estimated_monthly_searches": self._estimate_search_volume(title, topic),
            "recommendations": self._generate_seo_recommendations(factors, title),
        }

    # ------------------------
    # TENDÊNCIA (heurística local)
    # ------------------------
    def analyze_trend_relevance(self, title: str, topic: str) -> Dict[str, Any]:
        """Relevância para tendências atuais (ano, techs, formato e sazonalidade)."""
        title_lower = title.lower()
        current_year = datetime.now().year
        factors: Dict[str, int] = {}

        # 1) ano atual (ou próximo)
        year_refs = [str(current_year), str(current_year + 1)]
        factors["current_year"] = 20 if any(y in title for y in year_refs) else 0

        # 2) tecnologias trending
        tech_score = 0
        for tech, score in self.trending_tech_keywords.items():
            if tech in title_lower or tech in topic.lower():
                tech_score += score
        factors["tech_relevance"] = min(30, tech_score)

        # 3) formatos em alta
        trending_formats: Dict[str, int] = {
            "tutorial": 8,
            "review": 6,
            "comparison": 7,
            "vs": 5,
            "beginner": 8,
            "advanced": 6,
            "complete": 7,
            "guide": 6,
        }
        format_score = sum(score for fmt, score in trending_formats.items() if fmt in title_lower)
        factors["format_trend"] = min(20, format_score)

        # 4) sazonalidade
        month = datetime.now().month
        seasonal_boost = self._get_seasonal_relevance(title_lower, month)
        factors["seasonality"] = seasonal_boost

        # 5) problema/solução
        problem_words = ["problem", "issue", "fix", "solve", "solution", "error", "bug"]
        factors["problem_solving"] = 10 if any(w in title_lower for w in problem_words) else 0

        total_score = sum(factors.values())
        trend_score = max(0, min(100, total_score))

        return {
            "trend_score": trend_score,
            "factors": factors,
            "trending_elements": self._identify_trending_elements(title_lower),
            "recommendations": self._generate_trend_recommendations(factors, title),
        }

    # ------------------------
    # Google Trends
    # ------------------------
    def fetch_trends(self, query: str, timeframe: Optional[str] = None, geo: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Busca série histórica no Google Trends e produz estatísticas simples. Retorna None se vazio."""
        timeframe = timeframe or self.trends_timeframe
        try:
            self._pytrends.build_payload([query], geo=(geo or self.trends_geo), timeframe=timeframe)
            df = self._pytrends.interest_over_time()
            if df is None or df.empty or query not in df.columns:
                return None

            series = df[query]
            current = int(series.iloc[-1])
            peak = int(series.max())
            last_30 = float(series.tail(30).mean()) if len(series) >= 30 else float(series.mean())
            prev_30 = float(series.tail(60).head(30).mean()) if len(series) >= 60 else last_30
            momentum = 0.0 if prev_30 == 0 else round(((last_30 - prev_30) / prev_30) * 100, 1)

            # score de tendência 0–100: nível atual vs pico (50%) + média 30d normalizada (50%)
            level_ratio = 0.0 if peak == 0 else (current / peak)
            score = int(round(100 * (0.5 * level_ratio + 0.5 * (last_30 / 100.0))))

            return {
                "trend_current": current,
                "trend_peak": peak,
                "trend_30d_avg": int(round(last_30)),
                "trend_momentum_pct": momentum,
                "trend_score": score,
                "points": int(series.shape[0]),
                "timeframe": timeframe,
                "geo": geo or self.trends_geo,
            }
        except Exception as e:
            logger.warning(f"[trends] erro consultando Google Trends para '{query}': {e}")
            return None

    def enrich_title_with_trends(self, title: str, topic: str, geo: Optional[str] = None, timeframe: Optional[str] = None) -> Dict[str, Any]:
        """Combina heurísticas locais (engagement/SEO/trend) + Google Trends. Retorna dict pronto para ContentMetadata."""
        local = self.analyze_title_all(title, topic)
        trends = self.fetch_trends(topic, timeframe=timeframe, geo=geo)

        out = dict(local)
        if trends:
            out["trend_stats"] = trends
            if not out.get("trend_relevance"):
                out["trend_relevance"] = trends["trend_score"]
            else:
                # média ponderada: 60% heurística local, 40% trends
                try:
                    out["trend_relevance"] = int(round(0.6 * float(out["trend_relevance"]) + 0.4 * float(trends["trend_score"])) )
                except Exception:
                    out["trend_relevance"] = int(trends["trend_score"])
        return out

    # ------------------------
    # Consolidador (normalização)
    # ------------------------
    def analyze_title_all(self, title: str, topic: str) -> Dict[str, Any]:
        """Consolida engagement/SEO/trend e normaliza chaves para o app."""
        e = self.analyze_title_engagement(title, topic)
        s = self.analyze_seo_potential(title, topic)
        t = self.analyze_trend_relevance(title, topic)
        return {
            # chaves esperadas pelo restante da aplicação
            "engagement_potential": e.get("engagement_score", 0),
            "seo_score": s.get("seo_score", 0),
            "trend_relevance": t.get("trend_score", 0),
            # breakdowns
            "engagement_factors": e.get("factors", {}),
            "seo_factors": s.get("factors", {}),
            "trend_factors": t.get("factors", {}),
            # extras
            "estimated_monthly_searches": s.get("estimated_monthly_searches"),
            "trending_elements": t.get("trending_elements", []),
            "recommendations": {
                "engagement": e.get("recommendations", []),
                "seo": s.get("recommendations", []),
                "trend": t.get("recommendations", []),
            },
        }

    # ------------------------
    # Helpers internos
    # ------------------------
    def _estimate_search_volume(self, title: str, topic: str) -> str:
        """Estimativa heurística de volume de busca (faixas)."""
        topic_complexity = len(topic.split())
        title_complexity = len(title.split())
        tl = title.lower()

        if topic_complexity > 4 or title_complexity > 10:
            return "100-1K/mês (nicho)"
        elif any(x in tl for x in ["best", "top", "how to"]):
            return "1K-10K/mês (popular)"
        else:
            return "500-5K/mês (médio)"

    def _get_seasonal_relevance(self, title_lower: str, month: int) -> int:
        """Relevância sazonal simples por mês."""
        seasonal_keywords: Dict[int, List[str]] = {
            1: ["new", "resolution", "start", "beginning", str(datetime.now().year)],
            9: ["learning", "course", "education", "back to school"],
            12: ["review", "best of", "year", "planning", str(datetime.now().year)],
        }
        words = seasonal_keywords.get(month, [])
        matches = sum(1 for w in words if w in title_lower)
        return min(15, matches * 5)

    def _identify_trending_elements(self, title_lower: str) -> List[str]:
        """Identifica elementos em alta a partir do título (lowercase)."""
        trending: List[str] = []
        if any(w in title_lower for w in ["ai", "ia", "chatgpt", "gpt"]):
            trending.append("IA/AI Content")
        if any(w in title_lower for w in ["automation", "productivity"]):
            trending.append("Automação/Produtividade")
        if any(w in title_lower for w in ["react", "next.js", "typescript"]):
            trending.append("Tecnologias Web Modernas")
        if "remote" in title_lower or "work from home" in title_lower:
            trending.append("Trabalho Remoto")
        return trending

    def _generate_engagement_recommendations(self, factors: Dict[str, int], title: str) -> List[str]:
        """Recomendações para aumentar engajamento do título."""
        recs: List[str] = []
        if factors.get("numbers", 0) == 0:
            recs.append("Adicione números específicos (ex.: '5 Dicas', '10 Erros')")
        if factors.get("question", 0) == 0 and not title.strip().endswith("?"):
            recs.append("Considere formato de pergunta para gerar curiosidade")
        if factors.get("power_words", 0) < 10:
            recs.append("Use palavras de impacto: 'Ultimate', 'Complete', 'Secrets'")
        if factors.get("optimal_length", 0) < 15:
            recs.append("Ajuste o comprimento para 50–70 caracteres")
        return recs

    def _generate_seo_recommendations(self, factors: Dict[str, int], title: str) -> List[str]:
        """Recomendações para melhorar SEO do título."""
        recs: List[str] = []
        if factors.get("keyword_presence", 0) < 15:
            recs.append("Inclua mais palavras-chave do tópico principal")
        if factors.get("seo_length", 0) < 20:
            recs.append("Mantenha entre 40–60 caracteres para melhor SEO")
        if factors.get("long_tail", 0) < 15:
            recs.append("Use frases mais específicas (long-tail keywords)")
        if factors.get("stop_words", 0) < 10:
            recs.append("Reduza palavras irrelevantes (the, a, very etc.)")
        return recs

    def _generate_trend_recommendations(self, factors: Dict[str, int], title: str) -> List[str]:
        """Recomendações para aumentar relevância de tendência."""
        recs: List[str] = []
        if factors.get("current_year", 0) == 0:
            recs.append("Adicione referência ao ano atual")
        if factors.get("tech_relevance", 0) < 15:
            recs.append("Inclua tecnologias em alta (AI, React, Python etc.)")
        if factors.get("format_trend", 0) < 10:
            recs.append("Use formatos populares: 'Tutorial', 'Complete Guide', 'Review'")
        return recs
