"""
ContentGenerationRouter — Geração rápida, métricas locais e Google Trends (sem nulls)

Conexões rápidas
- service = ai_service.py   (gera conteúdo via OpenAI)
- metrics = metrics_service.py (métricas locais + Google Trends)
- schema  = content.py      (request/response dos endpoints)
- config  = ai_config.py    (modelos, thresholds e rate limits)

Resumo
- Foco em **velocidade** e **respostas limpas** (sem campos `null`).
- Para **títulos**: calcula métricas locais (engagement/SEO/tendência) e, opcionalmente, agrega **Google Trends**.
- Tenta **evitar múltiplas tentativas** para títulos (regeneração desativada por padrão para velocidade).
- Usa `response_model_exclude_*` e limpeza de metadados para remover chaves vazias.

Novos parâmetros (opcionais) no request
- `enrichWithTrends: bool = False` → adiciona estatísticas de Google Trends.
- `trendsGeo: str = "BR"` → região do Trends (ex.: US, BR, GB).

Principais endpoints
- POST /generate-content      → ContentGenerationResponse (metadados preenchidos e sem `null`)
- GET  /content-models        → Configs de modelos e limites
- POST /analyze-quality       → Avalia qualidade de um item específico
- GET  /recent-content        → Mock de histórico
- GET  /health                → Verificação de saúde da integração OpenAI
"""

from __future__ import annotations

import time
import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field, field_validator

from app.schemas.content import (
    ContentGenerationResponse,
    RecentContentResponse,
    MockRecentItem,
    GeneratedContentItem,
    ContentMetadata,
)
from app.services.ai_service import AIContentService
from app.services.ai_config import ai_config, ContentType, AIModel
from app.services.metrics_service import RealMetricsService
from app.dependencies.auth import get_current_active_user
from app.models.user_model import User

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiting simples (em produção use Redis)
request_history: Dict[str, List[float]] = {}


class AdvancedContentGenerationRequest(BaseModel):
    """Request avançado com validações adicionais (Pydantic v2)."""
    mainTopic: str = Field(..., min_length=3, max_length=200, description="Tópico principal")
    audience: Optional[str] = Field(None, description="Audiência alvo")
    contentType: Optional[str] = Field(None, description="Tipo de conteúdo (ou duração, conforme geração)")
    contentTone: Optional[str] = Field(None, description="Tom do conteúdo")
    generationType: str = Field(..., description="titulos | roteiros | episodios")
    model: Optional[str] = Field(AIModel.GPT4O_MINI.value, description="Modelo a ser usado")
    qualityThreshold: Optional[int] = Field(70, ge=0, le=100, description="Threshold mínimo de qualidade")
    regenerateIfBelowThreshold: bool = Field(True, description="Regenerar se abaixo do threshold")

    # novos
    enrichWithTrends: Optional[bool] = Field(False, description="Enriquecer com Google Trends")
    trendsGeo: Optional[str] = Field("BR", description="Região do Google Trends (ex.: BR, US)")

    @field_validator("generationType")
    @classmethod
    def _validate_generation_type(cls, v: str) -> str:
        valid = {"titulos", "roteiros", "episodios"}
        if v not in valid:
            raise ValueError(f"generationType deve ser um de: {sorted(valid)}")
        return v

    @field_validator("model")
    @classmethod
    def _validate_model(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in [m.value for m in AIModel]:
            raise ValueError(f"Modelo inválido. Use um de: {[m.value for m in AIModel]}")
        return v


class ContentQualityReport(BaseModel):
    """Relatório de qualidade do conteúdo gerado."""
    overall_score: int
    quality_passed: bool
    improvement_suggestions: List[str]
    strengths: List[str]
    weaknesses: List[str]
    regeneration_recommended: bool


def check_rate_limit(identifier: str = "global") -> bool:
    """Verificação simples de rate limiting (janela de 1h)."""
    current_time = time.time()

    if identifier not in request_history:
        request_history[identifier] = []

    # Remove requests mais antigos que 1 hora
    request_history[identifier] = [
        req_time for req_time in request_history[identifier]
        if current_time - req_time < 3600
    ]

    # Verifica limite (usa ai_config.rate_limits)
    try:
        limit = ai_config.rate_limits.requests_per_hour
    except Exception:
        limit = 100

    if len(request_history[identifier]) >= limit:
        return False

    request_history[identifier].append(current_time)
    return True


def analyze_content_quality(content_items: List[Dict[str, Any]]) -> ContentQualityReport:
    """Analisa qualidade do conteúdo gerado a partir de score/metadata."""
    if not content_items:
        return ContentQualityReport(
            overall_score=0,
            quality_passed=False,
            improvement_suggestions=["Nenhum conteúdo foi gerado"],
            strengths=[],
            weaknesses=["Falha na geração"],
            regeneration_recommended=True,
        )

    scores: List[int] = []
    all_metadata: List[Dict[str, Any]] = []

    for item in content_items:
        # normaliza qualquer float para int aqui também, por segurança
        scores.append(int(round(float(item.get("score", 0)))))
        if "metadata" in item and isinstance(item["metadata"], dict):
            all_metadata.append(item["metadata"])  

    overall_score = int(sum(scores) / len(scores)) if scores else 0

    strengths: List[str] = []
    weaknesses: List[str] = []
    suggestions: List[str] = []

    if overall_score >= 80:
        strengths.append("Excelente qualidade geral")
    elif overall_score >= 60:
        strengths.append("Qualidade adequada")
    else:
        weaknesses.append("Qualidade abaixo do esperado")
        suggestions.append("Considere refinar o tópico ou ajustar parâmetros")

    def _avg(key: str) -> float:
        return (
            sum(float(m.get(key, 0.0)) for m in all_metadata) / len(all_metadata)
            if all_metadata else 0.0
        )

    avg_engagement = _avg("engagement_potential")
    avg_seo = _avg("seo_score")
    avg_trend = _avg("trend_relevance")

    if avg_engagement < 60:
        weaknesses.append("Baixo potencial de engajamento")
        suggestions.append("Use mais números, perguntas ou palavras de impacto")
    elif avg_engagement > 80:
        strengths.append("Alto potencial de engajamento")

    if avg_seo < 50:
        weaknesses.append("SEO pode ser melhorado")
        suggestions.append("Inclua mais palavras-chave relevantes")
    elif avg_seo > 75:
        strengths.append("Bem otimizado para SEO")

    if avg_trend < 40:
        weaknesses.append("Baixa relevância para tendências atuais")
        suggestions.append("Considere temas mais atuais ou sazonais")
    elif avg_trend > 70:
        strengths.append("Muito relevante para tendências atuais")

    quality_passed = ai_config.is_quality_acceptable({
        "engagement_potential": avg_engagement,
        "seo_score": avg_seo,
        "trend_relevance": avg_trend,
    })

    return ContentQualityReport(
        overall_score=overall_score,
        quality_passed=quality_passed,
        improvement_suggestions=suggestions,
        strengths=strengths,
        weaknesses=weaknesses,
        regeneration_recommended=overall_score < 60,
    )


# ---------- helpers ----------

def _clean_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Remove chaves com None ou coleções vazias, preservando 0/False."""
    out = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, (list, dict)) and len(v) == 0:
            continue
        out[k] = v
    return out


# ----------------- ROUTES -----------------

@router.post(
    "/generate-content",
    response_model=ContentGenerationResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    response_model_exclude_defaults=True,
)
async def generate_content(
    request: AdvancedContentGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
):
    """Geração com análise local (+ opcional Google Trends) e resposta sem `null`."""

    # Rate limiting
    identifier = str(getattr(current_user, "id", "global"))
    if not check_rate_limit(identifier=identifier):
        raise HTTPException(
            status_code=429,
            detail="Limite de requisições excedido. Tente novamente em 1 hora.",
        )

    try:
        start_time = time.time()

        # Configuração do modelo baseada no tipo de conteúdo
        content_type_map = {
            "titulos": ContentType.TITLES,
            "roteiros": ContentType.SCRIPTS,
            "episodios": ContentType.EPISODES,
        }
        content_type = content_type_map.get(request.generationType, ContentType.TITLES)
        model_cfg = ai_config.get_model_config(content_type)
        model_to_use = request.model or model_cfg.primary_model.value

        ai_service = AIContentService(model=model_to_use)

        logger.info(
            f"[gen] tipo={request.generationType} topic='{request.mainTopic[:60]}...' model={model_to_use} user={getattr(current_user, 'email', 'unknown')}"
        )

        # Geração + tentativas
        raw_content: List[Dict[str, Any]] = []
        attempts = 0

        # SPEED: para TÍTULOS, evita loops longos (normalmente 1 tentativa é suficiente)
        if request.generationType == "titulos":
            max_attempts = 1 if not request.regenerateIfBelowThreshold else 1
        else:
            max_attempts = 3 if request.regenerateIfBelowThreshold else 1

        while attempts < max_attempts:
            attempts += 1
            try:
                if request.generationType == "titulos":
                    raw_content = ai_service.generate_titles(
                        topic=request.mainTopic,
                        audience=request.audience or "",
                        content_type=request.contentType or "",
                        tone=request.contentTone or "",
                        model=model_to_use,
                    )
                elif request.generationType == "roteiros":
                    raw_content = ai_service.generate_script(
                        topic=request.mainTopic,
                        duration=request.contentType or "10",
                        description=request.audience or "",
                        model=model_to_use,
                    )
                elif request.generationType == "episodios":
                    raw_content = ai_service.generate_episode(
                        title=request.mainTopic,
                        series_type=request.contentType or "",
                        episode_number=request.audience or "1",
                        model=model_to_use,
                    )

                # para títulos vamos sempre aceitar a 1ª geração (enriquecemos localmente)
                if request.generationType == "titulos":
                    break

                # para roteiros/episódios, aplica threshold se houver múltiplas tentativas
                quality_report = analyze_content_quality(raw_content)
                if quality_report.overall_score >= (request.qualityThreshold or 70) or attempts >= max_attempts:
                    break
                logger.warning(
                    f"[gen] tentativa={attempts} score={quality_report.overall_score} < threshold={request.qualityThreshold}. Regenerando..."
                )
            except Exception as e:
                logger.error(f"[gen] erro na tentativa {attempts}: {e}")
                if attempts >= max_attempts:
                    raise
                continue

        # Enriquecimento de METADADOS (local + opcional Trends)
        metrics = RealMetricsService(trends_geo=request.trendsGeo or "BR", trends_lang="pt-BR")

        generated_items: List[GeneratedContentItem] = []
        for item in raw_content:
            md = (item.get("metadata", {}) or {}).copy()

            if request.generationType == "titulos":
                if request.enrichWithTrends:
                    enriched = metrics.enrich_title_with_trends(
                        title=item["content"], topic=request.mainTopic, geo=request.trendsGeo or "BR"
                    )
                else:
                    enriched = metrics.analyze_title_all(title=item["content"], topic=request.mainTopic)

                # Mescla apenas o que estiver vazio/ausente
                for k, v in enriched.items():
                    if md.get(k) in (None, "", [], {}):
                        md[k] = v

            # Metadados padrão do pipeline
            md.update(
                {
                    "generation_time": round(time.time() - start_time, 2),
                    "model_used": model_to_use,
                    "generation_attempts": attempts,
                    "request_timestamp": int(time.time()),
                }
            )

            metadata_clean = _clean_dict(md)

            generated_items.append(
                GeneratedContentItem(
                    content=item["content"],
                    score=int(round(float(item.get("score", 0)))),
                    metadata=ContentMetadata(**metadata_clean),
                )
            )

        # Análise final sobre os itens normalizados (para score médio real)
        raw_for_quality = [
            {"score": gi.score, "metadata": (gi.metadata.model_dump() if gi.metadata else {})}
            for gi in generated_items
        ]
        final_quality = analyze_content_quality(raw_for_quality)

        generation_time = time.time() - start_time
        logger.info(
            f"[gen] concluído em {generation_time:.2f}s • score_médio={final_quality.overall_score} • itens={len(generated_items)}"
        )

        message = f"{len(generated_items)} item(s) gerado(s)"
        if not final_quality.quality_passed:
            message += f" (Qualidade: {final_quality.overall_score}/100 - Abaixo do threshold)"

        return ContentGenerationResponse(success=True, message=message, data=generated_items)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[gen] erro: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Erro interno na geração de conteúdo",
                "details": str(e),
                "suggestion": "Tente novamente com parâmetros diferentes",
            },
        )


@router.get(
    "/content-models",
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
)
async def get_available_models(current_user: User = Depends(get_current_active_user)):
    """Lista modelos disponíveis e suas configurações atuais."""
    return {
        "available_models": [model.value for model in AIModel],
        "model_configs": {ct.value: cfg.model_dump() for ct, cfg in ai_config.model_configs.items()},
        "quality_thresholds": ai_config.quality_thresholds,
        "rate_limits": ai_config.rate_limits.model_dump(),
    }


@router.post(
    "/analyze-quality",
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
)
async def analyze_content_quality_endpoint(content: Dict[str, Any], current_user: User = Depends(get_current_active_user)):
    """Endpoint para analisar a qualidade de um item de conteúdo específico."""
    try:
        quality_report = analyze_content_quality([content])
        return quality_report.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/recent-content",
    response_model=RecentContentResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
)
async def get_recent_content(current_user: User = Depends(get_current_active_user)):
    """Retorna dados mock de conteúdo recente (com métricas ilustrativas)."""
    mock_data = [
        MockRecentItem(
            id="1",
            type="titulo",
            title="10 React Hooks Que Mudaram Minha Carreira",
            content="Descubra os hooks mais poderosos do React que todo desenvolvedor precisa dominar...",
            score=4.2,
            status="Aprovado",
            date="08/01/2024",
            description="Gerado com GPT-4o-mini • Engagement: 87/100 • SEO: 79/100",
        ),
        MockRecentItem(
            id="2",
            type="roteiro",
            title="TypeScript Para Iniciantes",
            content="[0:00-0:15] HOOK: Você está perdendo oportunidades incríveis por não saber TypeScript...",
            score=3.8,
            status="Rascunho",
            date="08/01/2024",
            description="Roteiro 15min • 2,400 palavras • Estrutura completa",
        ),
        MockRecentItem(
            id="3",
            type="script",
            title="Como Criar Uma Startup Tech",
            content="ESTRUTURA EXECUTIVA: Este episódio #1 da série 'Empreendedorismo Tech' oferece um roadmap...",
            score=4.6,
            status="Aprovado",
            date="07/01/2024",
            description="Episódio completo • 8 seções • Recursos inclusos",
        ),
    ]

    return RecentContentResponse(
        success=True,
        message="Histórico com dados de qualidade",
        data=mock_data,
    )


@router.get(
    "/health",
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
)
async def health_check(current_user: User = Depends(get_current_active_user)):
    """Health check com ping no OpenAI e status local de configuração."""
    try:
        ai_service = AIContentService()
        test_start = time.time()
        _ = ai_service.client.chat.completions.create(
            model=ai_config.get_model_config(ContentType.TITLES).primary_model.value,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        response_time = time.time() - test_start
        return {
            "status": "healthy",
            "openai_connection": "ok",
            "response_time_ms": round(response_time * 1000),
            "available_models": [model.value for model in AIModel],
            "rate_limits_active": True,
            "quality_checks_active": True,
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e), "openai_connection": "failed"}


# Placeholders para compatibilidade com o frontend (proteger se necessário)
@router.post(
    "/save-content",
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
)
async def save_content(current_user: User = Depends(get_current_active_user)):
    return {"success": True, "message": "Função de persistência será implementada com banco Neon"}


@router.delete(
    "/content/{content_id}",
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
)
async def delete_content(content_id: str, current_user: User = Depends(get_current_active_user)):
    return {"success": True, "message": "Função de exclusão será implementada com banco Neon"}
