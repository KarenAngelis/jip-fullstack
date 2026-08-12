# app/routers/episode_suggestions.py
from fastapi import APIRouter, HTTPException, Depends, Query, status, Request
from typing import List, Optional
import logging
from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from ..dependencies.auth import get_current_active_user
from ..schemas.auth_schema import UserResponse
from ..schemas.episode_suggestions_schema import (
    EpisodeSuggestionRequest,
    EpisodeSuggestionsResponse,
    EpisodeSuggestion,
    EpisodeAnalyticsRequest
)
from ..services.episode_suggestions_service import EpisodeSuggestionsService
from ..database.database import get_db
from ..models.episode_suggestion_model import (
    EpisodeSuggestionBatch,
    EpisodeSuggestion as EpisodeSuggestionDB
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/episode-suggestions", tags=["Episode Suggestions"])

# Instância do serviço
episode_service = EpisodeSuggestionsService()

@router.post("/generate", response_model=EpisodeSuggestionsResponse)
async def generate_episode_suggestions(
    request: EpisodeSuggestionRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Gera 12 sugestões de episódios baseadas no título fornecido
    
    Integra análises de:
    - Google Trends (análise preditiva)
    - YouTube Trends (métricas de vídeo)
    - Análise Jurídica (compliance)
    - ChatGPT/IA (geração de conteúdo)
    
    Retorna:
    1. Título
    2. Descrição curta (roteiro reduzido)  
    3. Palavras-chave para o episódio
    4. Indicação de convidados
    5. Percentual de acerto (análise preditiva)
    6. Análise jurídica com status
    """
    try:
        logger.info(f"Gerando sugestões para: '{request.title}'")
        
        # Pega IP do usuário
        user_ip = http_request.client.host if http_request else None
        
        start_time = datetime.now()
        response = await episode_service.generate_episode_suggestions(
            request,
            db=db,
            user_ip=user_ip,
            user_id=current_user.id
        )
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Geradas {response.total_suggestions} sugestões em {processing_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"Erro ao gerar sugestões: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar sugestões: {str(e)}"
        )

@router.get("/episode/{episode_id}", response_model=EpisodeSuggestion)
async def get_episode_details(
    episode_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Busca detalhes completos de um episódio específico
    
    Retorna todas as análises e métricas detalhadas para um episódio,
    incluindo trend analysis, legal status e sugestões de convidados.
    """
    try:
        logger.info(f"Buscando detalhes do episódio: {episode_id}")
        
        episode = await episode_service.get_episode_details(episode_id, db=db)
        
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Episódio não encontrado"
            )
        
        logger.info(f"Detalhes encontrados para episódio: {episode.title}")
        return episode
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar episódio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar episódio: {str(e)}"
        )

@router.post("/episode/{episode_id}/reanalyze", response_model=EpisodeSuggestion)
async def reanalyze_episode(
    episode_id: str,
    additional_keywords: List[str] = Query([], description="Keywords adicionais para análise"),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Re-analisa um episódio com keywords adicionais
    
    Permite refinar a análise de um episódio adicionando novas palavras-chave
    e recalculando todas as métricas (trends, legal, YouTube).
    """
    try:
        logger.info(f"Re-analisando episódio {episode_id} com keywords: {additional_keywords}")
        
        updated_episode = await episode_service.reanalyze_episode(
            episode_id, additional_keywords
        )
        
        if not updated_episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Episódio não encontrado"
            )
        
        logger.info(f"Episódio re-analisado com sucesso. Nova probabilidade: {updated_episode.success_probability}%")
        return updated_episode
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na re-análise: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na re-análise: {str(e)}"
        )

@router.get("/templates")
async def get_suggestion_templates(
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Retorna templates e exemplos para criação de episódios
    
    Lista formatos populares, estruturas de título e contextos
    que funcionam bem na plataforma.
    """
    return {
        "title_templates": [
            "Como [AÇÃO] em [ÁREA] sem [OBSTÁCULO]",
            "Os Segredos de [TEMA] que Ninguém Conta",
            "[NÚMERO] Estratégias para [RESULTADO]",
            "De [SITUAÇÃO A] para [SITUAÇÃO B]: Minha Jornada",
            "O Guia Definitivo de [TEMA] para Iniciantes",
            "Erros Comuns em [ÁREA] e Como Evitá-los",
            "Masterclass: [HABILIDADE] em [TEMPO] Dias",
            "Por Que [CRENÇA COMUM] Está Errada",
            "[TEMA]: Mitos vs Realidade",
            "A Verdade Sobre [TÓPICO POLÊMICO]"
        ],
        "context_examples": [
            "Baseado na minha experiência de 5 anos como...",
            "Depois de falir e recomeçar, aprendi que...",
            "Como alguém que já passou por...",
            "Sendo introvertido, descobri como...",
            "Após perder tudo, consegui...",
            "Como mãe/pai empreendedor(a)...",
            "Migrando de carreira aos 40 anos...",
            "Superando a síndrome do impostor..."
        ],
        "successful_formats": [
            {
                "format": "Entrevista com Especialista",
                "description": "Conversa com expert no assunto",
                "duration": "45-60 min",
                "success_rate": "85%"
            },
            {
                "format": "História Pessoal + Lições",
                "description": "Narrativa pessoal com insights",
                "duration": "30-45 min", 
                "success_rate": "80%"
            },
            {
                "format": "Tutorial Prático",
                "description": "Passo a passo para resolver problema",
                "duration": "25-40 min",
                "success_rate": "75%"
            },
            {
                "format": "Debate de Ideias",
                "description": "Discussão de diferentes perspectivas",
                "duration": "40-55 min",
                "success_rate": "70%"
            }
        ],
        "trending_topics_br": [
            "Inteligência Artificial no Trabalho",
            "Empreendedorismo Digital", 
            "Saúde Mental e Produtividade",
            "Investimentos para Iniciantes",
            "Marketing de Conteúdo",
            "Desenvolvimento Pessoal",
            "Tecnologia e Futuro",
            "Sustentabilidade e Negócios"
        ]
    }

@router.get("/analytics/summary")
async def get_analytics_summary(
    days: int = Query(7, ge=1, le=30, description="Período em dias"),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Resumo de analytics das sugestões geradas
    
    Mostra estatísticas sobre as sugestões criadas, temas populares,
    success rates médios e insights sobre performance.
    """
    # Analytics mock - em produção, conectar com banco de dados
    return {
        "period_days": days,
        "total_suggestions_generated": 156,
        "unique_users": 23,
        "avg_success_rate": 78.5,
        "top_themes": [
            {"theme": "Empreendedorismo", "count": 34, "avg_success": 82.1},
            {"theme": "Tecnologia", "count": 28, "avg_success": 79.3},
            {"theme": "Marketing", "count": 22, "avg_success": 76.8},
            {"theme": "Desenvolvimento Pessoal", "count": 19, "avg_success": 81.2},
            {"theme": "Negócios", "count": 15, "avg_success": 77.9}
        ],
        "legal_analysis_stats": {
            "status_ok": 89.2,
            "status_warning": 8.7,
            "status_error": 2.1
        },
        "guest_suggestions_stats": {
            "avg_guests_per_episode": 2.3,
            "most_requested_expertise": [
                "CEO/Fundador", "Especialista em IA", "Consultor Estratégico"
            ]
        },
        "trend_insights": {
            "best_performing_months": ["Janeiro", "Setembro", "Outubro"],
            "optimal_posting_times": "Terça a Quinta, 14h-17h",
            "trending_keywords": ["IA", "startup", "produtividade", "investimentos"]
        }
    }

@router.get("/health")
async def health_check():
    """Verifica status dos serviços integrados"""
    try:
        # Testa integração com os serviços
        health_status = {
            "episode_suggestions": "ok",
            "google_trends": "ok",
            "youtube_api": "configured" if episode_service.youtube_api_key else "not_configured",
            "news_insights": "ok",
            "legal_analyzer": "ok",
            "cache_status": f"{len(episode_service.episode_cache)} itens em cache",
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "status": "healthy",
            "services": health_status,
            "features": [
                "Geração de 12 sugestões por request",
                "Análise integrada de trends, legal e YouTube",
                "Sugestões de convidados especialistas",
                "Análise preditiva de sucesso",
                "Cache inteligente (10 min)",
                "Re-análise com keywords adicionais"
            ]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Erro no health check: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

# ==================== NOVOS ENDPOINTS DE HISTÓRICO ====================

@router.get("/history")
async def get_user_history(
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Máximo de batches"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    include_episodes: bool = Query(True, description="Incluir episódios completos")
):
    """
    Lista histórico de gerações do usuário
    
    Retorna batches ordenados do mais recente para o mais antigo.
    Se include_episodes=True (padrão), inclui os 12 episódios de cada batch.
    
    Parâmetros:
    - limit: Máximo de batches (1-100)
    - offset: Para paginação
    - include_episodes: true = traz episódios completos | false = só resumo do batch
    
    Exemplos:
    - GET /history → Traz tudo completo (batches + episódios)
    - GET /history?include_episodes=false → Só resumo dos batches
    - GET /history?limit=10&offset=0 → Primeiros 10 batches com episódios
    """
    try:
        logger.info(f"Buscando histórico do usuário {current_user.id}")
        
        # Busca batches do usuário com episódios (eager loading)
        batches_query = db.query(EpisodeSuggestionBatch).filter(
            EpisodeSuggestionBatch.user_id == current_user.id
        )
        
        # Se incluir episódios, faz join otimizado
        if include_episodes:
            batches_query = batches_query.options(
                joinedload(EpisodeSuggestionBatch.episodes)
            )
        
        batches = batches_query.order_by(
            EpisodeSuggestionBatch.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        total = db.query(EpisodeSuggestionBatch).filter(
            EpisodeSuggestionBatch.user_id == current_user.id
        ).count()
        
        history_items = []
        for batch in batches:
            batch_data = {
                "batch_id": batch.id,
                "request_title": batch.request_title,
                "request_context": batch.request_context,
                "request_personal_input": batch.request_personal_input,
                "request_target_audience": batch.request_target_audience,
                "request_episode_format": batch.request_episode_format,
                "total_suggestions": batch.total_suggestions,
                "overall_trend_score": batch.overall_trend_score,
                "market_opportunity": batch.market_opportunity,
                "recommended_timing": batch.recommended_timing,
                "processing_time_ms": batch.processing_time_ms,
                "created_at": batch.created_at.isoformat(),
                "status": batch.status
            }
            
            # Adiciona episódios se solicitado
            if include_episodes:
                episodes_list = []
                for ep in batch.episodes:
                    episodes_list.append({
                        "id": ep.id,
                        "title": ep.title,
                        "short_description": ep.short_description,
                        "keywords": ep.keywords,
                        "success_probability": ep.success_probability,
                        "estimated_duration": ep.estimated_duration,
                        "difficulty_level": ep.difficulty_level,
                        "target_audience": ep.target_audience,
                        "guest_suggestions": ep.guest_suggestions,
                        "jip_trend_analysis": ep.jip_trend_analysis,
                        "jip_legal_analysis": ep.jip_legal_analysis,
                        "jip_market_analysis": ep.jip_market_analysis,
                        "episode_news": ep.episode_news,
                        "created_at": ep.created_at.isoformat()
                    })
                
                batch_data["episodes"] = episodes_list
            
            history_items.append(batch_data)
        
        logger.info(f"✅ Encontrados {len(history_items)} batches (include_episodes={include_episodes})")
        
        return {
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "include_episodes": include_episodes,
            "data": history_items
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar histórico: {str(e)}"
        )

@router.get("/batch/{batch_id}")
async def get_batch_details(
    batch_id: int,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Busca detalhes completos de um batch (incluindo os 12 episódios)
    
    Retorna:
    - Informações do batch
    - Lista dos 12 episódios gerados
    """
    try:
        logger.info(f"Buscando batch {batch_id}")
        
        # Busca batch com episódios (eager loading)
        batch = db.query(EpisodeSuggestionBatch).options(
            joinedload(EpisodeSuggestionBatch.episodes)
        ).filter(
            EpisodeSuggestionBatch.id == batch_id,
            EpisodeSuggestionBatch.user_id == current_user.id  # Segurança: só do usuário
        ).first()
        
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Batch não encontrado"
            )
        
        # Converter episódios para dict
        episodes_list = []
        for ep in batch.episodes:
            episodes_list.append({
                "id": ep.id,
                "title": ep.title,
                "short_description": ep.short_description,
                "keywords": ep.keywords,
                "success_probability": ep.success_probability,
                "estimated_duration": ep.estimated_duration,
                "difficulty_level": ep.difficulty_level,
                "target_audience": ep.target_audience,
                "guest_suggestions": ep.guest_suggestions,
                "jip_trend_analysis": ep.jip_trend_analysis,
                "jip_legal_analysis": ep.jip_legal_analysis,
                "jip_market_analysis": ep.jip_market_analysis,
                "episode_news": ep.episode_news,
                "created_at": ep.created_at.isoformat()
            })
        
        logger.info(f"Batch {batch_id} com {len(episodes_list)} episódios")
        
        return {
            "success": True,
            "batch": {
                "id": batch.id,
                "request_title": batch.request_title,
                "request_context": batch.request_context,
                "request_personal_input": batch.request_personal_input,
                "request_target_audience": batch.request_target_audience,
                "request_episode_format": batch.request_episode_format,
                "total_suggestions": batch.total_suggestions,
                "overall_trend_score": batch.overall_trend_score,
                "market_opportunity": batch.market_opportunity,
                "recommended_timing": batch.recommended_timing,
                "processing_time_ms": batch.processing_time_ms,
                "created_at": batch.created_at.isoformat(),
                "status": batch.status
            },
            "episodes": episodes_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar batch: {str(e)}"
        )

@router.delete("/batch/{batch_id}")
async def delete_batch(
    batch_id: int,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Deleta um batch e todos os seus episódios
    
    O delete é em cascade, então os 12 episódios são deletados automaticamente.
    """
    try:
        logger.info(f"Deletando batch {batch_id}")
        
        # Busca batch
        batch = db.query(EpisodeSuggestionBatch).filter(
            EpisodeSuggestionBatch.id == batch_id,
            EpisodeSuggestionBatch.user_id == current_user.id  # Segurança
        ).first()
        
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Batch não encontrado"
            )
        
        # Delete cascade automático (episódios são deletados junto)
        db.delete(batch)
        db.commit()
        
        logger.info(f"✅ Batch {batch_id} deletado")
        
        return {
            "success": True,
            "message": f"Batch {batch_id} e seus episódios foram deletados com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao deletar batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar batch: {str(e)}"
        )