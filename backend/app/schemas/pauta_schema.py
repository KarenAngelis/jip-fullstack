# app/schemas/pauta_schema.py

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

class PautaRequest(BaseModel):
   """Schema para requisição de geração de pauta"""
   tema: str = Field(..., min_length=2, max_length=200, description="Tema principal da pauta")
   incluir_dados_tendencia: bool = Field(default=True, description="Incluir análise de tendências")
   tipo_episodio: Optional[str] = Field(default=None, description="Tipo: entrevista, solo, debate")
   duracao_desejada: Optional[int] = Field(default=15, ge=5, le=60, description="Duração em minutos")

class ArtigoInfo(BaseModel):
   """Informações de artigo/fonte com proveniência"""
   titulo: str = Field(..., description="Título do artigo")
   link: str = Field(..., description="URL do artigo")
   fonte: str = Field(..., description="Nome da fonte/veículo")
   resumo: str = Field(..., description="Resumo do conteúdo")
   data: str = Field(..., description="Data de publicação (YYYY-MM-DD)")
   confiabilidade: str = Field(..., description="Nível de confiabilidade: alto, medio, baixo")
   metodo: str = Field(..., description="Método de obtenção: trending_analysis, web_search, curadoria")
   
   @validator('confiabilidade')
   def validate_confiabilidade(cls, v):
       valid_values = ['alto', 'medio', 'baixo']
       if v not in valid_values:
           raise ValueError(f'Confiabilidade deve ser um de: {valid_values}')
       return v

class ArtigoRef(BaseModel):
   """Referência de artigo para router simples"""
   titulo: str
   fonte: str
   data: str
   url: str
   resumo: str
   confiabilidade: str

class AnguloEpisodio(BaseModel):
   """Ângulos possíveis para o episódio - formato normalizado"""
   tipo: str = Field(..., description="Tipo normalizado: introdutorio, tendencia, polemico, pratico, estudo_caso")
   titulo: str = Field(..., description="Título do ângulo")
   descricao: str = Field(..., description="Descrição detalhada")
   
   @validator('tipo')
   def validate_tipo(cls, v):
       valid_types = ['introdutorio', 'tendencia', 'polemico', 'pratico', 'estudo_caso']
       if v not in valid_types:
           raise ValueError(f'Tipo deve ser um de: {valid_types}')
       return v

class BlocoEstrutura(BaseModel):
   """Bloco da estrutura do episódio com duração precisa"""
   bloco: str = Field(..., description="Nome do bloco em snake_case")
   minutos: float = Field(..., ge=0.1, le=30.0, description="Duração em minutos (float)")
   descricao: str = Field(..., description="Descrição do conteúdo do bloco")

class PotencialViral(BaseModel):
   """Análise do potencial viral com scores normalizados"""
   score: int = Field(..., ge=0, le=100, description="Score de potencial viral (0-100)")
   fatores: List[str] = Field(..., min_items=1, description="Fatores que contribuem")

class MetricasEsperadas(BaseModel):
   """Métricas esperadas com valores normalizados"""
   retencao_estimada: float = Field(..., ge=0.0, le=1.0, description="Taxa de retenção (0.0-1.0)")
   compartilhamentos: float = Field(..., ge=0.0, le=1.0, description="Taxa de compartilhamento (0.0-1.0)")
   comentarios: float = Field(..., ge=0.0, le=1.0, description="Taxa de comentários (0.0-1.0)")

class DadosUtilizados(BaseModel):
   """Dados de tendência utilizados na análise"""
   volume_mencoes: int = Field(default=0, ge=0, description="Número de menções encontradas")
   engajamento_medio: float = Field(default=0.0, ge=0.0, le=1.0, description="Engagement médio (0.0-1.0)")
   termos_relacionados: List[str] = Field(default=[], description="Termos relacionados em alta")
   janela_temporal: str = Field(default="ultimos_7_dias", description="Período analisado")
   fontes_origem: List[str] = Field(default=[], description="Fontes dos dados")

class TrendsDetalhadas(BaseModel):
   """Dados detalhados de tendências de busca"""
   keywords: List[str] = Field(..., description="Palavras-chave relacionadas")
   volume_busca_mensal: int = Field(..., description="Volume de buscas por mês")
   crescimento_30_dias: str = Field(..., description="Percentual de crescimento em 30 dias")
   tendencia: str = Field(..., description="Direção da tendência: crescendo, declinando, estável")
   popularidade_score: int = Field(..., ge=0, le=100, description="Score de popularidade (0-100)")
   pico_interesse: str = Field(..., description="Período do pico de interesse")
   previsao_proximo_mes: str = Field(..., description="Previsão para próximo mês: alta, média, baixa")
   interesse_regional: Dict[str, int] = Field(..., description="Distribuição de interesse por região")

class DeepResearch(BaseModel):
   """Validação para pesquisa aprofundada"""
   validacao: List[str] = Field(..., description="Pontos de validação para pesquisa")

class RoteiroEstruturado(BaseModel):
   """Estrutura de roteiro para o episódio"""
   abertura: str = Field(..., description="Como começar o episódio")
   bloco_1: str = Field(..., description="Primeiro bloco de conteúdo")
   bloco_2: str = Field(..., description="Segundo bloco de conteúdo")
   bloco_3: str = Field(..., description="Terceiro bloco de conteúdo")
   bloco_4: str = Field(..., description="Quarto bloco de conteúdo")
   conclusao: str = Field(..., description="Como encerrar o episódio")

class EstrategiaPauta(BaseModel):
   """Seção estratégica da pauta - conteúdo para o roteirista"""
   resumo_executivo: List[str] = Field(..., min_items=3, max_items=5, description="3-5 bullets objetivos")
   topicos_chave: List[str] = Field(..., min_items=3, description="Palavras-chave e conceitos")
   angulos_episodio: List[AnguloEpisodio] = Field(..., min_items=3, max_items=5, description="Ângulos possíveis")
   perguntas_sugeridas: List[str] = Field(..., min_items=5, max_items=7, description="Perguntas estratégicas")
   estrutura_sugerida: List[BlocoEstrutura] = Field(..., min_items=3, description="Estrutura por blocos")
   titulos_sugeridos: List[str] = Field(..., min_items=5, max_items=5, description="Títulos SEO-friendly")
   hooks_abertura: List[str] = Field(..., min_items=3, max_items=3, description="Frases de abertura")
   cta_sugerido: str = Field(..., description="Chamada para ação específica")
   persona_tom: str = Field(..., description="Tom e personalidade sugeridos")
   publico_alvo: str = Field(..., description="Definição da audiência-alvo")

class AnalyticsPauta(BaseModel):
   """Seção de analytics - métricas e scores"""
   prioridade: int = Field(..., ge=0, le=100, description="Prioridade de produção (0-100)")
   potencial_viral: PotencialViral = Field(..., description="Análise de potencial viral")
   metricas_esperadas: MetricasEsperadas = Field(..., description="Métricas de performance")
   dados_utilizados: DadosUtilizados = Field(..., description="Dados de tendência")

class Proveniencia(BaseModel):
   """Seção de proveniência - rastreabilidade e fontes"""
   fonte_dados: List[str] = Field(..., description="Lista de fontes utilizadas")
   gerado_em: str = Field(..., description="Timestamp ISO 8601 de geração")
   versao_sistema: str = Field(..., description="Versão do sistema gerador")

class Producao(BaseModel):
   """Seção de produção - informações práticas"""
   duracao_total_prevista: float = Field(..., ge=5.0, le=60.0, description="Duração total em minutos")
   complexidade_preparo: str = Field(..., description="Complexidade: baixa, media, alta")
   recursos_necessarios: List[str] = Field(..., description="Recursos necessários para produção")
   urgencia_publicacao: str = Field(..., description="Urgência: baixa, media, alta, muito_alta")
   
   @validator('complexidade_preparo')
   def validate_complexidade(cls, v):
       valid_values = ['baixa', 'media', 'alta']
       if v not in valid_values:
           raise ValueError(f'Complexidade deve ser: {valid_values}')
       return v
   
   @validator('urgencia_publicacao')
   def validate_urgencia(cls, v):
       valid_values = ['baixa', 'media', 'alta', 'muito_alta']
       if v not in valid_values:
           raise ValueError(f'Urgência deve ser: {valid_values}')
       return v

# Schemas de resposta
class PautaResponse(BaseModel):
   """Schema completo da resposta estruturada da pauta"""
   tema: str = Field(..., description="Tema principal")
   hash_tema: str = Field(..., description="Hash MD5 do tema para cache")
   idioma: str = Field(..., description="Código do idioma (pt-BR)")
   regiao: str = Field(..., description="Código da região (BR)")
   
   estrategia: EstrategiaPauta = Field(..., description="Seção estratégica/conteúdo")
   analytics: AnalyticsPauta = Field(..., description="Seção de métricas/scores")
   proveniencia: Proveniencia = Field(..., description="Seção de rastreabilidade")
   producao: Producao = Field(..., description="Seção de informações de produção")
   
   @validator('idioma')
   def validate_idioma(cls, v):
       if v != 'pt-BR':
           raise ValueError('Idioma deve ser pt-BR')
       return v
   
   @validator('regiao')
   def validate_regiao(cls, v):
       if v != 'BR':
           raise ValueError('Região deve ser BR')
       return v

class PautaResponseReal(BaseModel):
   """Schema para resposta da API simples com dados reais"""
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

class PreviewPauta(BaseModel):
   """Preview rápido da pauta com scores de viabilidade"""
   tema: str = Field(..., description="Tema analisado")
   viabilidade_score: int = Field(..., ge=0, le=100, description="Score de viabilidade")
   dados_encontrados: Dict[str, Any] = Field(default={}, description="Dados de tendência")
   recomendacao: str = Field(..., description="Recomendação estratégica")
   proximos_passos: List[str] = Field(..., description="Próximas ações")
   tempo_estimado_preparo: str = Field(..., description="Tempo para preparar")

# Schema simples para requests
class PautaRequestSimple(BaseModel):
   """Schema simplificado para requests da API"""
   tema: str
   duracao_desejada: Optional[int] = 15