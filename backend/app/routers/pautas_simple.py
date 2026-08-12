# app/routers/pautas_simple.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import os
from datetime import datetime

# DB & Model
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.pauta import Pauta

# 🔐 Auth (iguais aos que você já usa em outros routers)
from app.dependencies.auth import get_current_active_user
from app.models.user_model import User

from app.services.content_services import (
    NewsService,
    TrendsService,
    AIContentGenerator,
)

router = APIRouter()

# -------------------------
# Schemas
# -------------------------
class PautaRequestSimple(BaseModel):
    tema: str
    duracao_desejada: Optional[int] = 15

class ArtigoRef(BaseModel):
    titulo: str
    fonte: str
    data: str
    url: str
    resumo: str
    confiabilidade: str

class TrendsDetalhadas(BaseModel):
    keywords: List[str]
    volume_busca_mensal: int
    crescimento_30_dias: str
    tendencia: str
    popularidade_score: int
    pico_interesse: str
    previsao_proximo_mes: str
    interesse_regional: Dict[str, int]

class DeepResearch(BaseModel):
    validacao: List[str]

class RoteiroEstruturado(BaseModel):
    abertura: str
    bloco_1: str
    bloco_2: str
    bloco_3: str
    bloco_4: str
    conclusao: str

class PautaResponseReal(BaseModel):
    tema: str
    duracao_min: int
    resumo_executivo: List[str]
    titulos_sugeridos: List[str]
    perguntas_sugeridas: List[str]
    artigos_referencia: List[ArtigoRef]
    trends_detalhadas: TrendsDetalhadas
    deep_research: DeepResearch
    roteiro_estruturado: RoteiroEstruturado
    status: str

# -------------------------
# Helpers
# -------------------------
def _rank_and_dedup(noticias: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not noticias:
        return []
    seen, cleaned = set(), []
    for n in noticias:
        url = n.get("url")
        if url and url not in seen:
            seen.add(url)
            cleaned.append(n)
    cleaned.sort(key=lambda n: n.get("data", "") or "", reverse=True)
    return cleaned

async def _gen_questions(tema: str, tone: str = "educativo") -> List[str]:
    if not os.getenv("OPENAI_API_KEY"):
        return [
            f"O que mudou recentemente em {tema}?",
            f"Como as mudanças em {tema} impactam os estudantes?",
            f"Quais são os prazos e etapas mais importantes de {tema}?",
            f"Que erros comuns evitar ao se preparar para {tema}?",
            f"Quais recursos gratuitos ajudam na preparação para {tema}?",
        ]
    prompt = f"""Gere 5 perguntas objetivas para um episódio de 15 min sobre "{tema}".
Tom {tone}, pt-BR. Uma por linha."""
    txt = await AIContentGenerator._call_openai_gpt(prompt, 220)
    if not txt:
        return [
            f"O que mudou recentemente em {tema}?",
            f"Como as mudanças em {tema} impactam os estudantes?",
            f"Quais são os prazos e etapas mais importantes de {tema}?",
            f"Que erros comuns evitar ao se preparar para {tema}?",
            f"Quais recursos gratuitos ajudam na preparação para {tema}?",
        ]
    return [x.strip() for x in txt.splitlines() if x.strip()][:5]

async def _gen_deep_research(tema: str, artigos: List[Dict[str, Any]]) -> List[str]:
    base = [
        "Confirmar datas oficiais e cronograma em fonte primária (INEP/MEC).",
        "Comparar documento oficial recente vs. ano anterior para mudanças.",
        "Checar estatísticas em relatórios públicos.",
    ]
    if not os.getenv("OPENAI_API_KEY"):
        return base
    refs = "\n".join(f"- {a.get('titulo','')} ({a.get('fonte','')})" for a in artigos[:5])
    prompt = f"""Liste 5 checagens factuais para "{tema}" com foco em fontes primárias.
Considere:
{refs}"""
    txt = await AIContentGenerator._call_openai_gpt(prompt, 220)
    return [x.strip("- ").strip() for x in (txt or "").splitlines() if x.strip()] or base

async def _gen_roteiro(tema: str, duracao: int, tone: str = "educativo") -> Dict[str, str]:
    if not os.getenv("OPENAI_API_KEY"):
        return {
            "abertura": f"Por que {tema} importa agora; o que o ouvinte ganha em {duracao} min.",
            "bloco_1": "Dados oficiais e mudanças recentes.",
            "bloco_2": "Tendências de interesse e significado.",
            "bloco_3": "Impactos práticos (prazos, oportunidades).",
            "bloco_4": "Dicas rápidas e recursos úteis.",
            "conclusao": "3 pontos-chave e call-to-action.",
        }
    prompt = f"""Mini-roteiro para {duracao} min sobre "{tema}" (Abertura, Bloco 1..4, Conclusão), tom {tone}, pt-BR.
Cada parte em 1-2 frases. Formato "Abertura: ...", etc."""
    txt = await AIContentGenerator._call_openai_gpt(prompt, 400)
    if not txt:
        return await _gen_roteiro(tema, duracao, tone="educativo")
    campos = {"abertura":"","bloco_1":"","bloco_2":"","bloco_3":"","bloco_4":"","conclusao":""}
    for line in txt.splitlines():
        l = line.strip()
        if not l: 
            continue
        low = l.lower()
        if low.startswith("abertura"): campos["abertura"] = l.split(":",1)[-1].strip() or l
        elif low.startswith("bloco 1"): campos["bloco_1"] = l.split(":",1)[-1].strip() or l
        elif low.startswith("bloco 2"): campos["bloco_2"] = l.split(":",1)[-1].strip() or l
        elif low.startswith("bloco 3"): campos["bloco_3"] = l.split(":",1)[-1].strip() or l
        elif low.startswith("bloco 4"): campos["bloco_4"] = l.split(":",1)[-1].strip() or l
        elif low.startswith("conclus"): campos["conclusao"] = l.split(":",1)[-1].strip() or l
    defaults = await _gen_roteiro(tema, duracao, tone="educativo") if any(v == "" for v in campos.values()) else {}
    for k, v in campos.items():
        if not v:
            campos[k] = defaults.get(k, v)
    return campos

def _gerar_resumo_do_titulo(titulo: str, tema: str) -> str:
    t = (titulo or "").lower()
    if "atualiza" in t: return f"Análise das mudanças e novidades mais recentes sobre {tema}."
    if "especialistas" in t: return f"Debate entre especialistas sobre {tema}, com diferentes perspectivas."
    if "tendên" in t or "tendenc" in t: return f"Principais tendências e direcionamentos futuros relacionados a {tema}."
    if "guia" in t: return f"Guia prático e atualizado sobre {tema}."
    if "novidades" in t: return f"Cobertura das mudanças e inovações mais recentes em {tema}."
    return f"Artigo informativo sobre {tema} com contexto atualizado."

# -------------------------
# Endpoints (com AUTH)
# -------------------------

@router.get("/api/pautas/")
def list_pautas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lista apenas as pautas do usuário autenticado (mais recentes primeiro)."""
    qs = (
        db.query(Pauta)
        .filter(Pauta.user_id == current_user.id)
        .order_by(Pauta.created_at.desc())
        .limit(50)
    )
    def _to_dict(p: Pauta):
        return {
            "id": p.id,
            "tema": p.tema,
            "duracao_min": p.duracao_min,
            "status": p.status,
            "resumo_executivo": p.resumo_executivo or [],
            "titulos_sugeridos": p.titulos_sugeridos or [],
            "perguntas_sugeridas": p.perguntas_sugeridas or [],
            "artigos_referencia": p.artigos_referencia or [],
            "trends_detalhadas": p.trends_detalhadas or {},
            "deep_research": p.deep_research or {},
            "roteiro_estruturado": p.roteiro_estruturado or {},
            "volume_busca_mensal": p.volume_busca_mensal,
            "popularidade_score": p.popularidade_score,
            "crescimento_30_dias": p.crescimento_30_dias,
            "tendencia": p.tendencia,
            "user_id": p.user_id,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
    items = [_to_dict(p) for p in qs.all()]
    return {"pautas": items, "total": len(items)}

@router.post("/api/pautas/generate", response_model=PautaResponseReal, status_code=status.HTTP_201_CREATED)
async def generate_pauta(
    request: PautaRequestSimple,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Gera pauta com dados reais coletados **e salva no banco** vinculada ao usuário autenticado."""
    # 1) Dados reais
    noticias_raw = await NewsService.collect_news(request.tema, "pt", 12)
    noticias = _rank_and_dedup(noticias_raw)
    trends_data = await TrendsService.collect_trends(request.tema, "BR")

    # 2) IA
    titles, questions, summary_text, validacoes, roteiro = await asyncio.gather(
        AIContentGenerator.gen_titles(request.tema, request.duracao_desejada, "educativo"),
        _gen_questions(request.tema, "educativo"),
        AIContentGenerator.gen_summary(request.tema, noticias, request.duracao_desejada, "educativo"),
        _gen_deep_research(request.tema, noticias),
        _gen_roteiro(request.tema, request.duracao_desejada, "educativo"),
    )

    # 3) Artigos
    artigos_ref: List[ArtigoRef] = []
    for a in noticias[:5]:
        artigos_ref.append(ArtigoRef(
            titulo=a.get("titulo",""),
            fonte=a.get("fonte","") or "Google News",
            data=a.get("data",""),
            url=a.get("url",""),
            resumo=_gerar_resumo_do_titulo(a.get("titulo",""), request.tema),
            confiabilidade=a.get("confianca","médio"),
        ))
    if not artigos_ref:
        artigos_ref.append(ArtigoRef(
            titulo=f"Busca atualizada sobre {request.tema}",
            fonte="Google News",
            data=datetime.now().strftime("%Y-%m-%d"),
            url=f"https://news.google.com/search?q={request.tema.replace(' ', '+')}&hl=pt",
            resumo=f"Coleta geral de notícias recentes sobre {request.tema}.",
            confiabilidade="médio",
        ))

    # 4) Resumo executivo e trends
    metrics = trends_data.get("metrics", {}) if isinstance(trends_data, dict) else {}
    growth = trends_data.get("growth", {}) if isinstance(trends_data, dict) else {}
    volume_busca_mensal = int((metrics.get("volume_busca_mensal") or metrics.get("volume_busca_atual") or metrics.get("interesse_atual") or 0))
    fontes_count = len(artigos_ref)

    resumo_executivo = [
        f"Tema '{request.tema}' com dados atualizados de {fontes_count} fontes jornalísticas",
        f"Volume de buscas: {volume_busca_mensal:,} pesquisas/mês",
        f"Formato otimizado para {request.duracao_desejada} minutos",
        f"Tendência: {growth.get('tendencia','estável')} nos últimos 30 dias",
    ]
    if summary_text:
        resumo_executivo.append(summary_text)

    trends_detalhadas = TrendsDetalhadas(
        keywords=trends_data.get("keywords", []),
        volume_busca_mensal=volume_busca_mensal,
        crescimento_30_dias=growth.get("crescimento_30_dias","0%"),
        tendencia=growth.get("tendencia","estável"),
        popularidade_score=int(metrics.get("popularidade_score") or metrics.get("interesse_atual") or 50),
        pico_interesse=growth.get("pico_interesse","últimos 30 dias"),
        previsao_proximo_mes=growth.get("previsao_proximo_mes","média"),
        interesse_regional=metrics.get("interesse_regional", {"BR": 100}),
    )

    deep_research = DeepResearch(validacao=validacoes[:5])
    roteiro_estruturado = RoteiroEstruturado(**roteiro)

    # 5) Persistência (com vinculação ao usuário)
    pauta_row = Pauta(
        tema=request.tema,
        duracao_min=request.duracao_desejada or 15,
        status="ativo",
        resumo_executivo=[*resumo_executivo],
        titulos_sugeridos=(titles or [])[:5],
        perguntas_sugeridas=(questions or [])[:5],
        artigos_referencia=[a.model_dump() for a in artigos_ref],
        trends_detalhadas=trends_detalhadas.model_dump(),
        deep_research=deep_research.model_dump(),
        roteiro_estruturado=roteiro_estruturado.model_dump(),
        volume_busca_mensal=volume_busca_mensal,
        popularidade_score=int(metrics.get("popularidade_score") or metrics.get("interesse_atual") or 50),
        crescimento_30_dias=float(str(growth.get("crescimento_30_dias","0")).replace("%","") or 0) if isinstance(growth.get("crescimento_30_dias"), (int,float,str)) else 0.0,
        tendencia=growth.get("tendencia","estável"),
        user_id=current_user.id,   # 🔐 aqui liga ao dono
    )
    db.add(pauta_row)
    db.commit()
    db.refresh(pauta_row)

    # 6) Resposta
    return PautaResponseReal(
        tema=pauta_row.tema,
        duracao_min=pauta_row.duracao_min,
        resumo_executivo=pauta_row.resumo_executivo or [],
        titulos_sugeridos=pauta_row.titulos_sugeridos or [],
        perguntas_sugeridas=pauta_row.perguntas_sugeridas or [],
        artigos_referencia=[ArtigoRef(**a) for a in (pauta_row.artigos_referencia or [])],
        trends_detalhadas=TrendsDetalhadas(**(pauta_row.trends_detalhadas or {})),
        deep_research=DeepResearch(**(pauta_row.deep_research or {})),
        roteiro_estruturado=RoteiroEstruturado(**(pauta_row.roteiro_estruturado or {})),
        status="gerado com dados reais, validação e roteiro estruturado",
    )

@router.get("/api/pautas/{pauta_id}")
def get_pauta_by_id(
    pauta_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retorna a pauta **somente se** pertencer ao usuário autenticado."""
    p = (
        db.query(Pauta)
        .filter(Pauta.id == pauta_id, Pauta.user_id == current_user.id)
        .first()
    )
    if not p:
        # não vaza se existe pauta de outro usuário
        raise HTTPException(status_code=404, detail="Pauta não encontrada")
    return {
        "id": p.id,
        "tema": p.tema,
        "duracao_min": p.duracao_min,
        "status": p.status,
        "resumo_executivo": p.resumo_executivo or [],
        "titulos_sugeridos": p.titulos_sugeridos or [],
        "perguntas_sugeridas": p.perguntas_sugeridas or [],
        "artigos_referencia": p.artigos_referencia or [],
        "trends_detalhadas": p.trends_detalhadas or {},
        "deep_research": p.deep_research or {},
        "roteiro_estruturado": p.roteiro_estruturado or {},
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }
