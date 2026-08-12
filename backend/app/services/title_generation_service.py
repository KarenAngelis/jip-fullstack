# app/services/title_generation_service.py
import asyncio
import re
import json
import time
from typing import List, Dict, Tuple, Optional
import logging
from openai import AsyncOpenAI
import aiohttp
import random
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.schemas.title_generation import (
    TitleGenerationRequest, 
    TitleGenerationResponse, 
    GeneratedTitle, 
    TitleScore,
    TitleAnalysisRequest,
    TitleAnalysisResponse
)
from app.models.title_generation_model import TitleGeneration

logger = logging.getLogger(__name__)

class TitleGenerationService:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.power_words = [
            # Urgência
            "agora", "hoje", "rápido", "imediato", "urgente", "último", "final",
            # Números e listas
            "top", "melhor", "pior", "primeiro", "único", "exclusivo", "segredo",
            # Emocionais
            "incrível", "surpreendente", "chocante", "revolucionário", "épico", 
            "fantástico", "impossível", "proibido", "secreto", "oculto",
            # Curiosidade
            "como", "por que", "o que", "quando", "onde", "quem", "qual",
            # Benefícios
            "grátis", "gratuito", "sem custo", "fácil", "simples", "rápido", "eficaz",
            # Negativos (que funcionam)
            "erro", "problema", "falha", "mito", "mentira", "evitar", "nunca",
            # Sociais
            "todos", "ninguém", "maioria", "poucos", "expert", "profissional", "guru"
        ]
        
        self.trending_keywords = []
        self.last_trends_update = 0
    
    async def get_google_trends(self, topic: str) -> List[str]:
        """Busca trends relacionadas ao tópico via Google Trends API simulada"""
        try:
            # Simula busca de trends relacionadas (você pode integrar com pytrends ou API real)
            simulated_trends = [
                f"{topic} 2025",
                f"{topic} iniciantes",
                f"como {topic}",
                f"{topic} passo a passo",
                f"{topic} dicas",
                f"melhor {topic}",
                f"{topic} tutorial",
                f"{topic} guia completo",
                f"{topic} para iniciantes",
                f"{topic} avançado"
            ]
            
            # Adiciona algumas trends reais simuladas baseadas no tempo atual
            current_trends = [
                "inteligência artificial",
                "ChatGPT",
                "produtividade",
                "home office",
                "marketing digital",
                "empreendedorismo",
                "investimentos",
                "criptomoedas",
                "sustentabilidade",
                "saúde mental"
            ]
            
            # Filtra trends relacionadas ao tópico
            related_trends = [trend for trend in current_trends if any(word in topic.lower() for word in trend.split())]
            
            return simulated_trends[:5] + related_trends[:3]
            
        except Exception as e:
            logger.error(f"Erro ao buscar trends: {e}")
            return []
    
    def calculate_title_scores(self, title: str, trends_used: List[str]) -> TitleScore:
        """Calcula scores detalhados para um título"""
        
        # Score de Engajamento (baseado em palavras de poder, números, etc.)
        engagement_score = 50  # Base
        
        # Palavras de poder encontradas
        power_words_found = [word for word in self.power_words if word.lower() in title.lower()]
        engagement_score += len(power_words_found) * 8
        
        # Números no título
        numbers_found = re.findall(r'\d+', title)
        engagement_score += len(numbers_found) * 10
        
        # Perguntas (engajam mais)
        if any(word in title.lower() for word in ['como', 'por que', 'o que', 'quando', 'onde']):
            engagement_score += 15
        
        # Listas (X coisas, X formas, etc.)
        if any(pattern in title.lower() for pattern in ['coisas', 'formas', 'maneiras', 'dicas', 'passos']):
            engagement_score += 12
        
        engagement_score = min(100, engagement_score)
        
        # Score de SEO
        seo_score = 40  # Base
        
        # Comprimento ideal (50-60 caracteres)
        title_length = len(title)
        if 45 <= title_length <= 65:
            seo_score += 20
        elif 35 <= title_length <= 80:
            seo_score += 10
        
        # Keywords longas (mais de 2 palavras)
        words = title.split()
        if len(words) >= 4:
            seo_score += 15
        
        # Uso de palavras-chave específicas
        seo_keywords = ['tutorial', 'guia', 'como fazer', 'passo a passo', 'completo', 'melhor', 'top']
        for keyword in seo_keywords:
            if keyword in title.lower():
                seo_score += 8
        
        seo_score = min(100, seo_score)
        
        # Score de Trend
        trend_score = 30  # Base
        trend_score += len(trends_used) * 15
        if trends_used:
            trend_score += 25  # Bonus por usar trends
        
        trend_score = min(100, trend_score)
        
        # Score Geral (média ponderada)
        overall_score = int((engagement_score * 0.4 + seo_score * 0.3 + trend_score * 0.3))
        
        return TitleScore(
            engagement=engagement_score,
            seo=seo_score,
            trend=trend_score,
            overall=overall_score
        )
    
    async def generate_titles_with_gpt(
        self, 
        request: TitleGenerationRequest, 
        trends: List[str]
    ) -> Tuple[List[str], int, int]:
        """Gera títulos usando GPT-4 com otimização para engajamento"""
        
        # Monta prompt otimizado
        trends_text = f"\nTrends atuais relacionadas: {', '.join(trends)}" if trends else ""
        power_words_text = f"\nUse palavras de poder como: {', '.join(random.sample(self.power_words, 15))}"
        
        prompt = f"""Você é um especialista em marketing de conteúdo e copywriting viral. 
Sua missão é criar títulos que PARAM o scroll e geram cliques irresistíveis.

TÓPICO: {request.topic}
AUDIÊNCIA: {request.audience.value}
TIPO DE CONTEÚDO: {request.content_type.value}
TOM: {request.tone.value}
COMPRIMENTO MÁXIMO: {request.max_length} caracteres{trends_text}{power_words_text if request.include_power_words else ""}

REGRAS OBRIGATÓRIAS:
1. Cada título deve ter no MÁXIMO {request.max_length} caracteres
2. {'USE NÚMEROS quando possível (estatísticas, listas, passos)' if request.include_numbers else 'Evite números'}
3. {'Integre as trends atuais de forma natural' if request.use_trends and trends else ''}
4. Foque em gatilhos emocionais: curiosidade, urgência, benefício claro
5. Use poder de storytelling: "Como", "Por que", "O que", "Segredo de"

FÓRMULAS DE ALTA CONVERSÃO:
- "Como [fazer algo] em X [tempo/passos] (mesmo [obstáculo])"
- "[Número] [coisas] que [resultado desejado] (a maioria não sabe)"  
- "O segredo de [autoridade] para [resultado] que [benefício]"
- "Por que [crença comum] está [sabotando/impedindo] seu [objetivo]"

GERE EXATAMENTE {request.quantity} TÍTULOS ÚNICOS E IRRESISTÍVEIS.

Responda APENAS com um JSON válido no formato:
{{
    "titles": [
        {{
            "title": "título aqui",
            "trends_used": ["trend1", "trend2"],
            "power_words": ["palavra1", "palavra2"]
        }}
    ]
}}"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é um copywriter expert em títulos virais e marketing de conteúdo."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.8,  # Criatividade alta
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown se houver
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            # Parse do JSON
            data = json.loads(content)
            titles_data = data.get("titles", [])
            
            # Extrai apenas os títulos e metadados
            titles = []
            all_trends_used = []
            all_power_words = []
            
            for item in titles_data:
                titles.append(item["title"])
                all_trends_used.extend(item.get("trends_used", []))
                all_power_words.extend(item.get("power_words", []))
            
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            
            return titles, prompt_tokens, completion_tokens
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON do GPT: {e}")
            # Fallback: títulos genéricos
            fallback_titles = [
                f"Como dominar {request.topic} em 2025",
                f"{request.topic}: Guia completo para iniciantes",
                f"5 segredos de {request.topic} que poucos conhecem",
                f"O método definitivo de {request.topic}",
                f"Por que {request.topic} é essencial agora"
            ]
            return fallback_titles[:request.quantity], 0, 0
            
        except Exception as e:
            logger.error(f"Erro na geração de títulos: {e}")
            return [], 0, 0
    
    async def generate_titles(
        self, 
        request: TitleGenerationRequest,
        db: Optional[Session] = None,
        user_ip: Optional[str] = None
    ) -> TitleGenerationResponse:
        """Método principal para geração de títulos"""
        start_time = time.time()
        
        try:
            # 1. Busca trends se solicitado
            trends = []
            if request.use_trends:
                trends = await self.get_google_trends(request.topic)
            
            # 2. Gera títulos com GPT
            titles_text, prompt_tokens, completion_tokens = await self.generate_titles_with_gpt(request, trends)
            
            # 3. Processa e calcula scores
            generated_titles = []
            for title in titles_text:
                # Identifica trends usadas no título
                trends_used = [trend for trend in trends if any(word in title.lower() for word in trend.lower().split())]
                
                # Identifica power words
                power_words_found = [word for word in self.power_words if word.lower() in title.lower()]
                
                # Calcula scores
                scores = self.calculate_title_scores(title, trends_used)
                
                generated_titles.append(GeneratedTitle(
                    title=title,
                    scores=scores,
                    trends_used=trends_used,
                    power_words=power_words_found
                ))
            
            # Ordena por score geral (melhor primeiro)
            generated_titles.sort(key=lambda x: x.scores.overall, reverse=True)
            
            generation_time = time.time() - start_time
            
            # ✅ SALVAR NO BANCO DE DADOS
            if db and generated_titles:
                try:
                    # Pega o melhor título
                    best_title = generated_titles[0]
                    
                    db_record = TitleGeneration(
                        topic=request.topic,
                        usuario_ip=user_ip,
                        audience=request.audience.value,
                        content_type=request.content_type.value,
                        tone=request.tone.value,
                        quantity=request.quantity,
                        max_length=request.max_length,
                        use_trends=request.use_trends,
                        include_numbers=request.include_numbers,
                        include_power_words=request.include_power_words,
                        titles_generated=[
                            {
                                "title": t.title,
                                "scores": {
                                    "engagement": t.scores.engagement,
                                    "seo": t.scores.seo,
                                    "trend": t.scores.trend,
                                    "overall": t.scores.overall
                                },
                                "trends_used": t.trends_used,
                                "power_words": t.power_words
                            }
                            for t in generated_titles
                        ],
                        total_titles=len(generated_titles),
                        trends_found=trends,
                        best_title=best_title.title,
                        best_score=best_title.scores.overall,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=prompt_tokens + completion_tokens,
                        generation_time=generation_time,
                        status="success"
                    )
                    
                    db.add(db_record)
                    db.commit()
                    db.refresh(db_record)
                    logger.info(f"✅ Títulos salvos no banco: ID {db_record.id}")
                    
                except Exception as db_error:
                    logger.error(f"❌ Erro ao salvar no banco: {db_error}")
                    db.rollback()
            
            return TitleGenerationResponse(
                success=True,
                titles=generated_titles,
                trends_found=trends,
                generation_time=generation_time,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )
            
        except Exception as e:
            logger.error(f"Erro geral na geração de títulos: {e}")
            
            # ❌ SALVAR ERRO NO BANCO
            if db:
                try:
                    db_error = TitleGeneration(
                        topic=request.topic,
                        usuario_ip=user_ip,
                        audience=request.audience.value,
                        content_type=request.content_type.value,
                        tone=request.tone.value,
                        quantity=request.quantity,
                        max_length=request.max_length,
                        use_trends=request.use_trends,
                        include_numbers=request.include_numbers,
                        include_power_words=request.include_power_words,
                        titles_generated=[],
                        total_titles=0,
                        trends_found=[],
                        status="error",
                        error_message=str(e),
                        generation_time=time.time() - start_time
                    )
                    
                    db.add(db_error)
                    db.commit()
                    logger.info(f"❌ Erro salvo no banco")
                    
                except Exception as db_error:
                    logger.error(f"❌ Erro ao salvar erro no banco: {db_error}")
                    db.rollback()
            
            return TitleGenerationResponse(
                success=False,
                titles=[],
                trends_found=[],
                generation_time=time.time() - start_time,
                prompt_tokens=0,
                completion_tokens=0
            )
    
    async def analyze_title(self, request: TitleAnalysisRequest) -> TitleAnalysisResponse:
        """Analisa um título existente e dá sugestões de melhoria"""
        try:
            title = request.title
            
            # Busca trends se tópico fornecido
            trends = []
            if request.topic:
                trends = await self.get_google_trends(request.topic)
            
            trends_used = [trend for trend in trends if any(word in title.lower() for word in trend.lower().split())]
            scores = self.calculate_title_scores(title, trends_used)
            
            # Power words detectadas
            power_words_detected = [word for word in self.power_words if word.lower() in title.lower()]
            
            # Análise de comprimento
            length_analysis = {
                "current_length": len(title),
                "ideal_range": "50-60 caracteres",
                "status": "ideal" if 50 <= len(title) <= 60 else 
                         "muito longo" if len(title) > 80 else "muito curto",
                "seo_friendly": 45 <= len(title) <= 65
            }
            
            # Sugestões baseadas nos scores
            suggestions = []
            
            if scores.engagement < 70:
                suggestions.append("Adicione palavras de poder para aumentar o engajamento")
                suggestions.append("Considere usar números (ex: '5 formas', '10 dicas')")
                suggestions.append("Transforme em pergunta (Como, Por que, O que)")
            
            if scores.seo < 70:
                suggestions.append("Ajuste o comprimento para 50-60 caracteres")
                suggestions.append("Inclua palavras-chave mais específicas")
            
            if scores.trend < 50 and request.topic:
                suggestions.append("Incorpore trends atuais relacionadas ao tópico")
            
            if not power_words_detected:
                suggestions.append("Use palavras que geram curiosidade: 'segredo', 'revelado', 'surpreendente'")
            
            # Keywords SEO identificadas
            seo_keywords = re.findall(r'\b\w+\b', title.lower())
            seo_keywords = [word for word in seo_keywords if len(word) > 3][:5]
            
            return TitleAnalysisResponse(
                success=True,
                title=title,
                scores=scores,
                suggestions=suggestions,
                power_words_detected=power_words_detected,
                length_analysis=length_analysis,
                seo_keywords=seo_keywords
            )
            
        except Exception as e:
            logger.error(f"Erro na análise do título: {e}")
            return TitleAnalysisResponse(
                success=False,
                title=request.title,
                scores=TitleScore(engagement=0, seo=0, trend=0, overall=0),
                suggestions=["Erro na análise. Tente novamente."],
                power_words_detected=[],
                length_analysis={},
                seo_keywords=[]
            )

# Instância global do serviço
title_service = TitleGenerationService()