# app/schemas/episodes_schemas.py
"""
Schema para geração de episódios de podcast completos e vencedores.
Tudo é gerado pela IA com base no título fornecido.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from enum import Enum

class TipoSerie(str, Enum):
    """Tipos de série disponíveis"""
    MOTIVACIONAL = "motivacional"
    TUTORIAL = "tutorial"
    TENDENCIAS = "tendências"
    REVIEW = "review"
    NOTICIAS = "notícias"
    ENTRETENIMENTO = "entretenimento"
    EDUCATIVO = "educativo"
    LIFESTYLE = "lifestyle"
    BUSINESS = "business"
    TECNOLOGIA = "tecnologia"

class DificuldadeConteudo(str, Enum):
    """Nível de dificuldade do conteúdo"""
    INICIANTE = "iniciante"
    INTERMEDIARIO = "intermediário"
    AVANCADO = "avançado"
    EXPERT = "expert"

class FormatoEpisodio(str, Enum):
    """Formato do episódio"""
    SOLO = "solo"
    ENTREVISTA = "entrevista"
    PAINEL = "painel"
    NARRATIVO = "narrativo"
    TUTORIAL_PRATICO = "tutorial_prático"

# ==================== PESQUISA E DADOS (Reutilizando padrão das pautas) ====================

class FonteReferencia(BaseModel):
    """Fonte de referência encontrada pela IA"""
    titulo: str
    url: Optional[str] = None
    autor: Optional[str] = None
    data_publicacao: Optional[str] = None
    tipo: str  # artigo, vídeo, podcast, estudo, etc.
    relevancia_score: float = Field(ge=0.0, le=100.0)
    resumo: str
    citacao_sugerida: Optional[str] = None

class TrendAnalysis(BaseModel):
    """Análise de tendências do tópico"""
    keywords_principais: List[str]
    volume_busca_estimado: int
    tendencia_crescimento: str  # "crescendo", "estável", "declinando"
    sazonalidade: Optional[str] = None
    pico_interesse: Optional[str] = None
    interesse_regional: Dict[str, float] = {}
    oportunidade_score: float = Field(ge=0.0, le=100.0)

class CompetitorAnalysis(BaseModel):
    """Análise de concorrentes/similar content"""
    conteudos_similares: List[str]
    lacunas_identificadas: List[str]
    diferenciais_sugeridos: List[str]
    oportunidades_unicas: List[str]

class PesquisaCompleta(BaseModel):
    """Pesquisa completa gerada pela IA"""
    fontes_referencia: List[FonteReferencia]
    trend_analysis: TrendAnalysis
    competitor_analysis: CompetitorAnalysis
    fatos_verificados: List[str]
    estatisticas_relevantes: List[str]
    especialistas_sugeridos: List[str]
    confiabilidade_geral: float = Field(ge=0.0, le=100.0)

# ==================== CONTEÚDO ESTRUTURADO ====================

class GanchoAbertura(BaseModel):
    """Gancho de abertura do episódio"""
    tipo: str  # pergunta, estatística, história, problema, etc.
    conteudo: str
    tempo_estimado: int  # em segundos
    impacto_esperado: str  # alto, médio, baixo

class BlocoConteudo(BaseModel):
    """Bloco de conteúdo detalhado"""
    titulo: str
    subtopicos: List[str]
    conteudo_detalhado: str
    tempo_estimado_minutos: int
    elementos_especiais: List[str] = []  # [PAUSA], [MÚSICA], [INTERAÇÃO], etc.
    pontos_chave: List[str]
    transicao_proxima: str

class CallToAction(BaseModel):
    """Call to action específico"""
    tipo: str  # subscribe, share, comment, visit, buy, etc.
    texto: str
    posicionamento: str  # início, meio, fim
    urgencia: str  # alta, média, baixa
    expectativa_conversao: float = Field(ge=0.0, le=100.0)

class RoteiroCompleto(BaseModel):
    """Roteiro completo e detalhado"""
    gancho_abertura: GanchoAbertura
    introducao: str
    blocos_principais: List[BlocoConteudo]
    momentos_interacao: List[str]
    transicoes: List[str]
    conclusao_impactante: str
    calls_to_action: List[CallToAction]
    timing_detalhado: Dict[str, str]  # "00:00-00:30": "Gancho de abertura"

# ==================== PRODUÇÃO E ELEMENTOS TÉCNICOS ====================

class ElementosAudio(BaseModel):
    """Elementos de áudio e produção"""
    vinheta_abertura: str
    musica_fundo_sugerida: str
    efeitos_sonoros: List[str]
    pausas_dramaticas: List[str]
    volume_recomendado: Dict[str, int]  # música: 20, voz: 80, etc.
    qualidade_tecnica: Dict[str, str]

class EstruturaTemporal(BaseModel):
    """Estrutura temporal precisa"""
    tempo_total_segundos: int
    tempo_introducao: int
    tempo_desenvolvimento: int
    tempo_conclusao: int
    marcos_temporais: Dict[str, int]  # "primeiro_cta": 180, "climax": 600, etc.
    ritmo_sugerido: str  # rápido, moderado, contemplativo

# ==================== ESTRATÉGIA E OTIMIZAÇÃO ====================

class TargetAudience(BaseModel):
    """Audiência-alvo detalhada"""
    persona_principal: str
    faixa_etaria: str
    interesses: List[str]
    problemas_que_resolve: List[str]
    linguagem_recomendada: str
    referencias_culturais: List[str]

class SEOStrategy(BaseModel):
    """Estratégia de SEO e descobrimento"""
    titulo_otimizado: str
    descricao_otimizada: str
    keywords_principais: List[str]
    keywords_longtail: List[str]
    hashtags_estrategicas: List[str]
    categorias_plataformas: Dict[str, str]  # spotify: "Education", youtube: "How-to", etc.

class MetricasObjetivo(BaseModel):
    """Métricas e objetivos esperados"""
    engagement_esperado: float = Field(ge=0.0, le=100.0)
    retencao_esperada: float = Field(ge=0.0, le=100.0)
    compartilhamentos_meta: int
    comentarios_esperados: int
    conversao_cta_esperada: float = Field(ge=0.0, le=100.0)
    crescimento_audience: float = Field(ge=0.0, le=100.0)

class EstrategiaCompleta(BaseModel):
    """Estratégia completa do episódio"""
    target_audience: TargetAudience
    seo_strategy: SEOStrategy
    metricas_objetivo: MetricasObjetivo
    diferenciacao_mercado: List[str]
    proposta_valor_unica: str
    timing_publicacao: Dict[str, Any]

# ==================== REQUESTS E RESPONSES ====================

class EpisodeGenerateRequest(BaseModel):
    """Request minimalista - IA faz todo o resto"""
    titulo: str = Field(..., min_length=3, max_length=150, 
                       description="Título do episódio - a IA criará tudo baseado nisso")
    tipo_serie: TipoSerie = Field(default=TipoSerie.MOTIVACIONAL)
    numero_episodio: int = Field(default=1, ge=1, le=9999)
    duracao_desejada: int = Field(default=15, ge=5, le=180, 
                                description="Duração em minutos")
    
    # Opções avançadas (opcional)
    publico_alvo: Optional[str] = Field(None, description="Ex: 'empreendedores iniciantes'")
    tom_desejado: Optional[str] = Field(None, description="Ex: 'inspirador', 'técnico', 'casual'")
    incluir_dados_reais: bool = Field(default=True, description="Buscar dados reais vs. gerar tudo")
    formato_preferido: FormatoEpisodio = Field(default=FormatoEpisodio.SOLO)
    dificuldade: DificuldadeConteudo = Field(default=DificuldadeConteudo.INTERMEDIARIO)
    
    @validator('titulo')
    def validar_titulo(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Título não pode estar vazio")
        # Remove caracteres especiais problemáticos
        import re
        if not re.match(r'^[a-zA-Z0-9À-ÿ\s\-\.,!?()]+$', v):
            raise ValueError("Título contém caracteres inválidos")
        return v.strip()

class EpisodeVencedor(BaseModel):
    """Episódio completo e vencedor gerado pela IA"""
    
    # Identificação
    id: Optional[str] = None
    titulo: str
    tipo_serie: str
    numero_episodio: int
    formato: str
    dificuldade: str
    
    # Pesquisa e dados (gerados pela IA)
    pesquisa_completa: PesquisaCompleta
    
    # Conteúdo estruturado
    roteiro_completo: RoteiroCompleto
    
    # Produção
    elementos_audio: ElementosAudio
    estrutura_temporal: EstruturaTemporal
    
    # Estratégia
    estrategia_completa: EstrategiaCompleta
    
    # Metadados finais
    score_qualidade: float = Field(ge=0.0, le=100.0, description="Score de qualidade geral")
    pontos_fortes: List[str]
    areas_atencao: List[str]
    proximos_episodios_sugeridos: List[str]
    
    # Dados de geração
    tempo_geracao: float
    modelo_ia_usado: str
    tokens_utilizados: Optional[int] = None
    gerado_em: datetime = Field(default_factory=datetime.now)

class EpisodeGenerateResponse(BaseModel):
    """Response da geração"""
    success: bool
    episodio: Optional[EpisodeVencedor] = None
    message: str
    warnings: List[str] = []
    suggestions: List[str] = []

# ==================== TEMPLATES E UTILITÁRIOS ====================

class EpisodeTemplate(BaseModel):
    """Template pré-definido por tipo"""
    tipo: TipoSerie
    nome: str
    descricao: str
    estrutura_base: Dict[str, Any]
    elementos_obrigatorios: List[str]
    tempo_recomendado: int
    score_medio_esperado: float

class EpisodeAnalytics(BaseModel):
    """Analytics de performance (para usar depois)"""
    views_total: int = 0
    engagement_real: float = 0.0
    retention_media: float = 0.0
    comentarios: int = 0
    shares: int = 0
    conversao_cta: float = 0.0
    score_performance: float = Field(ge=0.0, le=100.0, default=0.0)

# ==================== RESPONSES DE LISTAGEM ====================

class EpisodeListItem(BaseModel):
    """Item da lista de episódios"""
    id: str
    titulo: str
    tipo_serie: str
    numero_episodio: int
    score_qualidade: float
    duracao_estimada: int
    gerado_em: datetime
    status: str = "draft"  # draft, published, archived

class EpisodeListResponse(BaseModel):
    """Response da listagem"""
    episodes: List[EpisodeListItem]
    total: int
    page: int = 1
    per_page: int = 10
    total_pages: int

# ==================== MODELOS DE BANCO ====================

class EpisodeDB(BaseModel):
    """Modelo para persistência no banco"""
    id: Optional[int] = None
    user_id: int
    titulo: str
    tipo_serie: str
    numero_episodio: int
    episodio_json: Dict[str, Any]  # JSON completo do EpisodeVencedor
    score_qualidade: float
    status: str = "draft"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None