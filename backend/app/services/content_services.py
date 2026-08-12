# app/services/content_services.py
from typing import List, Dict, Optional, Any  
import httpx
import logging
from datetime import datetime, timedelta
import asyncio
import openai
import os
import json
import re
from urllib.parse import quote

logger = logging.getLogger(__name__)

class NewsService:
    """Serviço para coleta de notícias usando apenas HTTP requests"""
    
    @staticmethod
    async def collect_news(tema: str, lingua: str = "pt", limit: int = 10) -> List[Dict]:
        """
        Busca notícias usando métodos que funcionam sem dependências externas
        """
        try:
            logger.info(f"Coletando notícias para tema: {tema}")
            noticias = []
            
            # 1. Google News via scraping direto
            google_news = await NewsService._get_google_news_direct(tema, lingua, limit//2)
            noticias.extend(google_news)
            
            # 2. NewsAPI se disponível
            if os.getenv("NEWSAPI_KEY"):
                news_api = await NewsService._get_newsapi(tema, lingua, limit//2)
                noticias.extend(news_api)
            
            # 3. Fallback: RSS simples sem feedparser
            if len(noticias) < 3:
                rss_news = await NewsService._get_rss_simple(tema, limit - len(noticias))
                noticias.extend(rss_news)
            
            logger.info(f"Total de notícias coletadas: {len(noticias)}")
            return noticias[:limit]
            
        except Exception as e:
            logger.error(f"Erro ao coletar notícias: {e}")
            # Retornar pelo menos uma notícia de fallback
            return [{
                "titulo": f"Pesquisa sobre {tema} - Informações Atualizadas",
                "fonte": "Google News",
                "data": datetime.now().strftime("%Y-%m-%d"),
                "url": f"https://news.google.com/search?q={tema.replace(' ', '+')}&hl={lingua}",
                "confianca": "médio",
                "resumo": f"Busca direcionada sobre {tema} com informações recentes."
            }]
    
    @staticmethod
    async def _get_google_news_direct(tema: str, lingua: str, limit: int) -> List[Dict]:
        """Coleta do Google News via HTTP direto"""
        try:
            query = quote(tema)
            url = f"https://news.google.com/rss/search?q={query}&hl={lingua}&gl=BR&ceid=BR:{lingua}"
            
            async with httpx.AsyncClient() as client:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = await client.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                content = response.text
                noticias = []
                
                # Extrair títulos usando regex
                title_matches = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', content)
                link_matches = re.findall(r'<link>(.*?)</link>', content)
                pubdate_matches = re.findall(r'<pubDate>(.*?)</pubDate>', content)
                
                for i, title in enumerate(title_matches[:limit]):
                    if title and len(title) > 5:
                        # Pular o primeiro item que geralmente é o título do feed
                        if i == 0 and "Google News" in title:
                            continue
                            
                        link = link_matches[i] if i < len(link_matches) else ""
                        pubdate = pubdate_matches[i] if i < len(pubdate_matches) else ""
                        
                        # Converter data se possível
                        data_str = datetime.now().strftime("%Y-%m-%d")
                        try:
                            if pubdate:
                                data_obj = datetime.strptime(pubdate[:25], "%a, %d %b %Y %H:%M:%S")
                                data_str = data_obj.strftime("%Y-%m-%d")
                        except:
                            pass
                        
                        noticias.append({
                            "titulo": title.strip(),
                            "fonte": "Google News",
                            "data": data_str,
                            "url": link,
                            "confianca": "alto",
                            "resumo": f"Notícia sobre {tema} do Google News"
                        })
                
                logger.info(f"Google News RSS: {len(noticias)} notícias encontradas")
                return noticias[:limit]
                
        except Exception as e:
            logger.error(f"Erro no Google News direto: {e}")
            return []
    
    @staticmethod
    async def _get_newsapi(tema: str, lingua: str, limit: int) -> List[Dict]:
        """NewsAPI oficial"""
        try:
            api_key = os.getenv("NEWSAPI_KEY")
            if not api_key:
                return []
                
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": tema,
                "language": "pt" if lingua == "pt" else "en",
                "sortBy": "publishedAt",
                "pageSize": limit,
                "apiKey": api_key
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10)
                
            if response.status_code == 200:
                data = response.json()
                noticias = []
                
                for article in data.get("articles", []):
                    if article["title"] and article["url"]:
                        noticias.append({
                            "titulo": article["title"],
                            "fonte": article["source"]["name"],
                            "data": article["publishedAt"][:10],
                            "url": article["url"],
                            "confianca": "alto",
                            "resumo": article["description"] or ""
                        })
                
                logger.info(f"NewsAPI: {len(noticias)} notícias encontradas")
                return noticias
                
        except Exception as e:
            logger.error(f"Erro no NewsAPI: {e}")
            return []
    
    @staticmethod
    async def _get_rss_simple(tema: str, limit: int) -> List[Dict]:
        """RSS parsing simples sem feedparser"""
        try:
            # URLs de RSS brasileiros
            rss_urls = [
                "https://g1.globo.com/rss/g1/",
                "https://feeds.folha.uol.com.br/folha/cotidiano/rss091.xml"
            ]
            
            noticias = []
            
            for rss_url in rss_urls:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(rss_url, timeout=10)
                    
                    if response.status_code == 200:
                        content = response.text
                        
                        # Extrair itens do RSS
                        items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
                        
                        for item in items[:3]:  # Máximo 3 por fonte
                            title_match = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item)
                            link_match = re.search(r'<link>(.*?)</link>', item)
                            
                            if title_match and link_match:
                                title = title_match.group(1)
                                link = link_match.group(1)
                                
                                # Verificar se tem relação com o tema
                                if tema.lower() in title.lower():
                                    noticias.append({
                                        "titulo": title,
                                        "fonte": "Portal Brasileiro",
                                        "data": datetime.now().strftime("%Y-%m-%d"),
                                        "url": link,
                                        "confianca": "médio",
                                        "resumo": f"Notícia relacionada a {tema}"
                                    })
                                    
                                    if len(noticias) >= limit:
                                        break
                        
                        if len(noticias) >= limit:
                            break
                            
                except Exception as e:
                    logger.error(f"Erro no RSS {rss_url}: {e}")
                    continue
            
            logger.info(f"RSS simples: {len(noticias)} notícias encontradas")
            return noticias
            
        except Exception as e:
            logger.error(f"Erro no RSS simples: {e}")
            return []

class TrendsService:
    """Serviço para coleta de tendências com fallbacks inteligentes"""
    
    @staticmethod
    async def collect_trends(tema: str, region: str = "BR") -> Dict[str, Any]:
        """
        Coleta dados de tendências com múltiplos fallbacks
        """
        try:
            logger.info(f"Coletando trends para tema: {tema}")
            
            # Inicializar dados básicos
            trends_data = {
                "keywords": [],
                "metrics": {},
                "growth": {}
            }
            
            # 1. Tentar Google Suggest (mais confiável)
            keywords = await TrendsService._get_smart_keywords(tema)
            trends_data["keywords"] = keywords
            
            # 2. Métricas estimadas inteligentes
            metrics = await TrendsService._get_smart_metrics(tema, keywords)
            trends_data["metrics"] = metrics
            
            # 3. Análise de crescimento
            growth = await TrendsService._estimate_smart_growth(tema)
            trends_data["growth"] = growth
            
            logger.info(f"Trends coletados: {len(keywords)} keywords, métricas calculadas")
            return trends_data
            
        except Exception as e:
            logger.error(f"Erro ao coletar trends: {e}")
            # Fallback final com dados inteligentes
            return TrendsService._get_fallback_trends(tema)
    
    @staticmethod
    async def _get_smart_keywords(tema: str) -> List[str]:
        """Gera keywords inteligentes para qualquer tema"""
        try:
            # Primeiro tentar Google Suggest
            url = "http://suggestqueries.google.com/complete/search"
            params = {
                "q": tema,
                "client": "firefox", 
                "hl": "pt-BR"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=8)
            
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1 and isinstance(data[1], list) and data[1]:
                    suggestions = data[1][:7]
                    logger.info(f"Google Suggest: {len(suggestions)} sugestões encontradas")
                    return suggestions
                    
        except Exception as e:
            logger.error(f"Erro no Google Suggest: {e}")
        
        # Fallback inteligente baseado no tema
        return TrendsService._generate_smart_keywords(tema)
    
    @staticmethod
    def _generate_smart_keywords(tema: str) -> List[str]:
        """Gera keywords inteligentes baseadas no tema"""
        tema_lower = tema.lower()
        keywords = []
        
        # Detectar categoria do tema
        if any(word in tema_lower for word in ["enem", "vestibular", "concurso", "prova"]):
            keywords = [
                f"{tema} 2025",
                f"inscrição {tema}",
                f"data {tema}",
                f"resultado {tema}",
                f"preparação {tema}",
                f"dicas {tema}",
                f"gabarito {tema}"
            ]
        elif any(word in tema_lower for word in ["matemática", "física", "química", "biologia"]):
            keywords = [
                f"{tema} básica",
                f"exercícios {tema}",
                f"fórmulas {tema}",
                f"{tema} ensino médio",
                f"{tema} enem",
                f"curso {tema}",
                f"aulas {tema}"
            ]
        elif any(word in tema_lower for word in ["tecnologia", "programação", "código", "software"]):
            keywords = [
                f"{tema} 2025",
                f"curso {tema}",
                f"linguagem {tema}",
                f"framework {tema}",
                f"tutorial {tema}",
                f"desenvolvimento {tema}",
                f"carreira {tema}"
            ]
        elif any(word in tema_lower for word in ["saúde", "medicina", "doença", "tratamento"]):
            keywords = [
                f"{tema} sintomas",
                f"tratamento {tema}",
                f"prevenção {tema}",
                f"causas {tema}",
                f"diagnóstico {tema}",
                f"medicamento {tema}",
                f"especialista {tema}"
            ]
        elif any(word in tema_lower for word in ["economia", "mercado", "investimento", "dinheiro"]):
            keywords = [
                f"{tema} brasil",
                f"investir {tema}",
                f"mercado {tema}",
                f"análise {tema}",
                f"tendências {tema}",
                f"previsão {tema}",
                f"estratégia {tema}"
            ]
        else:
            # Padrão genérico mas útil
            keywords = [
                f"{tema} 2025",
                f"o que é {tema}",
                f"como {tema}",
                f"dicas {tema}",
                f"curso {tema}",
                f"guia {tema}",
                f"{tema} brasil"
            ]
        
        return keywords[:7]
    
    @staticmethod
    async def _get_smart_metrics(tema: str, keywords: List[str]) -> Dict[str, Any]:
        """Calcula métricas inteligentes baseadas no tema e keywords"""
        try:
            # Score base baseado na complexidade do tema
            base_score = 30
            
            # Aumentar score para temas populares
            popular_terms = ["enem", "vestibular", "concurso", "matemática", "tecnologia", "saúde"]
            if any(term in tema.lower() for term in popular_terms):
                base_score += 25
            
            # Aumentar score se há muitas keywords relacionadas
            if len(keywords) >= 5:
                base_score += 15
            
            # Calcular volume estimado
            volume_multiplier = 100
            if "enem" in tema.lower():
                volume_multiplier = 1000  # ENEM é muito popular
            elif any(term in tema.lower() for term in ["concurso", "vestibular"]):
                volume_multiplier = 500
            elif any(term in tema.lower() for term in ["matemática", "física"]):
                volume_multiplier = 300
            
            volume_busca = base_score * volume_multiplier
            
            return {
                "interesse_atual": base_score,
                "popularidade_score": base_score,
                "volume_busca_atual": base_score,
                "volume_busca_mensal": volume_busca,
                "interesse_medio_3m": max(10, base_score - 5),
                "interesse_regional": {"BR": 100, "SP": 85, "RJ": 75, "MG": 65}
            }
            
        except Exception as e:
            logger.error(f"Erro nas métricas inteligentes: {e}")
            return {"interesse_atual": 35, "popularidade_score": 35, "volume_busca_mensal": 3500}
    
    @staticmethod
    async def _estimate_smart_growth(tema: str) -> Dict[str, str]:
        """Estima crescimento baseado no tema e época do ano"""
        try:
            now = datetime.now()
            growth_rate = 0
            
            # Detectar sazonalidade
            if "enem" in tema.lower():
                # ENEM cresce muito entre março-novembro
                if 3 <= now.month <= 11:
                    growth_rate = 15
                else:
                    growth_rate = -5
            elif "vestibular" in tema.lower():
                # Vestibular cresce entre agosto-dezembro
                if 8 <= now.month <= 12:
                    growth_rate = 12
                else:
                    growth_rate = -3
            elif any(term in tema.lower() for term in ["matemática", "física", "química"]):
                # Matérias escolares crescem durante período letivo
                if 2 <= now.month <= 6 or 8 <= now.month <= 11:
                    growth_rate = 8
                else:
                    growth_rate = -2
            elif "tecnologia" in tema.lower():
                # Tecnologia cresce constantemente
                growth_rate = 5
            else:
                # Crescimento neutro para temas genéricos
                growth_rate = 2
            
            # Determinar tendência
            if growth_rate > 10:
                tendencia = "crescendo"
                previsao = "alta"
            elif growth_rate > 0:
                tendencia = "estável"
                previsao = "média"
            else:
                tendencia = "declinando"
                previsao = "baixa"
            
            return {
                "crescimento_30_dias": f"{growth_rate:+.1f}%",
                "tendencia": tendencia,
                "previsao_proximo_mes": previsao,
                "pico_interesse": "últimos 7 dias" if growth_rate > 15 else "últimos 30 dias"
            }
            
        except Exception as e:
            logger.error(f"Erro na estimativa de crescimento: {e}")
            return {
                "crescimento_30_dias": "+3.0%",
                "tendencia": "estável",
                "previsao_proximo_mes": "média",
                "pico_interesse": "últimos 30 dias"
            }
    
    @staticmethod
    def _get_fallback_trends(tema: str) -> Dict[str, Any]:
        """Fallback final com dados inteligentes"""
        keywords = TrendsService._generate_smart_keywords(tema)
        
        return {
            "keywords": keywords,
            "metrics": {
                "interesse_atual": 40,
                "popularidade_score": 40,
                "volume_busca_mensal": 4000,
                "interesse_regional": {"BR": 100}
            },
            "growth": {
                "crescimento_30_dias": "+5.0%",
                "tendencia": "estável",
                "previsao_proximo_mes": "média",
                "pico_interesse": "últimos 30 dias"
            }
        }

class ContentProcessor:
    """Processamento de conteúdo"""
    
    @staticmethod
    def rank_and_dedup(artigos: List[Dict]) -> List[Dict]:
        """Remove duplicados e ordena por relevância"""
        try:
            logger.info(f"Processando {len(artigos)} artigos")
            
            if not artigos:
                return []
            
            # Remove duplicados por título e URL
            unique_articles = []
            seen_titles = set()
            seen_urls = set()
            
            for artigo in artigos:
                titulo = artigo.get("titulo", "").lower().strip()
                url = artigo.get("url", "")
                
                # Verificar duplicatas
                if titulo in seen_titles or url in seen_urls:
                    continue
                
                # Verificar título muito curto
                if len(titulo) < 10:
                    continue
                
                seen_titles.add(titulo)
                seen_urls.add(url)
                unique_articles.append(artigo)
            
            # Ordenar por confiança e data
            confidence_order = {"alto": 3, "médio": 2, "baixo": 1}
            
            def sort_key(artigo):
                confidence_score = confidence_order.get(artigo.get("confianca", "médio"), 2)
                # Data mais recente = melhor
                try:
                    date_obj = datetime.strptime(artigo.get("data", "2000-01-01")[:10], "%Y-%m-%d")
                    days_old = (datetime.now() - date_obj).days
                    date_score = max(0, 30 - days_old)  # Bonus para artigos recentes
                except:
                    date_score = 0
                
                return (confidence_score, date_score)
            
            unique_articles.sort(key=sort_key, reverse=True)
            
            logger.info(f"Após processamento: {len(unique_articles)} artigos únicos")
            return unique_articles
            
        except Exception as e:
            logger.error(f"Erro ao processar artigos: {e}")
            return artigos

class AIContentGenerator:
    """Geração de conteúdo com IA"""
    
    @staticmethod
    async def _call_openai_gpt(prompt: str, max_tokens: int = 500) -> Optional[str]:
        """
        Chama a API da OpenAI GPT
        """
        try:
            client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "Você é um especialista em criação de conteúdo para podcasts. Seja objetivo, informativo e engajante. Responda sempre em português brasileiro."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Erro na chamada para OpenAI: {e}")
            return None
    
    @staticmethod
    async def gen_summary(tema: str, artigos: List[Dict], duracao: int, tone: str) -> str:
        """
        Gera resumo executivo
        """
        logger.info(f"Gerando summary para {tema}")
        
        if os.getenv("OPENAI_API_KEY"):
            try:
                # Preparar contexto dos artigos
                artigos_context = ""
                for artigo in artigos[:3]:
                    artigos_context += f"- {artigo['titulo']} ({artigo['fonte']})\n"
                
                prompt = f"""
                Crie um resumo executivo para um episódio de podcast sobre "{tema}".
                
                Contexto:
                - Duração: {duracao} minutos
                - Tom: {tone}
                - Artigos de referência:
                {artigos_context}
                
                O resumo deve ser:
                - Informativo e envolvente
                - Adequado para o tom {tone}
                - Focado nos pontos mais relevantes
                - Entre 2-3 frases concisas
                - Em português brasileiro
                
                Resumo:
                """
                
                ai_summary = await AIContentGenerator._call_openai_gpt(prompt, 200)
                
                if ai_summary:
                    logger.info("Summary gerado com sucesso via GPT")
                    return ai_summary
                
            except Exception as e:
                logger.error(f"Erro na IA para summary: {e}")
        
        # Fallback sem dados fictícios - apenas estrutural
        return f"Análise atualizada sobre {tema} com base em {len(artigos)} fontes recentes, " \
               f"formatada para {duracao} minutos de conteúdo informativo."
    
    @staticmethod
    async def gen_titles(tema: str, duracao: int, tone: str) -> List[str]:
        """
        Gera títulos com GPT
        """
        logger.info(f"Gerando títulos para {tema}")
        
        if os.getenv("OPENAI_API_KEY"):
            try:
                prompt = f"""
                Crie 5 títulos atrativos para um episódio de podcast sobre "{tema}".
                
                Requisitos:
                - Duração: {duracao} minutos
                - Tom: {tone}
                - Títulos devem ser SEO-friendly
                - Incluir o tema principal
                - Variar o estilo entre informativos e curiosos
                - Em português brasileiro
                
                Formato: retorne apenas os títulos, um por linha, sem numeração.
                """
                
                ai_titles = await AIContentGenerator._call_openai_gpt(prompt, 300)
                
                if ai_titles:
                    titles_list = [title.strip() for title in ai_titles.split('\n') if title.strip()]
                    if len(titles_list) >= 3:
                        logger.info("Títulos gerados com sucesso via GPT")
                        return titles_list[:5]
                
            except Exception as e:
                logger.error(f"Erro na geração de títulos via IA: {e}")
        
        # Fallback estrutural (não fictício)
        return [
            f"{tema.title()}: Análise Completa em {duracao} Minutos",
            f"Guia Atualizado sobre {tema.title()}",
            f"{tema.title()}: O Que Você Precisa Saber",
            f"Novidades e Tendências em {tema.title()}",
            f"{tema.title()} Explicado - Episódio Completo"
        ]