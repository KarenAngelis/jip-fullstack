# app/schemas/title_generation.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum

class AudienceType(str, Enum):
    INICIANTES = "iniciantes"
    INTERMEDIARIO = "intermediario"
    AVANCADO = "avancado"
    GERAL = "geral"

class ContentType(str, Enum):
    TUTORIAL = "tutorial"
    LISTA = "lista"
    GUIA = "guia"
    REVIEW = "review"
    COMPARACAO = "comparacao"
    NOTICIAS = "noticias"
    OPINIAO = "opiniao"

class ToneType(str, Enum):
    DIVERTIDO = "divertido"
    PROFISSIONAL = "profissional"
    CASUAL = "casual"
    INSPIRADOR = "inspirador"
    PROVOCATIVO = "provocativo"

class TitleGenerationRequest(BaseModel):
    topic: str = Field(..., description="Tópico principal do conteúdo")
    audience: AudienceType = Field(default=AudienceType.GERAL, description="Público-alvo")
    content_type: ContentType = Field(default=ContentType.TUTORIAL, description="Tipo de conteúdo")
    tone: ToneType = Field(default=ToneType.CASUAL, description="Tom do conteúdo")
    quantity: int = Field(default=5, ge=1, le=10, description="Quantidade de títulos a gerar")
    
    # Parâmetros avançados (opcionais, com defaults otimizados)
    use_trends: bool = Field(default=True, description="Usar trends atuais para otimização")
    include_numbers: bool = Field(default=True, description="Incluir números nos títulos")
    include_power_words: bool = Field(default=True, description="Usar palavras de poder")
    max_length: int = Field(default=60, ge=30, le=100, description="Tamanho máximo do título")

class TitleScore(BaseModel):
    engagement: int = Field(..., description="Score de engajamento (0-100)")
    seo: int = Field(..., description="Score de SEO (0-100)")
    trend: int = Field(..., description="Score de tendência (0-100)")
    overall: int = Field(..., description="Score geral (0-100)")

class GeneratedTitle(BaseModel):
    title: str = Field(..., description="Título gerado")
    scores: TitleScore = Field(..., description="Scores do título")
    trends_used: List[str] = Field(default=[], description="Trends utilizadas no título")
    power_words: List[str] = Field(default=[], description="Palavras de poder utilizadas")

class TitleGenerationResponse(BaseModel):
    success: bool = Field(default=True)
    titles: List[GeneratedTitle] = Field(..., description="Lista de títulos gerados")
    trends_found: List[str] = Field(default=[], description="Trends encontradas para o tópico")
    generation_time: float = Field(..., description="Tempo de geração em segundos")
    prompt_tokens: int = Field(default=0, description="Tokens utilizados no prompt")
    completion_tokens: int = Field(default=0, description="Tokens da resposta")

class TitleAnalysisRequest(BaseModel):
    title: str = Field(..., description="Título para análise")
    topic: Optional[str] = Field(None, description="Tópico relacionado (opcional)")

class TitleAnalysisResponse(BaseModel):
    success: bool = Field(default=True)
    title: str = Field(..., description="Título analisado")
    scores: TitleScore = Field(..., description="Scores detalhados")
    suggestions: List[str] = Field(default=[], description="Sugestões de melhoria")
    power_words_detected: List[str] = Field(default=[], description="Palavras de poder detectadas")
    length_analysis: dict = Field(default={}, description="Análise do comprimento")
    seo_keywords: List[str] = Field(default=[], description="Keywords SEO identificadas")