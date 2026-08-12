# app/routers/trends.py
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Any, Dict, List, Optional, Tuple
import asyncio
import logging
import time

from ..services.google_trends_service import GoogleTrendsService
from ..dependencies.auth import get_current_active_user
from ..schemas.auth_schema import UserResponse
from ..schemas.trends_schema import (
    TrendingTopic,
    ContentOpportunity,
    TrendAnalysisResult,
    TrendsSearchRequest,
    QuickTrendSummary,
    TrendsDashboard,
    TrendingPeriod,
    TrendMetrics,
    CompetitionLevel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trends", tags=["Google Trends"])

# =========================== Service singleton ===========================
_svc: Optional[GoogleTrendsService] = None
def _get_svc() -> GoogleTrendsService:
    global _svc
    if _svc is None:
        _svc = GoogleTrendsService()
    return _svc

# ============================== Timeouts otimizados =============================
FAST_TIMEOUT = 8
SLOW_TIMEOUT = 15

async def _with_timeout(coro, seconds: int, default):
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except Exception as e:
        logger.warning(f"Timeout após {seconds}s: {type(e).__name__}")
        return default

# ============================ Cache otimizado ==============================
CacheKey = Tuple[Any, ...]
_ANALYZE_CACHE: Dict[CacheKey, Tuple[float, Any]] = {}
ANALYZE_TTL = 60 * 30  # 30 minutos

def _cache_get(key: CacheKey):
    item = _ANALYZE_CACHE.get(key)
    if not item:
        return None
    exp, val = item
    if time.monotonic() > exp:
        _ANALYZE_CACHE.pop(key, None)
        return None
    return val

def _cache_set(key: CacheKey, value: Any):
    _ANALYZE_CACHE[key] = (time.monotonic() + ANALYZE_TTL, value)

# ============================== Helpers melhorados =================================
def _has_signal(ts: Dict[str, Any], kw: str) -> bool:
    pts = ts.get("interest_over_time") or []
    if not pts:
        return False
    total = sum(int(p.get(kw, 0)) for p in pts if p.get(kw))
    return total > 5

def _mk_enhanced_fallback_opp(keyword: str, ts: Dict[str, Any]) -> Dict[str, Any]:
    cur = ts.get("current_interest", 0) or 0
    peak = ts.get("peak_interest", 0) or 0
    avg = ts.get("average_interest", 0.0) or 0.0
    
    if peak >= 60 or avg >= 40:
        level = "media"
        roi = "Médio" 
        urgency = "alta"
        audience = "100K-500K pessoas"
    elif peak >= 30 or avg >= 20:
        level = "baixa"
        roi = "Médio"
        urgency = "media" 
        audience = "10K-100K pessoas"
    else:
        level = "muito_baixa"
        roi = "Baixo"
        urgency = "baixa"
        audience = "1K-10K pessoas"

    return {
        "keyword": keyword,
        "opportunity_type": "nicho_especifico",
        "market_analysis": {
            "current_interest": int(cur),
            "peak_interest": int(peak),
            "average_interest": float(avg),
            "growth_rate_12m": ts.get("growth_rate"),
            "demand_trend": "estavel" if avg > 0 else "baixa",
        },
        "competition_analysis": {"level": level},
        "content_angles": [
            f"Guia completo sobre {keyword}",
            f"Como usar {keyword} na prática",
            f"Erros comuns em {keyword}",
            f"{keyword}: dicas para iniciantes",
        ],
        "target_keywords": [],
        "content_types": ["artigo", "video", "tutorial"],
        "urgency_level": urgency,
        "best_channels": ["Blog", "YouTube", "Instagram"],
        "estimated_roi": roi,
        "target_personas": ["público geral", "iniciantes"],
        "audience_size": audience,
    }

def _normalize_opp_type(opp: Dict[str, Any]) -> None:
    otype = (opp.get("opportunity_type") or "").lower()
    if otype == "nicho":
        opp["opportunity_type"] = "nicho_especifico"
    elif otype in {"trending", "trending_topic"}:
        opp["opportunity_type"] = "trending"
    elif otype in {"alta", "alta_oportunidade"}:
        opp["opportunity_type"] = "viral"
    elif otype in {"viral"}:
        opp["opportunity_type"] = "viral"

def _to_int(x, default=0) -> int:
    try:
        if x is None: return default
        return int(float(str(x).replace(",", ".")))
    except Exception:
        return default

def _to_float(x, default=0.0) -> float:
    try:
        if x is None: return default
        return float(str(x).replace(",", "."))
    except Exception:
        return default

def _hydrate_overall_from_market(result: TrendAnalysisResult, opp: Dict[str, Any]) -> None:
    try:
        om = getattr(result, "overall_metrics", None)
        ma = (opp or {}).get("market_analysis", {}) or {}

        if isinstance(om, TrendMetrics):
            om_dump = om.model_dump()
        else:
            om_dump = om or {}

        zeros = (
            _to_int(om_dump.get("current_interest")) == 0
            and _to_int(om_dump.get("peak_interest")) == 0
            and _to_int(om_dump.get("average_interest")) == 0
        )

        if zeros:
            patch = {
                "current_interest": _to_int(ma.get("current_interest")),
                "peak_interest": _to_int(ma.get("peak_interest")),
                "average_interest": _to_float(ma.get("average_interest"), 0.0),
                "growth_rate": _to_float(ma.get("growth_rate_12m"), 0.0),
                "volatility": om_dump.get("volatility"),
                "trend_direction": om_dump.get("trend_direction") or "desconhecido",
            }

            if isinstance(om, TrendMetrics):
                result.overall_metrics = om.model_copy(update=patch)
            else:
                result.overall_metrics = patch
    except Exception:
        pass

# ============================= Endpoints ============================
@router.get("/test")
async def test_trends_service(current_user: UserResponse = Depends(get_current_active_user)):
    try:
        svc = _get_svc()
        items = await _with_timeout(
            svc.get_daily_trends(geo="BR", limit=3), 
            FAST_TIMEOUT, 
            []
        )
        return {
            "status": "ok",
            "count": len(items),
            "sample": [
                {"title": t.title, "category": t.category, "score": t.confidence_score}
                for t in items
            ],
        }
    except Exception as e:
        logger.exception("Falha no teste do TrendsService")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard", response_model=TrendsDashboard)
async def get_trends_dashboard(current_user: UserResponse = Depends(get_current_active_user)):
    try:
        svc = _get_svc()
        daily_task = _with_timeout(svc.get_daily_trends(geo="BR", limit=8), SLOW_TIMEOUT, [])
        opp_task = _with_timeout(svc.get_content_opportunities_quick(limit=6), SLOW_TIMEOUT, [])
        daily, opps = await asyncio.gather(daily_task, opp_task, return_exceptions=True)
        if isinstance(daily, Exception):
            daily = []
        if isinstance(opps, Exception):
            opps = []

        trending_now = [svc.to_quick_summary(t) for t in daily]
        opportunities = []
        for o in opps:
            level = (o.competition_analysis or {}).get("level")
            if isinstance(level, CompetitionLevel):
                level_val = level.value
            else:
                level_val = str(level or "")
            difficulty = "Médio" if level_val in {"media", "alta", "high", "very_high"} else "Fácil"
            opportunities.append(
                QuickTrendSummary(
                    topic=o.topic,
                    status="📈 Crescendo",
                    opportunity_score=75,
                    estimated_traffic=o.audience_size,
                    difficulty=difficulty,
                    best_action="Criar conteúdo",
                )
            )
        return TrendsDashboard(
            trending_now=trending_now,
            opportunities=opportunities,
            your_keywords=[],
            industry_insights={"last_updated": "real-time"},
        )
    except Exception:
        logger.exception("Erro no dashboard de trends")
        raise HTTPException(status_code=500, detail="Erro ao carregar dashboard")

@router.get("/daily", response_model=List[TrendingTopic])
async def get_daily_trends(
    geo: str = Query("BR", description="Código do país"),
    limit: int = Query(15, description="Limite de resultados", le=30),
    category: Optional[str] = Query(None, description="Filtro por categoria"),
    current_user: UserResponse = Depends(get_current_active_user),
):
    try:
        svc = _get_svc()
        items = await _with_timeout(
            svc.get_daily_trends(geo=geo, limit=limit), 
            SLOW_TIMEOUT, 
            []
        )
        if category:
            items = [t for t in items if (t.category or "").lower() == category.lower()]
        return items
    except Exception as e:
        logger.exception("Erro ao buscar tendências diárias")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze", response_model=TrendAnalysisResult)
async def analyze_trends(
    request: TrendsSearchRequest,
    current_user: UserResponse = Depends(get_current_active_user),
):
    if not request.keywords:
        raise HTTPException(status_code=400, detail="Envie ao menos 1 keyword")

    include_opportunities = getattr(request, "include_opportunities", True)
    include_predictions = getattr(request, "include_predictions", True)
    include_geo = getattr(request, "include_geo", True)
    include_related = getattr(request, "include_related", True)

    svc = _get_svc()
    main_kw = request.keywords[0]
    tf_val = request.timeframe.value if isinstance(request.timeframe, TrendingPeriod) else (request.timeframe or "today 12-m")
    geo_val = request.geo or "BR"

    cache_key = (
        tuple(request.keywords), tf_val, geo_val, request.category,
        include_opportunities, include_predictions, include_geo, include_related
    )
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.info(f"Cache hit para {main_kw}")
        return cached

    # série
    time_series = await _with_timeout(
        svc.get_interest_over_time(
            keywords=request.keywords,
            timeframe=tf_val,
            geo=geo_val,
            category=request.category,
        ),
        FAST_TIMEOUT,
        {"interest_over_time": []},
    )
    if not _has_signal(time_series, main_kw):
        time_series = await _with_timeout(
            svc.get_interest_over_time(
                keywords=request.keywords,
                timeframe="today 3-m",
                geo=geo_val,
                category=request.category,
            ),
            FAST_TIMEOUT,
            time_series,
        )

    # paralelos
    tasks = []
    if include_geo:
        tasks.append(_with_timeout(
            svc.get_geography_interest(
                keyword=main_kw, timeframe=tf_val, geo=geo_val, top_n=8
            ),
            FAST_TIMEOUT, []
        ))
    else:
        tasks.append(asyncio.sleep(0.01, result=[]))

    if include_related:
        tasks.append(_with_timeout(
            svc.get_related_topics(
                keyword=main_kw, timeframe=tf_val, geo=geo_val, top_n=4
            ),
            FAST_TIMEOUT, []
        ))
    else:
        tasks.append(asyncio.sleep(0.01, result=[]))

    if include_opportunities:
        tasks.append(_with_timeout(svc.analyze_content_opportunity(main_kw), FAST_TIMEOUT, {}))
    else:
        tasks.append(asyncio.sleep(0.01, result={}))

    geo_breakdown, related, opp_data = await asyncio.gather(*tasks, return_exceptions=True)
    if isinstance(geo_breakdown, Exception): geo_breakdown = []
    if isinstance(related, Exception): related = []
    if isinstance(opp_data, Exception): opp_data = {}

    if not opp_data or not opp_data.get("keyword"):
        opp_data = _mk_enhanced_fallback_opp(main_kw, time_series)
    _normalize_opp_type(opp_data)

    # monta resultado tipado
    result = await svc.build_trend_analysis_result(
        keyword=main_kw,
        interest_data=time_series,
        geo_data=geo_breakdown,
        related_data=related,
        opportunity_data=opp_data,
    )

    # === CORREÇÃO DO MERGE ===
    if not getattr(result, "opportunities", None):
        # cria a primeira oportunidade a partir do dict (faz mapeamento keyword->topic etc)
        result.opportunities = [svc._content_opp_from_dict(opp_data)]
    elif isinstance(result.opportunities, list) and result.opportunities:
        # Convertemos opp_data para modelo tipado primeiro:
        incoming = svc._content_opp_from_dict(opp_data)

        existing = result.opportunities[0]
        # Pydantic v2
        if hasattr(existing, "model_copy"):
            # Se você deseja que os valores EXISTENTES prevaleçam, faça update com exclude_none no incoming
            result.opportunities[0] = existing.model_copy(
                update=incoming.model_dump(exclude_unset=True, exclude_none=True)
            )
        else:
            # Pydantic v1 fallback
            result.opportunities[0] = existing.copy(
                update=incoming.dict(exclude_unset=True, exclude_none=True)
            )
    # === FIM CORREÇÃO ===

    _hydrate_overall_from_market(result, opp_data)

    if not include_predictions:
        result.future_predictions = None
        result.seasonal_patterns = None

    _cache_set(cache_key, result)
    return result

@router.get("/opportunities", response_model=List[ContentOpportunity])
async def get_content_opportunities(
    keywords: List[str] = Query(..., description="Palavras-chave para análise (max 3)"),
    industry: Optional[str] = Query(None, description="Setor/indústria (opcional)"),
    current_user: UserResponse = Depends(get_current_active_user),
):
    try:
        if len(keywords) > 3:
            keywords = keywords[:3]
        svc = _get_svc()
        tasks = [_with_timeout(svc.analyze_content_opportunity(kw), FAST_TIMEOUT, {}) for kw in keywords]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        opps: List[ContentOpportunity] = []
        for i, result_item in enumerate(results):
            if isinstance(result_item, Exception):
                logger.warning(f"Opp falhou para '{keywords[i]}': {type(result_item).__name__}")
                result_item = _mk_enhanced_fallback_opp(keywords[i], {"interest_over_time": []})
            if result_item and result_item.get("keyword"):
                _normalize_opp_type(result_item)
                opps.append(svc._content_opp_from_dict(result_item))
        return opps
    except Exception:
        logger.exception("Erro na análise de oportunidades")
        raise HTTPException(status_code=500, detail="Erro na análise de oportunidades")
