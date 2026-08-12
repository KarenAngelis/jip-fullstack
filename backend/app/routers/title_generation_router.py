# app/routers/title_generation_router.py
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.schemas.title_generation import (
    TitleGenerationRequest,
    TitleGenerationResponse,
    TitleAnalysisRequest,
    TitleAnalysisResponse,
    AudienceType,
    ToneType,
    ContentType
)
from app.services.title_generation_service import title_service
from app.dependencies.auth import get_current_active_user
from app.schemas.auth_schema import UserResponse
from app.database.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/generate-simple", response_model=TitleGenerationResponse)
async def generate_titles_simple(
    topic: str,
    audience: str = "geral",
    tone: str = "casual",
    quantity: int = 5,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    🚀 VERSÃO SIMPLIFICADA para usuários finais
    
    Gera títulos otimizados com apenas o essencial:
    - topic: "motivação para estudar"
    - audience: "geral", "iniciantes", "intermediario", "avancado" 
    - tone: "casual", "profissional", "divertido", "inspirador"
    - quantity: quantos títulos gerar (1-10)
    
    Todos os parâmetros técnicos são otimizados automaticamente!
    """
    try:
        logger.info(f"Usuário {current_user.email} gerando títulos (simples) para: {topic}")
        
        if not topic.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Por favor, digite um tópico"
            )
        
        if len(topic) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tópico deve ter pelo menos 3 caracteres"
            )
        
        # Converte strings para enums
        try:
            audience_enum = AudienceType(audience.lower())
        except ValueError:
            audience_enum = AudienceType.GERAL
            
        try:
            tone_enum = ToneType(tone.lower())  
        except ValueError:
            tone_enum = ToneType.CASUAL
        
        # Monta request com defaults otimizados
        title_request = TitleGenerationRequest(
            topic=topic.strip(),
            audience=audience_enum,
            content_type=ContentType.TUTORIAL,  # Default inteligente
            tone=tone_enum,
            quantity=min(quantity, 10),  # Limita quantidade
            use_trends=True,
            include_numbers=True, 
            include_power_words=True,
            max_length=60
        )
        
        # Pega IP do usuário
        user_ip = request.client.host if request else None
        
        # ✅ Gera títulos E salva no banco
        result = await title_service.generate_titles(
            title_request,
            db=db,
            user_ip=user_ip
        )
        
        if not result.success or not result.titles:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Não foi possível gerar títulos. Tente novamente."
            )
        
        logger.info(f"✅ Títulos gerados (simples) e salvos: {len(result.titles)} títulos")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na geração simples de títulos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@router.post("/generate", response_model=TitleGenerationResponse)
async def generate_titles(
    request_data: TitleGenerationRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Gera títulos otimizados para engajamento usando IA e trends atuais.
    
    Features:
    - Integração com trends do Google
    - Otimização para SEO e engajamento
    - Análise de power words
    - Scores detalhados para cada título
    - Diferentes tons e tipos de conteúdo
    - **Salva automaticamente no banco de dados**
    """
    try:
        logger.info(f"Usuário {current_user.email} gerando títulos para: {request_data.topic}")
        
        # Validações básicas
        if not request_data.topic.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tópico é obrigatório"
            )
        
        if len(request_data.topic) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tópico deve ter pelo menos 3 caracteres"
            )
        
        # Pega IP do usuário
        user_ip = request.client.host if request else None
        
        # ✅ Gera títulos E salva no banco
        result = await title_service.generate_titles(
            request_data,
            db=db,
            user_ip=user_ip
        )
        
        if not result.success or not result.titles:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Não foi possível gerar títulos. Tente novamente."
            )
        
        logger.info(f"✅ Títulos gerados e salvos para {current_user.email}: {len(result.titles)} títulos")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado na geração de títulos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@router.post("/analyze", response_model=TitleAnalysisResponse)
async def analyze_title(
    request_data: TitleAnalysisRequest,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Analisa um título existente e fornece sugestões de melhoria.
    
    Features:
    - Análise de scores (engajamento, SEO, trends)
    - Detecção de power words
    - Sugestões personalizadas de melhoria
    - Análise de comprimento ideal
    - Identificação de keywords SEO
    """
    try:
        logger.info(f"Usuário {current_user.email} analisando título: {request_data.title[:50]}...")
        
        # Validações
        if not request_data.title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Título é obrigatório"
            )
        
        if len(request_data.title) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Título deve ter pelo menos 5 caracteres"
            )
        
        # Analisa título
        result = await title_service.analyze_title(request_data)
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Não foi possível analisar o título. Tente novamente."
            )
        
        logger.info(f"Título analisado com sucesso para {current_user.email}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado na análise de título: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@router.get("/history")
async def get_title_history(
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 20,
    offset: int = 0
):
    """
    📊 Retorna histórico de títulos gerados (todos os usuários).
    
    Query params:
    - limit: quantidade de registros (padrão: 20)
    - offset: paginação (padrão: 0)
    """
    try:
        from app.models.title_generation_model import TitleGeneration
        
        # Busca registros ordenados por data
        records = db.query(TitleGeneration)\
            .order_by(TitleGeneration.created_at.desc())\
            .limit(limit)\
            .offset(offset)\
            .all()
        
        total = db.query(TitleGeneration).count()
        
        history = []
        for record in records:
            history.append({
                "id": record.id,
                "topic": record.topic,
                "audience": record.audience,
                "content_type": record.content_type,
                "tone": record.tone,
                "best_title": record.best_title,
                "best_score": record.best_score,
                "total_titles": record.total_titles,
                "generation_time": record.generation_time,
                "status": record.status,
                "created_at": record.created_at.isoformat()
            })
        
        return {
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "history": history
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar histórico"
        )

@router.get("/history/{generation_id}")
async def get_title_generation_details(
    generation_id: int,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    🔍 Retorna detalhes completos de uma geração específica.
    """
    try:
        from app.models.title_generation_model import TitleGeneration
        
        record = db.query(TitleGeneration).filter(TitleGeneration.id == generation_id).first()
        
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Geração não encontrada"
            )
        
        return {
            "success": True,
            "generation": {
                "id": record.id,
                "topic": record.topic,
                "audience": record.audience,
                "content_type": record.content_type,
                "tone": record.tone,
                "quantity": record.quantity,
                "max_length": record.max_length,
                "use_trends": record.use_trends,
                "include_numbers": record.include_numbers,
                "include_power_words": record.include_power_words,
                "titles_generated": record.titles_generated,
                "total_titles": record.total_titles,
                "trends_found": record.trends_found,
                "best_title": record.best_title,
                "best_score": record.best_score,
                "prompt_tokens": record.prompt_tokens,
                "completion_tokens": record.completion_tokens,
                "total_tokens": record.total_tokens,
                "generation_time": record.generation_time,
                "status": record.status,
                "error_message": record.error_message,
                "created_at": record.created_at.isoformat(),
                "usuario_ip": record.usuario_ip
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar detalhes"
        )

@router.get("/stats")
async def get_title_stats(
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    📈 Estatísticas gerais de geração de títulos.
    """
    try:
        from app.models.title_generation_model import TitleGeneration
        from sqlalchemy import func
        
        total_generations = db.query(TitleGeneration).count()
        total_titles = db.query(func.sum(TitleGeneration.total_titles)).scalar() or 0
        avg_score = db.query(func.avg(TitleGeneration.best_score)).scalar() or 0
        avg_time = db.query(func.avg(TitleGeneration.generation_time)).scalar() or 0
        
        # Top 5 tópicos mais gerados
        top_topics = db.query(
            TitleGeneration.topic,
            func.count(TitleGeneration.id).label('count')
        ).group_by(TitleGeneration.topic)\
         .order_by(func.count(TitleGeneration.id).desc())\
         .limit(5)\
         .all()
        
        # Distribuição por tipo de conteúdo
        content_types = db.query(
            TitleGeneration.content_type,
            func.count(TitleGeneration.id).label('count')
        ).group_by(TitleGeneration.content_type).all()
        
        return {
            "success": True,
            "stats": {
                "total_generations": total_generations,
                "total_titles_created": int(total_titles),
                "average_best_score": round(float(avg_score), 2),
                "average_generation_time": round(float(avg_time), 2),
                "top_topics": [{"topic": t[0], "count": t[1]} for t in top_topics],
                "content_type_distribution": [{"type": c[0], "count": c[1]} for c in content_types]
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar estatísticas"
        )

@router.get("/power-words")
async def get_power_words(
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Retorna lista de power words categorizadas para uso em títulos.
    """
    try:
        power_words_categorized = {
            "urgencia": ["agora", "hoje", "rápido", "imediato", "urgente", "último", "final"],
            "numeros": ["top", "melhor", "pior", "primeiro", "único", "exclusivo", "segredo"],
            "emocional": ["incrível", "surpreendente", "chocante", "revolucionário", "épico", "fantástico"],
            "curiosidade": ["como", "por que", "o que", "quando", "onde", "quem", "qual", "segredo", "revelado"],
            "beneficios": ["grátis", "gratuito", "sem custo", "fácil", "simples", "rápido", "eficaz"],
            "negativos": ["erro", "problema", "falha", "mito", "mentira", "evitar", "nunca"],
            "sociais": ["todos", "ninguém", "maioria", "poucos", "expert", "profissional", "guru"]
        }
        
        return {
            "success": True,
            "power_words": power_words_categorized,
            "total_words": sum(len(words) for words in power_words_categorized.values()),
            "tip": "Use 1-3 power words por título para máximo impacto sem soar forçado"
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar power words: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@router.get("/templates")
async def get_title_templates(
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Retorna templates de títulos de alta conversão categorizados.
    """
    try:
        templates = {
            "tutorial": [
                "Como [fazer algo] em X [tempo/passos] (mesmo [obstáculo])",
                "O guia definitivo de [tópico] para [audiência]",
                "[Tópico] passo a passo: do zero ao [resultado]",
                "Como dominar [tópico] em [tempo] (método comprovado)"
            ],
            "lista": [
                "[Número] [coisas] que [resultado] (a maioria não sabe)",
                "Top [número] [tópico] para [benefício específico]",
                "[Número] erros de [tópico] que estão [sabotando resultado]",
                "[Número] segredos de [autoridade] sobre [tópico]"
            ],
            "curiosidade": [
                "O segredo de [autoridade] para [resultado] que [benefício]",
                "Por que [crença comum] está [sabotando] seu [objetivo]",
                "O que [grupo de sucesso] fazem diferente em [área]",
                "A verdade sobre [tópico] que [autoridade] não contam"
            ],
            "problema_solucao": [
                "Como resolver [problema] sem [obstáculo comum]",
                "A solução simples para [problema] que poucos conhecem",
                "Como parar de [problema] de uma vez por todas",
                "[Tópico]: a única coisa que você precisa para [resultado]"
            ],
            "social_proof": [
                "Como [número] pessoas conseguiram [resultado] com [método]",
                "O método que [grupo] usam para [resultado extraordinário]",
                "Por que [percentual]% das pessoas falham em [tópico] (e como não ser uma delas)",
                "Como [pessoa comum] conseguiu [resultado impressionante] em [tempo]"
            ]
        }
        
        return {
            "success": True,
            "templates": templates,
            "usage_tip": "Substitua as [variáveis] pelos seus conteúdos específicos",
            "best_practice": "Teste diferentes templates para ver qual funciona melhor com sua audiência"
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@router.get("/metrics")
async def get_title_metrics_info(
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Explica como são calculados os scores dos títulos.
    """
    try:
        metrics_info = {
            "engagement_score": {
                "description": "Mede o potencial de engajamento do título",
                "factors": [
                    "Power words utilizadas (+8 pontos cada)",
                    "Números no título (+10 pontos cada)",
                    "Perguntas diretas (+15 pontos)",
                    "Palavras de lista (coisas, formas, dicas) (+12 pontos)"
                ],
                "range": "0-100",
                "ideal": "70+"
            },
            "seo_score": {
                "description": "Mede a otimização para mecanismos de busca",
                "factors": [
                    "Comprimento ideal 50-60 caracteres (+20 pontos)",
                    "Keywords específicas (+8 pontos cada)",
                    "Estrutura com 4+ palavras (+15 pontos)"
                ],
                "range": "0-100",
                "ideal": "65+"
            },
            "trend_score": {
                "description": "Mede o alinhamento com tendências atuais",
                "factors": [
                    "Uso de trends identificadas (+15 pontos cada)",
                    "Bonus por incorporar trends (+25 pontos)"
                ],
                "range": "0-100",
                "ideal": "60+"
            },
            "overall_score": {
                "description": "Score geral ponderado",
                "calculation": "Engajamento (40%) + SEO (30%) + Trends (30%)",
                "range": "0-100",
                "ideal": "75+"
            }
        }
        
        return {
            "success": True,
            "metrics": metrics_info,
            "interpretation": {
                "90-100": "Título excepcional - alta probabilidade de viralização",
                "75-89": "Título muito bom - ótimo potencial",
                "60-74": "Título bom - pode ser melhorado",
                "40-59": "Título médio - precisa de otimização",
                "0-39": "Título fraco - requer reformulação completa"
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar métricas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@router.get("/trending-topics")
async def get_trending_topics(
    current_user: UserResponse = Depends(get_current_active_user),
    category: str = "geral"
):
    """
    Retorna tópicos em tendência para inspiração de títulos.
    """
    try:
        trending_topics = {
            "geral": [
                "inteligência artificial",
                "sustentabilidade",
                "trabalho remoto",
                "saúde mental",
                "educação online",
                "empreendedorismo digital",
                "investimentos",
                "tecnologia",
                "lifestyle",
                "produtividade"
            ],
            "tecnologia": [
                "ChatGPT",
                "Python",
                "desenvolvimento web",
                "machine learning",
                "blockchain",
                "cybersecurity",
                "cloud computing",
                "mobile development",
                "DevOps",
                "data science"
            ],
            "marketing": [
                "marketing digital",
                "redes sociais",
                "SEO",
                "content marketing",
                "influencer marketing",
                "email marketing",
                "conversão",
                "branding",
                "analytics",
                "growth hacking"
            ],
            "educacao": [
                "aprendizado online",
                "cursos digitais",
                "certificações",
                "skill development",
                "microlearning",
                "gamificação",
                "metodologias ativas",
                "educação corporativa",
                "autodidatismo",
                "coaching"
            ]
        }
        
        return {
            "success": True,
            "category": category,
            "trending_topics": trending_topics.get(category, trending_topics["geral"]),
            "available_categories": list(trending_topics.keys()),
            "last_updated": "2025-01-15",
            "tip": "Use estes tópicos como base e adicione seu ângulo único"
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar trending topics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@router.get("/title-ideas/{topic}")
async def get_title_ideas_for_topic(
    topic: str,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Gera ideias rápidas de títulos para um tópico específico.
    """
    try:
        if not topic or len(topic) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tópico deve ter pelo menos 2 caracteres"
            )
        
        quick_ideas = [
            f"Como dominar {topic} em 30 dias",
            f"5 segredos de {topic} que mudaram minha vida",
            f"Por que todo mundo deveria aprender {topic}",
            f"{topic} para iniciantes: guia completo",
            f"Os maiores erros em {topic} (e como evitar)",
            f"Como ganhar dinheiro com {topic}",
            f"{topic}: da teoria à prática",
            f"O futuro do {topic} em 2025",
            f"Como {topic} pode transformar sua carreira",
            f"Mitos sobre {topic} que você precisa parar de acreditar"
        ]
        
        return {
            "success": True,
            "topic": topic,
            "quick_ideas": quick_ideas,
            "note": "Estas são ideias básicas. Use o endpoint /generate para títulos otimizados com IA",
            "suggestion": f"Experimente diferentes ângulos: iniciante vs avançado, problema vs solução, etc."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar ideias para tópico: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )