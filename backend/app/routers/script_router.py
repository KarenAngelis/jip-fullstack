"""
app/routers/script_router.py

Rotas FastAPI para geração e análise de roteiros.

🔗 Dependências diretas:
- Usa a classe ScriptService (app/services/script_service.py).
  * Se alterar assinatura ou retorno de ScriptService.generate_script(),
    é necessário atualizar o modelo ScriptResponse/GeneratedScript/ScriptMetadata aqui.
  * Se alterar ScriptService.analyze_existing_script(), revisar ScriptAnalysis.
  * Se alterar variáveis de configuração (ex.: words_per_minute, cálculo de duração),
    as métricas retornadas (estimated_duration_minutes, accuracy, structure_score) 
    também podem mudar, exigindo ajuste nas rotas.
- Health check utiliza `script_service.client.chat.completions.create()`. 
  * Alterações na forma de instanciar o cliente OpenAI no ScriptService impactam aqui.

O que expõe:
- POST /generate-script  -> Gera roteiro profissional com timing e instruções técnicas.
- POST /analyze-script   -> Analisa um roteiro existente e retorna métricas/recomendações.
- GET  /script-templates -> Retorna templates/estruturas sugeridas e guia de timing.
- GET  /script-styles    -> Lista estilos disponíveis e guia de audiência.
- GET  /health           -> Health check simples (valida conexão com OpenAI).

Modelos (Pydantic):
- ScriptRequest: valida entrada (tópico, duração 1–60, objetivos, público-alvo, estilo, interações).
  * Validadores garantem valores permitidos para `target_audience` e `script_style`.
- ScriptMetadata / GeneratedScript / ScriptResponse: envelope da resposta de geração.
- AnalysisRequest: recebe texto do roteiro e duração alvo.
- ScriptAnalysis: métricas de análise (contagem de palavras, duração estimada, acurácia, estrutura, legibilidade, recomendações).

Fluxo de /generate-script:
1) Loga o pedido e instancia ScriptService.
2) Chama ScriptService.generate_script(...) passando:
   - topic, duration_minutes, objectives, audience (de target_audience),
     style (de script_style) e include_interactions.
3) Se `metadata.error` vier marcado, retorna HTTP 500.
4) Converte o dict retornado pelo serviço em modelos pydantic (GeneratedScript/ScriptMetadata)
   e responde com mensagem de sucesso + contagem de palavras.

Fluxo de /analyze-script:
1) Instancia ScriptService.
2) Chama ScriptService.analyze_existing_script(content, target_duration).
3) Constrói ScriptAnalysis com as métricas e recomendações.

Ligação com app/services/script_service.py:
- Este router é a “fachada” HTTP do ScriptService.
- Reutiliza diretamente:
  * generate_script(...) → produz conteúdo + `metadata` (word_accuracy, structure_score, etc.).
  * analyze_existing_script(...) → devolve o mesmo conjunto de métricas calculadas no serviço.
- As chaves e tipos de `metadata` aqui espelham o que ScriptService._analyze_script retorna
  (ex.: `estimated_duration_minutes`, `has_timestamps`, `has_interactions`, `model_used`).
- Depende indiretamente de OPENAI_API_KEY (usado dentro de ScriptService para criar o cliente OpenAI).

Health check:
- Cria ScriptService e faz uma chamada mínima ao modelo "gpt-4o-mini" via client.chat.completions
  para validar a conectividade com a OpenAI; em caso de falha, retorna status "degraded".

Observações:
- Erros de geração → HTTP 500; erros de análise → HTTP 400 (input inválido/erros internos capturados).
- As listas de `templates`, `styles` e `audience_guide` são estáticas e podem ser usadas pelo front-end
  para montar seletores; o guia de timing assume 165 palavras/min (regra central do ScriptService).
- Ajustes futuros: adicionar prefixo/versionamento de rota, autenticação, rate limiting e paginação de logs.

Exemplo (curl):
  curl -X POST http://localhost:8000/generate-script \
    -H "Content-Type: application/json" \
    -d '{
      "topic":"Kubernetes básico",
      "duration_minutes":8,
      "objectives":"Introduzir pods e deployments",
      "target_audience":"iniciantes",
      "script_style":"educativo",
      "include_interactions":true
    }'
"""

# app/routers/script_router.py
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator

from app.services.script_service import ScriptService

logger = logging.getLogger(__name__)
router = APIRouter()

class ScriptRequest(BaseModel):
    """Request para geração de roteiro"""
    topic: str = Field(..., min_length=5, max_length=200, description="Tópico do vídeo")
    duration_minutes: int = Field(10, ge=1, le=60, description="Duração em minutos")
    objectives: str = Field("", max_length=500, description="Objetivos específicos")
    target_audience: str = Field("geral", description="Audiência alvo")  
    script_style: str = Field("educativo", description="Estilo do roteiro")
    include_interactions: bool = Field(True, description="Incluir interações")
    
    @validator('target_audience')
    def validate_audience(cls, v):
        valid = ['geral', 'iniciantes', 'intermediários', 'avançados', 'profissionais', 'estudantes']
        if v not in valid:
            raise ValueError(f'target_audience deve ser: {valid}')
        return v
    
    @validator('script_style') 
    def validate_style(cls, v):
        valid = ['educativo', 'casual', 'formal', 'motivacional', 'tutorial']
        if v not in valid:
            raise ValueError(f'script_style deve ser: {valid}')
        return v

class ScriptMetadata(BaseModel):
    """Metadados do roteiro gerado"""
    topic: str
    target_duration_minutes: int
    estimated_duration_minutes: float
    target_words: int
    actual_words: int
    word_accuracy: int
    structure_score: int
    sections_found: int
    has_timestamps: bool
    has_interactions: bool
    readability_score: int
    model_used: str
    generation_timestamp: int

class GeneratedScript(BaseModel):
    """Roteiro gerado"""
    content: str
    score: int
    metadata: ScriptMetadata

class ScriptResponse(BaseModel):
    """Resposta da API"""
    success: bool
    message: str
    script: Optional[GeneratedScript] = None

class AnalysisRequest(BaseModel):
    """Request para análise de roteiro"""
    content: str = Field(..., min_length=100, description="Conteúdo do roteiro")
    target_duration: int = Field(10, ge=1, le=60, description="Duração alvo")

class ScriptAnalysis(BaseModel):
    """Análise de roteiro"""
    word_count: int
    estimated_duration: float
    target_duration: int
    accuracy_percentage: int
    structure_score: int
    readability_score: int
    sections_identified: int
    has_timestamps: bool
    has_interactions: bool
    recommendations: list[str]

@router.post("/generate-script", response_model=ScriptResponse)
async def generate_script(request: ScriptRequest):
    """
    Gera roteiro profissional com timing preciso
    
    Parâmetros:
    - **topic**: Tópico do vídeo (obrigatório)
    - **duration_minutes**: Duração em minutos (1-60)
    - **objectives**: Objetivos específicos (opcional)
    - **target_audience**: Audiência alvo (geral, iniciantes, etc.)
    - **script_style**: Estilo (educativo, casual, formal, etc.)
    - **include_interactions**: Incluir momentos de interação
    """
    
    try:
        logger.info(f"Gerando roteiro: {request.topic} ({request.duration_minutes}min)")
        
        script_service = ScriptService()
        
        result = script_service.generate_script(
            topic=request.topic,
            duration_minutes=request.duration_minutes,
            objectives=request.objectives,
            audience=request.target_audience,
            style=request.script_style,
            include_interactions=request.include_interactions
        )
        
        # Verifica se houve erro
        if result.get("metadata", {}).get("error"):
            raise HTTPException(
                status_code=500,
                detail=result["metadata"]["error_message"]
            )
        
        # Monta resposta
        script = GeneratedScript(
            content=result["content"],
            score=result["score"],
            metadata=ScriptMetadata(**result["metadata"])
        )
        
        return ScriptResponse(
            success=True,
            message=f"Roteiro gerado com sucesso ({result['metadata']['actual_words']} palavras)",
            script=script
        )
        
    except Exception as e:
        logger.error(f"Erro na geração: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )

@router.post("/analyze-script", response_model=ScriptAnalysis)
async def analyze_script(request: AnalysisRequest):
    """
    Analisa qualidade e métricas de um roteiro existente
    
    Útil para:
    - Verificar se roteiro está dentro do timing
    - Identificar pontos de melhoria
    - Calcular métricas de qualidade
    """
    
    try:
        script_service = ScriptService()
        
        analysis = script_service.analyze_existing_script(
            content=request.content,
            target_duration=request.target_duration
        )
        
        return ScriptAnalysis(**analysis)
        
    except Exception as e:
        logger.error(f"Erro na análise: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Erro na análise: {str(e)}"
        )

@router.get("/script-templates")
async def get_templates():
    """
    Retorna templates e estruturas de roteiro
    """
    
    return {
        "templates": {
            "educativo": {
                "name": "Educativo/Tutorial",
                "description": "Roteiro didático com foco em aprendizado",
                "duration_range": "5-20 minutos",
                "structure": [
                    "Hook: Problema ou curiosidade (10%)",
                    "Introdução: Contexto e overview (15%)",
                    "Conteúdo: 3-5 pontos principais (65%)",
                    "Conclusão: Resumo e próximos passos (10%)"
                ],
                "best_for": ["Tutoriais", "Explicações", "Cursos online"],
                "example_topic": "Como usar useState no React"
            },
            "motivacional": {
                "name": "Motivacional/Inspirador", 
                "description": "Roteiro focado em inspiração e transformação",
                "duration_range": "8-15 minutos",
                "structure": [
                    "Hook: História pessoal impactante",
                    "Problema: Situação atual e obstáculos", 
                    "Solução: Mindset e estratégias",
                    "Ação: Chamada para mudança"
                ],
                "best_for": ["Palestras", "Desenvolvimento pessoal", "Coaching"],
                "example_topic": "5 hábitos que mudaram minha produtividade"
            },
            "tutorial": {
                "name": "Tutorial Prático",
                "description": "Roteiro passo-a-passo muito prático",
                "duration_range": "10-30 minutos", 
                "structure": [
                    "Hook: Resultado final ou problema resolvido",
                    "Introdução: Pré-requisitos e ferramentas",
                    "Passos: Instruções detalhadas numeradas",
                    "Conclusão: Teste e próximos desafios"
                ],
                "best_for": ["How-to", "Demonstrações", "Projetos"],
                "example_topic": "Criando um site completo em 20 minutos"
            }
        },
        "timing_guide": {
            "1-3_minutes": "Vídeos curtos: 1 ponto principal, direto ao ponto",
            "5-10_minutes": "Padrão YouTube: 3-5 pontos, estrutura completa", 
            "15-30_minutes": "Conteúdo longo: múltiplos capítulos com timestamps",
            "30+_minutes": "Formato aula: módulos bem definidos"
        },
        "tips": [
            "Use 165 palavras por minuto para calcular timing",
            "Inclua pausas estratégicas a cada 2-3 minutos",
            "Marque transições claras entre seções",
            "Teste lendo em voz alta antes de gravar",
            "Prepare instruções técnicas para edição"
        ]
    }

@router.get("/script-styles")
async def get_styles():
    """
    Lista estilos disponíveis e suas características
    """
    
    return {
        "styles": {
            "educativo": {
                "name": "Educativo",
                "description": "Didático e estruturado para ensino",
                "tone": "Professoral mas acessível",
                "pace": "Moderado com pausas para absorção",
                "language": "Clara e explicativa",
                "best_for": ["Tutoriais", "Explicações conceituais", "Cursos"]
            },
            "casual": {
                "name": "Casual",
                "description": "Conversacional e descontraído",
                "tone": "Amigável e próximo",
                "pace": "Natural, como conversa entre amigos", 
                "language": "Coloquial com humor apropriado",
                "best_for": ["Vlogs", "Reviews pessoais", "Conversas"]
            },
            "formal": {
                "name": "Formal",
                "description": "Profissional e estruturado",
                "tone": "Autoridade e credibilidade",
                "pace": "Controlado e preciso",
                "language": "Técnica e profissional",
                "best_for": ["Apresentações", "Webinars", "Conteúdo corporativo"]
            },
            "motivacional": {
                "name": "Motivacional", 
                "description": "Inspirador e transformador",
                "tone": "Enérgico e envolvente",
                "pace": "Variado para criar ritmo",
                "language": "Emocional com storytelling",
                "best_for": ["Palestras", "Coaching", "Desenvolvimento pessoal"]
            },
            "tutorial": {
                "name": "Tutorial",
                "description": "Prático e instrucionall",
                "tone": "Paciente e didático",
                "pace": "Pausado para acompanhar execução",
                "language": "Instrucional passo-a-passo",
                "best_for": ["How-to", "Demonstrações", "Projetos práticos"]
            }
        },
        "audience_guide": {
            "geral": "Linguagem acessível, equilibra simplicidade e profundidade",
            "iniciantes": "Defina termos técnicos, construa conhecimento gradualmente",
            "intermediários": "Assume conhecimento básico, foque em aplicações",
            "avançados": "Use terminologia técnica, insights únicos e casos complexos", 
            "profissionais": "Direto ao ponto, foque em ROI e aplicabilidade",
            "estudantes": "Conecte com currículo, inclua referências acadêmicas"
        }
    }

@router.get("/health")
async def health_check():
    """Health check do serviço de roteiros"""
    
    try:
        # Testa se OpenAI está funcionando
        script_service = ScriptService()
        
        # Teste básico
        test_response = script_service.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "teste"}],
            max_tokens=1
        )
        
        return {
            "status": "healthy",
            "service": "script_generator",
            "openai_connection": "ok",
            "models_available": ["gpt-4o-mini"],
            "features": [
                "script_generation",
                "script_analysis", 
                "templates",
                "multiple_styles"
            ]
        }
        
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "service": "script_generator"
        }