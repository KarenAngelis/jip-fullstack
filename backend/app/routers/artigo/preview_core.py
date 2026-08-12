from datetime import datetime
from typing import List, Dict, Tuple, Optional
import re
import hashlib
import uuid

# ================== Serviços externos (com fallbacks) ==================
try:
    from app.services.news_search import NewsSearchService
    from app.services.openai_service import OpenAIService  # Para insights via GPT
except Exception:
    # Fallback mínimo para ambiente de dev
    class NewsSearchService:  # type: ignore
        @staticmethod
        def search_news(tema: str, max_results: int = 3) -> List[Dict]:
            return []

    class OpenAIService:  # type: ignore
        @staticmethod
        def generate_insights(tema: str, score: int = 0, categoria: str = "geral") -> List[str]:
            return [
                "Insight gerado localmente (GPT indisponível)",
                "Use fontes confiáveis e dados atuais",
            ]

# ================== Configurações e Constantes ==================

TEMPORAL_TERMS = {
    "2025",
    "atual",
    "agora",
    "recente",
    "urgente",
    "crise",
    "cronograma",
    "inscrições",
}
TECH_TERMS = {
    "ia",
    "inteligência artificial",
    "ai",
    "machine learning",
    "tecnologia",
    "software",
    "dev",
}
ECON_TERMS = {"economia", "inflação", "juros", "finanças", "imposto", "impostos", "ir", "renda"}

SEASONAL_CONFIG = {
    "enem": {"months": [3, 4, 5, 6, 7, 8, 9, 10, 11], "score": 80, "label": "mar-nov", "bonus": 20},
    "vestibular": {"months": [3, 4, 5, 6, 7, 8, 9, 10, 11], "score": 75, "label": "mar-nov", "bonus": 20},
    "imposto": {"months": [3, 4, 5], "score": 85, "label": "mar-mai", "bonus": 18},
    "black friday": {"months": [10, 11], "score": 90, "label": "out-nov", "bonus": 25},
    "carnaval": {"months": [1, 2], "score": 70, "label": "jan-fev", "bonus": 15},
    "volta às aulas": {"months": [1, 2], "score": 65, "label": "jan-fev", "bonus": 12},
}

CATEGORIA_CONFIG = {
    "tecnologia": {"volume_base": 9000, "trend_base": 130, "bonus": 12},
    "financas": {"volume_base": 8000, "trend_base": 110, "bonus": 10},
    "educacao": {"volume_base": 10000, "trend_base": 90, "bonus": 8},
    "saude": {"volume_base": 8500, "trend_base": 95, "bonus": 9},
    "entretenimento": {"volume_base": 12000, "trend_base": 150, "bonus": 7},
    "geral": {"volume_base": 6000, "trend_base": 60, "bonus": 0},
}

# ================== Compliance (regras, extração e cálculo) ==================

LEGAL_PATTERNS = {
    # Padrões de leis/órgãos comuns
    "CDC": re.compile(r"\b(c[oó]digo\s+de\s+defesa\s+do\s+consumidor|cdc)\b", re.I),
    "CF": re.compile(r"\bconstitui[cç][aã]o\s*federal\b|\bart\.?\s*5[oº]\b", re.I),
    "ANVISA_RDC_44_2010": re.compile(r"\b(rdc|resolu[cç][aã]o)\s*n[ºo]?\s*44\s*/\s*2010\b", re.I),
    "LEI_5991_1973": re.compile(r"\blei\s*n[ºo]?\s*5\.?991\s*/\s*1973\b", re.I),
    "ARTIGO_NUM": re.compile(r"\bart\.?\s*\d+\b", re.I),
}

RISK_REGEX: Dict[str, Dict[str, List[re.Pattern[str]]]] = {
    # Saúde/farmacêutico
    "farmaceutico": {
        "high": [
            re.compile(r"\bsem\s+(receita|prescri[cç][aã]o)\b", re.I),
            re.compile(r"\bmedicamentos?\s+controlad[oa]s?.*sem\s+(receita|prescri[cç][aã]o)\b", re.I),
            re.compile(r"\bvenda(?:\s+de)?\s+medicamentos?.*sem\s+(receita|prescri[cç][aã]o)\b", re.I),
        ],
        "medium": [
            re.compile(r"\bpromove\s+cura\b", re.I),
            re.compile(r"\bresultados?\s+garantidos?\b", re.I),
        ],
    },
    # Genérico (publicidade enganosa/garantias)
    "geral": {
        "high": [
            re.compile(r"\bgarantia(s)?\b", re.I),
            re.compile(r"\bgarantido(s)?\b", re.I),
            re.compile(r"\bmilagre(s)?\b", re.I),
            re.compile(r"\bcura(s)?\b", re.I),
            re.compile(r"\bcerteza\b", re.I),
        ],
        "medium": [
            re.compile(r"\bretorno\s+garantido\b", re.I),
            re.compile(r"\blucro(s)?\b", re.I),
            re.compile(r"\bganho(s)?\b", re.I),
            re.compile(r"\b100%\s*seguro\b", re.I),
            re.compile(r"\bsem\s*riscos?\b", re.I),
        ],
    },
}


def extract_legal_citations(text: str) -> tuple[int, int, List[str]]:
    """Extrai citações legais do texto.

    Retorna (total_de_citacoes, fontes_distintas, lista_formatada).
    """
    citations: List[str] = []
    matched_sources: set[str] = set()
    total_refs = 0

    for key, pattern in LEGAL_PATTERNS.items():
        matches = list(pattern.finditer(text))
        if matches:
            matched_sources.add(key)
            total_refs += len(matches)
            snippet = matches[0].group(0)
            citations.append(f"{key.replace('_', ' ')}: {snippet}")

    return total_refs, len(matched_sources), citations


def assess_compliance(
    text: str,
    domain: Optional[str] = None,
    *,
    legal_refs: int = 0,
    evidence_sources: int = 0,
) -> Dict:
    """Avalia conformidade e calcula confiança de conformidade (0–1).

    - `status`: 'OK' ou 'WARNING'
    - `risk_level`: 'baixo' | 'médio' | 'alto'
    - `confidence`: 0–1 (quanto MAIOR, mais CONFORME)
    """
    x = text or ""
    dom = (domain or "geral").lower()
    rules = RISK_REGEX.get(dom, RISK_REGEX["geral"])

    # 1) Contagem de risco
    high_count = sum(1 for rx in rules["high"] if rx.search(x))
    med_count = sum(1 for rx in rules["medium"] if rx.search(x))

    # 2) Risco normalizado em [0,1)
    risk_raw = 1.0 * high_count + 0.5 * med_count
    k = 0.9
    risk_norm = 1.0 - (2.718281828 ** (-k * risk_raw))

    # 3) Veredito/nível
    issues: List[str] = []
    recs: List[str] = []
    if high_count > 0:
        status = "WARNING"
        risk_level = "alto"
        if dom in {"farmaceutico", "saude", "saúde"}:
            issues.append("Venda/alegação de medicamento sem receita/prescrição detectada")
            recs += [
                "Exigir e validar receita médica para medicamentos controlados",
                "Remover promessas absolutas/terapêuticas",
            ]
        else:
            issues.append("Termos de alto risco detectados (garantia/certeza/milagre/cura)")
            recs += ["Remover promessas absolutas", "Adicionar disclaimers"]
    elif med_count > 1:
        status = "WARNING"
        risk_level = "médio"
        issues.append("Múltiplas expressões de risco moderado (ex.: ganho/lucro/retorno garantido)")
        recs += ["Adicionar disclaimer apropriado", "Rever linguagem promocional"]
    else:
        status = "OK"
        risk_level = "baixo"
        recs.append("Conteúdo aprovado")

    # 4) Evidências legais (contagem + diversidade)
    evidence_norm = min(1.0, legal_refs / 3.0)
    diversity_bonus = min(0.1, max(0, evidence_sources - 1) * 0.03)

    # 5) Confiança de CONFORMIDADE
    conf = 0.6 * (1.0 - risk_norm) + 0.4 * evidence_norm + diversity_bonus
    if status == "WARNING":
        if legal_refs == 0:
            conf -= 0.25  # WARNING sem fontes ⇒ baixa confiança de conformidade
        elif legal_refs < 2:
            conf -= 0.10
    conf = max(0.05, min(0.98, conf))

    return {
        "status": status,
        "risk_level": risk_level,
        "confidence": round(conf, 2),
        "issues": issues,
        "recommendations": recs,
        "legal_refs": legal_refs,
        "evidence_sources": evidence_sources,
    }

# ================== Funções Core (tema/preview) ==================

def generate_unique_id(tema: str) -> str:
    """Gera ID único baseado no tema."""
    hash_obj = hashlib.md5(tema.encode())
    hash_hex = hash_obj.hexdigest()[:16]
    return f"{tema.lower().replace(' ', '-')[:20]}-{hash_hex}"


def detect_categoria(tema: str) -> str:
    """Detecta categoria do tema com heurísticas simples."""
    t = tema.lower()

    if any(k in t for k in TECH_TERMS):
        return "tecnologia"
    if any(k in t for k in ECON_TERMS):
        return "financas"
    if any(k in t for k in ["enem", "vestibular", "escola", "estudo", "educação", "educacao"]):
        return "educacao"
    if any(k in t for k in ["saúde", "saude", "medicina", "hospital", "vacina", "covid"]):
        return "saude"
    if any(k in t for k in ["filme", "série", "serie", "música", "musica", "netflix", "cinema"]):
        return "entretenimento"

    return "geral"


def calculate_seasonality(tema: str, now: datetime) -> Dict:
    """Calcula dados completos de sazonalidade."""
    t = tema.lower()

    for key, config in SEASONAL_CONFIG.items():
        if key in t:
            is_in_season = now.month in config["months"]
            return {
                "score": config["score"] if is_in_season else max(20, config["score"] - 40),
                "months": config["months"],
                "label": config["label"],
                "bonus": config["bonus"] if is_in_season else 0,
                "is_seasonal": True,
            }

    # Não sazonal
    return {
        "score": 40,
        "months": list(range(1, 13)),
        "label": "ano todo",
        "bonus": 0,
        "is_seasonal": False,
    }


def calculate_specificity_score(tema: str) -> int:
    """Calcula um score de especificidade do tema (0–20)."""
    words = [w for w in re.findall(r"\w+", tema) if len(w) > 2]
    word_count = len(words)

    specific_terms = len(
        [
            w
            for w in words
            if w.lower() in {"2025", "cronograma", "inscrição", "inscricoes", "resultado", "prazo"}
        ]
    )

    base_score = min(word_count * 3, 15)  # Máximo 15
    specific_bonus = specific_terms * 2

    return min(base_score + specific_bonus, 20)


def calculate_temporal_relevance(tema: str) -> int:
    """Calcula relevância temporal (0–20)."""
    t = tema.lower()
    score = 0

    if any(term in t for term in TEMPORAL_TERMS):
        score += 12
    if "2025" in t:
        score += 8

    return min(score, 20)


def calculate_difficulty_score(score: int, artigos: List[Dict], categoria: str) -> Tuple[str, int]:
    """Calcula nível e score de dificuldade de competição."""
    category_difficulty = {
        "tecnologia": 0.7,
        "financas": 0.6,
        "educacao": 0.4,
        "saude": 0.5,
        "entretenimento": 0.8,
        "geral": 0.5,
    }

    base_diff = category_difficulty.get(categoria, 0.5)
    news_factor = min(len(artigos) * 0.15, 0.3)  # Mais notícias => mais competição
    score_factor = (100 - score) / 200  # Score alto => menor dificuldade

    final_difficulty = base_diff + news_factor + score_factor
    difficulty_score = int(final_difficulty * 100)

    if difficulty_score >= 70:
        return "Hard", difficulty_score
    elif difficulty_score >= 50:
        return "Medium", difficulty_score
    else:
        return "Easy", difficulty_score


def extract_enhanced_keywords(tema: str, categoria: str) -> List[str]:
    """Extrai palavras-chave relevantes com base na categoria."""
    base_words = [w.lower() for w in re.findall(r"\w+", tema) if len(w) > 2]

    category_extras = {
        "educacao": ["inep", "redação", "redacao", "inscrição", "inscricao", "provas", "cronograma", "resultado"],
        "tecnologia": ["tendências", "tendencias", "framework", "roadmap", "inovação", "inovacao", "startup"],
        "financas": ["ipca", "selic", "investimento", "mercado", "economia"],
        "saude": ["sus", "anvisa", "tratamento", "prevenção", "prevencao", "sintomas"],
        "entretenimento": ["streaming", "lançamento", "lancamento", "crítica", "critica", "audiência", "audiencia"],
    }

    extras = category_extras.get(categoria, [])
    t = tema.lower()

    relevant_extras = [word for word in extras if any(base in t for base in word.split())]

    all_keywords = list(dict.fromkeys(base_words + relevant_extras))
    return all_keywords[:8]


def calculate_trend_growth(tema: str, categoria: str, now: datetime) -> int:
    """Calcula crescimento de tendência (em %)."""
    base_growth = CATEGORIA_CONFIG[categoria]["trend_base"]

    seasonality = calculate_seasonality(tema, now)
    seasonal_multiplier = 1.5 if seasonality["is_seasonal"] and seasonality["bonus"] > 0 else 1.0

    temporal_bonus = 1.3 if any(term in tema.lower() for term in TEMPORAL_TERMS) else 1.0

    final_growth = int(base_growth * seasonal_multiplier * temporal_bonus)
    return min(final_growth, 300)  # teto


def estimate_volume_enhanced(categoria: str, score: int, trend_pct: int) -> int:
    """Estima volume de busca com múltiplos fatores."""
    base_volume = CATEGORIA_CONFIG[categoria]["volume_base"]

    score_multiplier = 0.7 + (score / 100) * 0.6  # 0.7–1.3
    trend_multiplier = 1 + (trend_pct / 1000)  # +0.1x por 100%

    final_volume = int(base_volume * score_multiplier * trend_multiplier)
    return final_volume


def generate_badges(score: int, trend_pct: int, seasonality: Dict, difficulty: str) -> List[str]:
    """Gera badges com base nas métricas calculadas."""
    badges: List[str] = []

    if trend_pct >= 150:
        badges.append("🔥 Trending")
    elif trend_pct >= 100:
        badges.append("📈 Em alta")

    if seasonality["is_seasonal"] and seasonality["bonus"] > 0:
        badges.append("🗓️ Sazonal")

    if difficulty == "Easy":
        badges.append("🎯 Baixa competição")
    elif difficulty == "Hard":
        badges.append("⚡ Alta competição")

    if score >= 85:
        badges.append("⭐ Premium")

    return badges


def generate_insights_with_gpt(
    tema: str,
    score: int,
    categoria: str,
    seasonality: Dict,
    trend_pct: int,
    difficulty: str,
    use_gpt: bool = True,
) -> List[str]:
    """Gera insights (via GPT, se disponível) com fallback por regras."""
    insights: List[str] = []

    if use_gpt:
        try:
            # Algumas implementações usam assinatura (tema, score, categoria)
            gpt_insights = OpenAIService.generate_insights(tema, score, categoria)  # type: ignore[attr-defined]
            if isinstance(gpt_insights, list) and gpt_insights:
                insights.extend(gpt_insights[:3])
            else:
                use_gpt = False
        except TypeError:
            # Outras podem aceitar um contexto e max_insights
            try:
                context = {
                    "tema": tema,
                    "categoria": categoria,
                    "score": score,
                    "sazonalidade": seasonality["label"],
                    "trend_pct": trend_pct,
                    "dificuldade": difficulty,
                }
                gpt_insights = OpenAIService.generate_insights(context, max_insights=3)  # type: ignore[misc]
                if isinstance(gpt_insights, list) and gpt_insights:
                    insights.extend(gpt_insights[:3])
                else:
                    use_gpt = False
            except Exception:
                use_gpt = False
        except Exception:
            use_gpt = False

    if not use_gpt:
        # Fallback baseado em regras
        if seasonality["is_seasonal"] and seasonality["bonus"] > 0:
            insights.append(f"Sazonalidade alta no período {seasonality['label']}.")
        if trend_pct >= 150:
            insights.append(f"Crescimento explosivo de +{trend_pct}% nas últimas semanas.")
        elif trend_pct >= 100:
            insights.append(f"Tendência crescente com +{trend_pct}% de interesse.")
        if difficulty == "Easy":
            insights.append("Baixa dificuldade de competição para conteúdos introdutórios.")
        elif difficulty == "Hard":
            insights.append("Alta competição — exija conteúdo diferenciado.")
        if score >= 85:
            insights.append("Excelente potencial de engajamento e alcance.")

    return insights[:3]


def calculate_enhanced_score(tema: str, artigos: List[Dict], now: datetime) -> Tuple[int, Dict]:
    """Calcula score de viabilidade (0–100) com breakdown detalhado."""
    base = 50

    high_quality = sum(1 for a in artigos if a.get("confiabilidade") == "alto")
    medium_quality = sum(1 for a in artigos if a.get("confiabilidade") == "medio")
    total_articles = len(artigos)

    fontes_alta = high_quality * 15
    fontes_media = medium_quality * 8
    artigos_bonus = total_articles * 3

    especificidade = calculate_specificity_score(tema)
    relevancia_temporal = calculate_temporal_relevance(tema)

    seasonality = calculate_seasonality(tema, now)
    sazonalidade = seasonality["bonus"]

    categoria = detect_categoria(tema)
    categorias_bonus = CATEGORIA_CONFIG[categoria]["bonus"]

    total_score = base + fontes_alta + fontes_media + artigos_bonus + especificidade + relevancia_temporal + sazonalidade + categorias_bonus
    final_score = min(total_score, 100)

    breakdown = {
        "base": base,
        "fontes_alta": fontes_alta,
        "fontes_media": fontes_media,
        "artigos": artigos_bonus,
        "relevancia_temporal": relevancia_temporal,
        "especificidade": especificidade,
        "sazonalidade": sazonalidade,
        "categorias_bonus": categorias_bonus,
    }

    return final_score, breakdown

# ================== Função Principal ==================

def build_enhanced_preview_payload(
    tema: str,
    incluir_dados_tendencia: bool = True,
    duracao_minutos: int = 15,
    use_gpt_insights: bool = True,
) -> Dict:
    """Gera payload completo e detalhado do preview de pauta.

    Inclui bloco `compliance` com status, nível de risco, confiança (0–1) e fontes legais.
    """
    now = datetime.now()

    # 1) Busca notícias (opcional)
    artigos: List[Dict] = []
    if incluir_dados_tendencia:
        try:
            artigos = NewsSearchService.search_news(tema, max_results=5)
        except Exception as e:  # pragma: no cover
            print(f"Erro ao buscar notícias: {e}")

    # 2) Métricas principais
    score, breakdown = calculate_enhanced_score(tema, artigos, now)
    categoria = detect_categoria(tema)
    seasonality = calculate_seasonality(tema, now)
    trend_growth = calculate_trend_growth(tema, categoria, now)
    volume = estimate_volume_enhanced(categoria, score, trend_growth)
    difficulty, difficulty_score = calculate_difficulty_score(score, artigos, categoria)
    keywords = extract_enhanced_keywords(tema, categoria)
    badges = generate_badges(score, trend_growth, seasonality, difficulty)
    insights = generate_insights_with_gpt(
        tema, score, categoria, seasonality, trend_growth, difficulty, use_gpt_insights
    )

    # 3) Compliance (NOVO)
    # Monta um corpus simples com tema + títulos/descrições das notícias
    news_texts = []
    for a in artigos:
        for key in ("titulo", "title", "descricao", "description"):
            v = a.get(key)
            if isinstance(v, str) and v.strip():
                news_texts.append(v)
    corpus = " ".join([tema] + news_texts)

    # extrair citações legais
    legal_refs, evidence_sources, legal_citations = extract_legal_citations(corpus)
    domain = "farmaceutico" if categoria in {"saude"} else "geral"
    compliance = assess_compliance(
        text=corpus,
        domain=domain,
        legal_refs=legal_refs,
        evidence_sources=evidence_sources,
    )

    # 4) Recomendações de ação
    if score >= 85:
        recomendacao = "Tema excelente - gere pauta imediatamente!"
        cta_label = "🚀 Gerar pauta agora"
    elif score >= 65:
        recomendacao = "Tema viável - pode gerar boa pauta"
        cta_label = "📝 Gerar pauta completa"
    else:
        recomendacao = "Tema genérico - seja mais específico"
        cta_label = "🔍 Refinar tema"

    tempo_base = duracao_minutos
    complexidade_extra = len(keywords) + (5 if difficulty == "Hard" else 0)
    tempo_total = tempo_base + complexidade_extra

    # 5) Payload final
    return {
        "contract_version": "preview_v2",
        "id": generate_unique_id(tema),
        "generated_at": now.isoformat() + "Z",
        "tema": tema,
        "categoria": categoria,
        "viabilidade_score": score,
        "oportunidade": {
            "label": "Alta oportunidade"
            if score >= 85
            else "Boa oportunidade"
            if score >= 65
            else "Baixa oportunidade",
            "score_pct": round(score / 100, 2),
            "score": score,
        },
        "score_breakdown": breakdown,
        "trend_growth_pct": trend_growth,
        "volume_estimado": volume,
        "dificuldade": difficulty,
        "dificuldade_score": difficulty_score,
        "seasonality": seasonality,
        "palavras_chave": keywords,
        "insights": insights,
        "badges": badges,
        "noticias": {
            "has_news": len(artigos) > 0,
            "count": len(artigos),
            "items": artigos,
        },
        # ===== Bloco de compliance calculado =====
        "compliance": {
            "status": "Non Compliant" if compliance["status"] == "WARNING" else "Compliant",
            "risk_level": compliance["risk_level"].capitalize(),
            "confidence": compliance["confidence"],  # 0–1 (formate como % na UI)
            "fontes_legais": compliance["evidence_sources"],
            "legal_refs": compliance["legal_refs"],
            "issues": compliance["issues"],
            "recommendations": compliance["recommendations"],
            "citations": legal_citations,
            "domain": domain,
        },
        "tempo_estimado_preparo": f"{tempo_total} minutos",
        "proximos_passos": [
            "Gerar pauta completa",
            "Sistema buscará notícias atuais automaticamente"
            if incluir_dados_tendencia
            else "Pesquisar dados atuais",
            "Definir convidado (se necessário)"
            if categoria in ["tecnologia", "saude"]
            else "Preparar roteiro básico",
            "Preparar roteiro detalhado",
        ],
        "cta": {"label": cta_label, "endpoint": "/api/pautas/gerar"},
        "busca_noticias_ativa": incluir_dados_tendencia,
        "recomendacao": recomendacao,
    }


# ================== Função de Compatibilidade ==================

def build_preview_payload(tema: str, incluir_dados_tendencia: bool, duracao: int = 15) -> Dict:
    """Wrapper para compatibilidade com código existente."""
    return build_enhanced_preview_payload(tema, incluir_dados_tendencia, duracao)
