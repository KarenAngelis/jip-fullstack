# app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import uuid
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import openai
import re
import json
from typing import List, Dict, Any
from datetime import datetime
import app.models.pauta  # registra Pauta na Base


# Settings
from app.core.settings import settings
from app.routers.settings_router import router as settings_router



# DB / models (mantenha só o necessário p/ auth)
from app.database.database import engine, database, get_db
from sqlalchemy.orm import Session
from app.models import user_model
from app.models.user_model import User
from app.database.database import Base


# Auth dependency (para pegar o usuário logado)
from app.dependencies.auth import get_current_active_user

# Service de persistência unificado para Compliance
from app.services.compliance_service import save_compliance_analysis

# Routers ATIVOS
from app.routers.auth_router import router as auth_router
from app.routers.news_router import router as news_router
from app.routers.pautas_simple import router as pautas_router
from app.routers.script_router import router as script_router
from app.routers.episodes import router as episodes_router
from app.routers.trends import router as trends_router
from app.routers.title_generation_router import router as title_generation_router
from app.routers.youtube_trends import router as youtube_router
from app.routers.news_insights import router as news_insights_router
from app.routers.episode_suggestions import router as episode_suggestions_router  # NOVO
from app.routers.compliance import router as compliance_router

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- Criação das tabelas necessárias ----
Base.metadata.create_all(bind=engine)

# =================== SISTEMA DE CONFORMIDADE LEGAL ===================

class RealLegalScraper:
    """Scraper REAL para sites jurídicos brasileiros"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        }
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def search_all_sources(self, query: str, context_area: str = "geral") -> List[Dict[str, Any]]:
        """Busca em todas as fontes jurídicas relevantes"""
        print(f"🔍 Iniciando busca jurídica para: '{query}' (contexto: {context_area})")

        all_results = []
        search_tasks = [
            self.search_constitution_planalto(query),
            self.search_cdc_planalto(query),
        ]

        if 'trabalhista' in context_area.lower():
            search_tasks.append(self.search_clt_planalto(query))
        if 'lgpd' in context_area.lower() or 'dados' in context_area.lower():
            search_tasks.append(self.search_lgpd_planalto(query))

        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                print(f"❌ Erro em uma das buscas: {result}")

        # Remover duplicatas
        unique_results = []
        seen_content = set()
        for result in all_results:
            content_key = result['content'][:100]
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_results.append(result)

        sorted_results = sorted(unique_results, key=lambda x: x.get('relevance_score', 0), reverse=True)
        print(f"✅ Busca concluída: {len(sorted_results)} resultados únicos")
        return sorted_results[:8]

    async def search_constitution_planalto(self, query: str) -> List[Dict[str, Any]]:
        url = "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm"
        try:
            async with aiohttp.ClientSession(headers=self.headers, timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return []
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    results = []
                    paragraphs = soup.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if len(text) < 30:
                            continue
                        relevance = self._calculate_relevance(text, query)
                        if relevance > 0.1:
                            article_info = self._extract_article_info(text)
                            results.append({
                                "source": "Constituição Federal",
                                "source_type": "legislation",
                                "authority_level": 10,
                                "article": article_info,
                                "content": text[:600] + "..." if len(text) > 600 else text,
                                "url": url,
                                "relevance_score": relevance,
                                "search_query": query
                            })
                    print(f"📋 Constituição: {len(results)} artigos encontrados")
                    return sorted(results, key=lambda x: x['relevance_score'], reverse=True)[:3]
        except Exception as e:
            print(f"❌ Erro ao buscar Constituição: {e}")
            return []

    async def search_cdc_planalto(self, query: str) -> List[Dict[str, Any]]:
        url = "https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm"
        try:
            async with aiohttp.ClientSession(headers=self.headers, timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return []
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    results = []
                    paragraphs = soup.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if len(text) < 30:
                            continue
                        relevance = self._calculate_relevance(text, query)
                        if relevance > 0.1:
                            article_info = self._extract_article_info(text)
                            results.append({
                                "source": "Código de Defesa do Consumidor (Lei 8.078/90)",
                                "source_type": "legislation",
                                "authority_level": 10,
                                "article": article_info,
                                "content": text[:600] + "..." if len(text) > 600 else text,
                                "url": url,
                                "relevance_score": relevance,
                                "search_query": query
                            })
                    print(f"🛡️ CDC: {len(results)} artigos encontrados")
                    return sorted(results, key=lambda x: x['relevance_score'], reverse=True)[:3]
        except Exception as e:
            print(f"❌ Erro ao buscar CDC: {e}")
            return []

    async def search_clt_planalto(self, query: str) -> List[Dict[str, Any]]:
        url = "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm"
        try:
            async with aiohttp.ClientSession(headers=self.headers, timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return []
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    results = []
                    paragraphs = soup.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if len(text) < 30:
                            continue
                        relevance = self._calculate_relevance(text, query)
                        if relevance > 0.1:
                            article_info = self._extract_article_info(text)
                            results.append({
                                "source": "CLT - Consolidação das Leis do Trabalho",
                                "source_type": "legislation",
                                "authority_level": 10,
                                "article": article_info,
                                "content": text[:600] + "..." if len(text) > 600 else text,
                                "url": url,
                                "relevance_score": relevance,
                                "search_query": query
                            })
                    print(f"👷 CLT: {len(results)} artigos encontrados")
                    return sorted(results, key=lambda x: x['relevance_score'], reverse=True)[:2]
        except Exception as e:
            print(f"❌ Erro ao buscar CLT: {e}")
            return []

    async def search_lgpd_planalto(self, query: str) -> List[Dict[str, Any]]:
        url = "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm"
        try:
            async with aiohttp.ClientSession(headers=self.headers, timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return []
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    results = []
                    paragraphs = soup.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if len(text) < 30:
                            continue
                        relevance = self._calculate_relevance(text, query)
                        if relevance > 0.1:
                            article_info = self._extract_article_info(text)
                            results.append({
                                "source": "LGPD - Lei Geral de Proteção de Dados (Lei 13.709/18)",
                                "source_type": "legislation",
                                "authority_level": 10,
                                "article": article_info,
                                "content": text[:600] + "..." if len(text) > 600 else text,
                                "url": url,
                                "relevance_score": relevance,
                                "search_query": query
                            })
                    print(f"🔒 LGPD: {len(results)} artigos encontrados")
                    return sorted(results, key=lambda x: x['relevance_score'], reverse=True)[:2]
        except Exception as e:
            print(f"❌ Erro ao buscar LGPD: {e}")
            return []

    def _extract_article_info(self, text: str) -> str:
        patterns = [
            r'Art\.?\s*(\d+)([º°]?)',
            r'Artigo\s*(\d+)',
            r'§\s*(\d+)[º°]?',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"Art. {match.group(1)}"
        return "Dispositivo legal"

    def _calculate_relevance(self, text: str, query: str) -> float:
        text_lower = text.lower()
        query_words = [word.lower().strip() for word in query.split() if len(word.strip()) > 2]
        if not query_words:
            return 0.0
        word_matches = sum(1 for word in query_words if word in text_lower)
        word_score = word_matches / len(query_words) if query_words else 0
        legal_boost = 0
        legal_terms = ['direito', 'lei', 'código', 'artigo', 'constituição', 'dever', 'obrigação', 'responsabilidade', 'consumidor']
        for term in legal_terms:
            if term in text_lower:
                legal_boost += 0.05
        return min(word_score + legal_boost, 1.0)


class RealLegalComplianceAnalyzer:
    """Analisador de conformidade legal com busca REAL"""

    def __init__(self, openai_api_key: str):
        self.client = openai.OpenAI(api_key=openai_api_key)
        self.scraper = RealLegalScraper()

    async def analyze_compliance(self, content_to_analyze: str, context_area: str = "geral") -> Dict[str, Any]:
        try:
            start_time = datetime.now()
            print(f"🔍 Iniciando busca REAL para: {content_to_analyze[:50]}...")
            legal_sources = await self.scraper.search_all_sources(content_to_analyze, context_area)
            search_time = (datetime.now() - start_time).total_seconds()
            print(f"🤖 Analisando com OpenAI usando {len(legal_sources)} fontes REAIS...")
            ai_analysis = await self._analyze_with_ai(content_to_analyze, legal_sources, context_area)
            total_time = (datetime.now() - start_time).total_seconds()
            return {
                "status": "success",
                "analysis_type": "REAL_LEGAL_SEARCH",
                "content_analyzed": content_to_analyze[:200] + "..." if len(content_to_analyze) > 200 else content_to_analyze,
                "context_area": context_area,
                "legal_sources_found": len(legal_sources),
                "legal_sources": legal_sources[:5],
                "ai_analysis": ai_analysis,
                "performance": {
                    "search_time_seconds": search_time,
                    "total_time_seconds": total_time,
                },
                "timestamp": datetime.now().isoformat(),
                "confidence_score": ai_analysis.get('confidence_score', 0.7)
            }
        except Exception as e:
            print(f"❌ Erro na análise: {e}")
            return {
                "status": "error",
                "error": str(e),
                "content_analyzed": content_to_analyze[:100] + "...",
                "context_area": context_area,
                "timestamp": datetime.now().isoformat()
            }

    async def _analyze_with_ai(self, content: str, legal_sources: List[Dict[str, Any]], context_area: str) -> Dict[str, Any]:
        legal_context = "\n".join([
            f"**{source['source']}** ({source.get('article', 'N/A')}):\n{source['content']}\n"
            for source in legal_sources[:4]
        ])
        prompt = f"""
Você é um advogado especialista em direito brasileiro. Analise a conformidade legal do conteúdo usando as fontes jurídicas REAIS consultadas.

**CONTEXTO:** {context_area}

**CONTEÚDO:**
{content}

**FONTES JURÍDICAS REAIS CONSULTADAS:**
{legal_context}

**RESPONDA EM JSON VÁLIDO:**
{{
    "conformidade_status": "compliant|non_compliant|partially_compliant|unclear",
    "confidence_score": 0.85,
    "violations": ["violação específica com Art. X"],
    "legal_articles_cited": ["Art. 5º da CF/88", "Art. 6º do CDC"],
    "recommendations": ["recomendação específica 1", "recomendação 2"],
    "risk_level": "low|medium|high|critical",
    "summary": "Resumo em 2-3 frases",
    "detailed_analysis": "Análise detalhada citando os dispositivos consultados"
}}
        """
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é um advogado especialista em direito brasileiro. SEMPRE responda em JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            ai_response_text = response.choices[0].message.content.strip()
            if ai_response_text.startswith('```json'):
                ai_response_text = ai_response_text.replace('```json', '').replace('```', '').strip()
            elif ai_response_text.startswith('```'):
                ai_response_text = ai_response_text.replace('```', '').strip()
            ai_response = json.loads(ai_response_text)
            return ai_response
        except json.JSONDecodeError as e:
            return {
                "conformidade_status": "unclear",
                "confidence_score": 0.0,
                "violations": [f"Erro parsing: {str(e)}"],
                "recommendations": ["Consulte um advogado para análise manual"],
                "risk_level": "medium",
                "summary": "Erro no processamento da análise",
                "detailed_analysis": f"Erro JSON: {str(e)}"
            }
        except Exception as e:
            return {
                "conformidade_status": "unclear",
                "confidence_score": 0.0,
                "violations": [f"Erro técnico: {str(e)}"],
                "recommendations": ["Tente novamente ou consulte um advogado"],
                "risk_level": "medium",
                "summary": "Erro técnico na análise",
                "detailed_analysis": f"Erro: {str(e)}"
            }

# =================== FASTAPI APP ===================

app = FastAPI(
    title="JIP API",
    description="API do JIP — módulos estáveis incluindo Google Trends, YouTube, News, Episode Suggestions & Compliance Legal",
    version="4.4.0",
)

# ---- CORS (corrigido) ----
VERCEL_FRONTEND_URL = os.getenv("VERCEL_FRONTEND_URL", "https://jipcontent.com")
ALLOWED_ORIGINS = [
    VERCEL_FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "https://jip-api-1.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization", "Content-Type"],
    expose_headers=["*"],
)

# ---- Routers ATIVOS ----
app.include_router(auth_router, prefix="/api/auth", tags=["Autenticação"])
app.include_router(news_router, prefix="/api/news", tags=["Notícias"])
app.include_router(pautas_router, tags=["Pautas"])
app.include_router(script_router, prefix="/api/scripts", tags=["Scripts"])
app.include_router(episodes_router, prefix="/api", tags=["Episódios"])
app.include_router(trends_router, prefix="/api", tags=["Google Trends"])
app.include_router(title_generation_router, prefix="/api/titles", tags=["Títulos"])
app.include_router(youtube_router, prefix="/api", tags=["YouTube Trends"])
app.include_router(news_insights_router, prefix="/api", tags=["News & Insights"])
app.include_router(episode_suggestions_router, prefix="/api", tags=["Episode Suggestions"])
app.include_router(compliance_router)
app.include_router(settings_router)


# =================== COMPLIANCE ENDPOINTS ===================

@app.post("/api/compliance/analyze-real", tags=["Legal Compliance"])
async def real_compliance_analysis(
    request_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    🏛️ Análise REAL de Conformidade Legal — salva vinculada ao usuário autenticado.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return {
            "error": "OpenAI API Key não configurada",
            "setup": "Configure OPENAI_API_KEY nas variáveis de ambiente",
            "status": "configuration_error",
        }

    content = request_data.get("content", "")
    context = request_data.get("context", "geral")

    if not content.strip():
        return {"error": "Conteúdo não pode estar vazio", "status": "invalid_input"}

    print(f"🚀 Iniciando análise REAL para: {content[:50]}...")

    try:
        analyzer = RealLegalComplianceAnalyzer(openai_key)
        result = await analyzer.analyze_compliance(content, context)

        # --- SAVE-LOG (unificado) com usuário logado ---
        try:
            save_compliance_analysis(
                db=db,
                user_id=current_user.id,
                request_id=uuid.uuid4(),
                request_payload={
                    "content": content,
                    "context_area": context,
                    "specific_laws": None,
                    "company_info": None,
                },
                analysis_payload={
                    "status": (result.get("ai_analysis", {}) or {}).get("conformidade_status", "needs_review"),
                    "confidence_score": result.get("confidence_score"),
                    "risk_level": (result.get("ai_analysis", {}) or {}).get("risk_level"),
                    "summary": (result.get("ai_analysis", {}) or {}).get("summary"),
                    "violations": (result.get("ai_analysis", {}) or {}).get("violations", []),
                    "recommendations": (result.get("ai_analysis", {}) or {}).get("recommendations", []),
                    "detailed_analysis": (result.get("ai_analysis", {}) or {}).get("detailed_analysis"),
                    "legal_sources": result.get("legal_sources", []),
                },
            )
        except Exception as e:
            logger.exception("Erro ao salvar log de compliance: %s", e)

        return result

    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return {
            "status": "error",
            "error": f"Erro na análise: {str(e)}",
            "content": content[:50] + "...",
            "context": context,
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/compliance/test-sources")
async def test_legal_sources():
    """🔧 Testa conectividade com fontes jurídicas"""
    scraper = RealLegalScraper()
    test_query = "direito consumidor"

    tests = [
        ("Constituição Federal", scraper.search_constitution_planalto(test_query)),
        ("CDC", scraper.search_cdc_planalto(test_query)),
    ]

    results = {}
    for source_name, test_coro in tests:
        try:
            print(f"🔍 Testando {source_name}...")
            result = await test_coro
            results[source_name] = {
                "status": "✅ OK",
                "results_found": len(result),
                "sample": result[0]['content'][:100] + "..." if result else "Nenhum resultado"
            }
        except Exception as e:
            results[source_name] = {
                "status": "❌ ERRO",
                "error": str(e),
                "results_found": 0
            }

    return {
        "message": "🧪 Teste de Conectividade das Fontes Jurídicas",
        "timestamp": datetime.now().isoformat(),
        "test_query": test_query,
        "results": results,
        "overall_status": "✅ Sistema funcionando" if any("OK" in r["status"] for r in results.values()) else "❌ Problemas detectados"
    }

@app.get("/api/compliance/examples")
async def compliance_examples():
    """📋 Exemplos do sistema de conformidade legal"""
    return {
        "message": "🏛️ Sistema REAL de Conformidade Legal",
        "endpoint": "POST /api/compliance/analyze-real",
        "examples": {
            "e-commerce_problematico": {
                "content": "Nossos produtos são vendidos sem garantia. Não nos responsabilizamos por defeitos. O cliente usa por conta e risco.",
                "context": "e-commerce",
                "expected_sources": ["Constituição Federal", "CDC"]
            },
            "lgpd_violacao": {
                "content": "Coletamos todos os dados dos usuários e podemos compartilhá-los livremente para qualquer finalidade comercial.",
                "context": "lgpd",
                "expected_sources": ["LGPD", "Constituição Federal"]
            },
            "trabalhista_abusivo": {
                "content": "O funcionário deve trabalhar 10 horas diárias, incluindo sábados, sem direito a horas extras.",
                "context": "trabalhista",
                "expected_sources": ["CLT", "Constituição Federal"]
            }
        },
        "supported_contexts": ["geral", "e-commerce", "lgpd", "trabalhista"],
        "features": [
            "✅ Busca REAL nos sites oficiais do governo",
            "✅ Análise com OpenAI baseada em dados reais",
            "✅ Identificação de violações específicas",
            "✅ Recomendações práticas para adequação"
        ]
    }

# ---- Health / raiz ----
@app.get("/")
def read_root():
    return {
        "message": "JIP API v4.4 - Plataforma Completa de Análise de Conteúdo! 🚀🎬📰🏛️💡",
        "docs": "/docs",
        "status": "/api/status",
        "trends_dashboard": "/api/trends/dashboard",
        "youtube_trending": "/api/youtube/trending",
        "news_dashboard": "/api/news-insights/dashboard",
        "episode_suggestions": "/api/episode-suggestions/generate",
        "episode_templates": "/api/episode-suggestions/templates",
        "compliance_analyze": "/api/compliance/analyze-real",
        "compliance_test": "/api/compliance/test-sources",
        "compliance_examples": "/api/compliance/examples"
    }

@app.get("/healthz")
def health():
    return {"status": "healthy", "version": "4.4.0"}

@app.get("/api/status")
def api_status():
    return {
        "api_version": "4.4.0",
        "status": "healthy",
        "last_update": "2025-01-20",
        "modules": {
            "auth": "active ✅",
            "news": "active ✅",
            "pautas": "active ✅",
            "scripts": "active ✅",
            "episodes": "active ✅",
            "trends": "active ✅ (IMPROVED)",
            "titles": "active ✅",
            "youtube": "active ✅",
            "news_insights": "active ✅",
            "episode_suggestions": "active ✅ (NEW)",
            "legal_compliance": "active ✅",
            "pautas_pdf": "disabled 🚧",
            "opportunities": "disabled 🚧",
            "reddit": "disabled 🚧",
            "threads": "disabled 🚧",
            "podcast": "disabled 🚧",
        },
        "new_features": {
            "episode_suggestions": {
                "generate": "/api/episode-suggestions/generate",
                "episode_details": "/api/episode-suggestions/episode/{id}",
                "reanalyze": "/api/episode-suggestions/episode/{id}/reanalyze",
                "templates": "/api/episode-suggestions/templates",
                "analytics": "/api/episode-suggestions/analytics/summary",
                "description": "Sistema integrado que gera 12 sugestões de episódios com análise completa"
            },
            "google_trends": {
                "dashboard": "/api/trends/dashboard",
                "daily_trends": "/api/trends/daily",
                "analysis": "/api/trends/analyze",
                "opportunities": "/api/trends/opportunities",
                "seasonal_calendar": "/api/trends/seasonal-calendar",
                "quick_insights": "/api/trends/quick-insights/{keyword}",
                "competitor_analysis": "/api/trends/competitor-analysis/{keyword}",
                "description": "Análise avançada com dados brasileiros realistas"
            },
            "youtube_trends": {
                "trending": "/api/youtube/trending",
                "search_trending": "/api/youtube/search-trending",
                "categories": "/api/youtube/categories",
                "search": "/api/youtube/search",
                "analyze": "/api/youtube/analyze",
                "health": "/api/youtube/health",
                "description": "Análise completa do YouTube com dados reais da API oficial + busca por tema"
            },
            "news_insights": {
                "dashboard": "/api/news-insights/dashboard",
                "search": "/api/news-insights/search",
                "trending": "/api/news-insights/trending",
                "analyze": "/api/news-insights/analyze",
                "sources": "/api/news-insights/sources",
                "sentiment": "/api/news-insights/sentiment-analysis?topic=..."
            },
            "legal_compliance": {
                "analyze": "/api/compliance/analyze-real",
                "test_sources": "/api/compliance/test-sources",
                "examples": "/api/compliance/examples",
                "description": "Análise REAL de conformidade legal com busca em fontes oficiais"
            }
        },
        "integrated_systems": [
            "Google Trends + YouTube + News + Legal = Episode Suggestions",
            "Análise preditiva baseada em múltiplas fontes",
            "Conformidade legal automática em tempo real",
            "Dashboard consolidado de métricas",
            "Cache inteligente para performance otimizada"
        ]
    }

@app.get("/api/episode-suggestions-demo")
def episode_suggestions_demo():
    return {
        "message": "💡 Sistema de Episode Suggestions - Análise Integrada!",
        "description": "Gera 12 sugestões de episódios com análise completa usando todas as suas APIs",
        "workflow": {
            "input": "Título + Contexto opcional",
            "processing": [
                "1️⃣ Extrai palavras-chave do título",
                "2️⃣ Analisa tendências no Google Trends",
                "3️⃣ Busca dados similares no YouTube",
                "4️⃣ Verifica conformidade legal",
                "5️⃣ Gera descrições com IA",
                "6️⃣ Sugere convidados especialistas",
                "7️⃣ Calcula probabilidade de sucesso"
            ],
            "output": "12 episódios completos com análise preditiva"
        },
        "try_these": {
            "generate_suggestions": {
                "url": "POST /api/episode-suggestions/generate",
                "description": "Gera 12 sugestões completas de episódios",
                "example_request": {
                    "title": "Como Criar uma Startup de Sucesso",
                    "context": "Baseado na minha experiência de 3 startups, sendo 2 falharam e 1 teve exit",
                    "target_audience": "empreendedores",
                    "episode_format": "entrevista"
                }
            },
            "get_templates": {
                "url": "GET /api/episode-suggestions/templates",
                "description": "Templates e exemplos para títulos de episódios"
            },
            "episode_details": {
                "url": "GET /api/episode-suggestions/episode/{episode_id}",
                "description": "Detalhes completos de um episódio específico"
            },
            "analytics": {
                "url": "GET /api/episode-suggestions/analytics/summary",
                "description": "Estatísticas sobre as sugestões geradas"
            }
        },
        "features": [
            "✅ Integração com Google Trends para análise preditiva",
            "✅ Dados do YouTube para métricas de vídeo",
            "✅ Análise jurídica automática para compliance",
            "✅ Geração de descrições com IA",
            "✅ Sugestões inteligentes de convidados",
            "✅ Score de probabilidade de sucesso (0-100%)",
            "✅ Base de dados com especialistas por área",
            "✅ Cache otimizado para performance",
            "✅ Re-análise com keywords adicionais",
            "✅ Templates prontos para usar"
        ],
        "data_sources": {
            "trends": "Google Trends API + dados brasileiros",
            "youtube": "YouTube Data API v3 oficial",
            "legal": "Busca real em sites governamentais",
            "guests": "Base com 6 categorias de especialistas",
            "ai": "OpenAI GPT para geração de conteúdo"
        },
        "output_fields": {
            "1_titulo": "Título otimizado do episódio",
            "2_descricao": "Roteiro reduzido gerado por IA",
            "3_keywords": "Palavras-chave para SEO",
            "4_convidados": "Especialistas sugeridos com justificativa",
            "5_percentual_acerto": "Análise preditiva baseada em trends",
            "6_analise_juridica": "Status OK/Warning/Error com recomendações"
        },
        "api_requirements": {
            "required": "OPENAI_API_KEY (para análise legal e geração)",
            "optional": "YOUTUBE_API_KEY (melhores dados de vídeo)",
            "fallback": "Funciona com dados mock quando APIs não disponíveis"
        }
    }

@app.get("/api/features")
def get_features():
    return {
        "authentication": {
            "description": "Sistema JWT completo",
            "endpoints": {
                "register": "POST /api/auth/register",
                "login": "POST /api/auth/login",
                "profile": "GET /api/auth/me"
            }
        },
        "content_creation": {
            "description": "Geração de pautas, scripts e episódios",
            "endpoints": {
                "pautas": "POST /pautas/generate",
                "scripts": "POST /api/scripts/generate",
                "episodes": "POST /api/episodes/generate"
            }
        },
        "episode_suggestions": {
            "description": "💡 Sistema integrado de sugestões de episódios",
            "capabilities": [
                "Gera 12 sugestões por request",
                "Análise preditiva de sucesso baseada em trends",
                "Conformidade legal automática",
                "Sugestões de convidados especialistas",
                "Extração inteligente de keywords",
                "Roteiros reduzidos gerados por IA",
                "Re-análise com parâmetros adicionais"
            ],
            "integration": [
                "Google Trends - análise de tendências e sazonalidade",
                "YouTube - métricas de vídeos similares",
                "Legal Compliance - verificação automática",
                "OpenAI - geração de descrições otimizadas",
                "Base de Especialistas - 6 categorias profissionais"
            ],
            "endpoints": {
                "generate": "POST /api/episode-suggestions/generate",
                "details": "GET /api/episode-suggestions/episode/{id}",
                "reanalyze": "POST /api/episode-suggestions/episode/{id}/reanalyze",
                "templates": "GET /api/episode-suggestions/templates",
                "analytics": "GET /api/episode-suggestions/analytics/summary",
                "health": "GET /api/episode-suggestions/health"
            }
        },
        "google_trends": {
            "description": "Análise avançada do Google Trends com foco no Brasil",
            "capabilities": [
                "Dashboard consolidado com métricas principais",
                "Tendências diárias com dados realistas",
                "Análise completa de palavras-chave",
                "Oportunidades de conteúdo inteligentes",
                "Calendário sazonal brasileiro completo",
                "Insights rápidos para qualquer palavra-chave",
                "Análise de concorrentes e posicionamento"
            ],
            "brazilian_features": [
                "Padrões sazonais brasileiros (ENEM, Black Friday, Carnaval)",
                "Dados geográficos de todos os estados",
                "Volumes de busca baseados em dados reais",
                "Análise de competição específica do mercado BR",
                "Timing otimizado para o calendário brasileiro"
            ],
            "endpoints": {
                "dashboard": "GET /api/trends/dashboard",
                "daily": "GET /api/trends/daily?limit=20&geo=BR",
                "analyze": "POST /api/trends/analyze",
                "opportunities": "GET /api/trends/opportunities?keywords=...",
                "calendar": "GET /api/trends/seasonal-calendar",
                "insights": "GET /api/trends/quick-insights/{keyword}",
                "competitors": "GET /api/trends/competitor-analysis/{keyword}"
            }
        },
        "youtube_trends": {
            "description": "Análise completa do YouTube com dados reais da API oficial",
            "capabilities": [
                "Vídeos trending reais por região",
                "Busca avançada por palavra-chave",
                "Busca por tema personalizado",
                "Métricas completas (views, likes, comentários)",
                "Análise de categorias populares",
                "Score de trending baseado em engajamento",
                "Cache inteligente para performance otimizada",
                "Análise comparativa de múltiplas palavras-chave"
            ],
            "endpoints": {
                "trending": "GET /api/youtube/trending?region_code=BR&max_results=25",
                "search_by_theme": "GET /api/youtube/search-trending?theme=casamento 2025",
                "categories": "GET /api/youtube/categories?region_code=BR",
                "search": "GET /api/youtube/search?keyword=...",
                "analyze": "POST /api/youtube/analyze?keywords=...",
                "health": "GET /api/youtube/health"
            }
        },
        "news_insights": {
            "description": "Análise avançada de notícias com insights automáticos",
            "capabilities": [
                "Análise de notícias em tempo real",
                "Sentimento automático em português",
                "Extração inteligente de palavras-chave",
                "Categorização automática de artigos",
                "Dashboard consolidado com métricas",
                "Trending topics baseados em notícias",
                "Insights automáticos sobre padrões",
                "Análise temporal de sentimento"
            ],
            "endpoints": {
                "dashboard": "GET /api/news-insights/dashboard",
                "search": "GET /api/news-insights/search?query=...",
                "trending": "GET /api/news-insights/trending?limit=10",
                "analyze": "POST /api/news-insights/analyze",
                "sources": "GET /api/news-insights/sources",
                "sentiment": "GET /api/news-insights/sentiment-analysis?topic=..."
            }
        },
        "legal_compliance": {
            "description": "Análise REAL de conformidade legal",
            "capabilities": [
                "Busca real em fontes oficiais do governo",
                "Análise com IA baseada em dados reais",
                "Identificação de violações específicas",
                "Recomendações práticas para adequação",
                "Suporte a múltiplas áreas do direito"
            ],
            "sources": [
                "Constituição Federal (Planalto)",
                "CDC - Código de Defesa do Consumidor",
                "CLT - Consolidação das Leis do Trabalho",
                "LGPD - Lei Geral de Proteção de Dados"
            ],
            "endpoints": {
                "analyze": "POST /api/compliance/analyze-real",
                "test_sources": "GET /api/compliance/test-sources",
                "examples": "GET /api/compliance/examples"
            }
        },
        "title_optimization": {
            "description": "Geração e análise de títulos",
            "endpoints": {
                "generate": "POST /api/titles/generate",
                "analyze": "POST /api/titles/analyze",
                "power_words": "GET /api/titles/power-words",
                "templates": "GET /api/titles/templates"
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
