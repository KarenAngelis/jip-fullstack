# app/services/ai_config.py

"""
AIConfig — Configuração central do serviço de IA

Conexões rápidas
- usado por: ai_service.py (para decidir modelo, temperature, max_tokens, etc)
- schemas/routers: não usam diretamente, mas se beneficiam indiretamente (modelos escolhidos aqui)

Resumo
- Define enums de modelos (AIModel) e tipos de conteúdo (ContentType).
- Centraliza configs de modelo (primário/fallback, temperatura, max_tokens, top_p) por tipo de conteúdo.
- Define thresholds de qualidade (mínimos de engagement, SEO, trend, overall).
- Define políticas de retry/fallback e limites de rate limiting.
- Inclui configuração de modelo de embeddings.

Principais métodos
- from_env() -> AIConfig
  * Constrói configuração global, sobrescrevendo valores via variáveis de ambiente.
- get_model_config(content_type) -> ModelConfig
  * Retorna configuração específica para TITLES / SCRIPTS / EPISODES.
- is_quality_acceptable(scores) -> bool
  * Valida se os scores atendem aos thresholds mínimos e ao overall ponderado.

Dependências/Config
- Variáveis de ambiente opcionais:
  * AI_PRIMARY_MODEL (aplica a todos os tipos)
  * AI_TITLES_MODEL / AI_SCRIPTS_MODEL / AI_EPISODES_MODEL (overrides por tipo)
  * AI_TEMPERATURE (override global)
  * OPENAI_EMBED_MODEL (modelo de embeddings)
- Exporta instância global `ai_config` para uso em outros módulos.
"""

import os
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

class AIModel(str, Enum):
    GPT4O_MINI = "gpt-4o-mini"
    GPT4O = "gpt-4o"
    GPT4_TURBO = "gpt-4-turbo"
    GPT35_TURBO = "gpt-3.5-turbo"

class ContentType(str, Enum):
    TITLES = "titulos"
    SCRIPTS = "roteiros"
    EPISODES = "episodios"

class ModelConfig(BaseModel):
    primary_model: AIModel
    fallback_model: AIModel
    temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = Field(gt=0)
    top_p: float = Field(gt=0.0, le=1.0)

class RetryConfig(BaseModel):
    max_retries: int = Field(ge=0, default=2)
    retry_delay: float = Field(ge=0.0, default=1.0)
    enable_fallback: bool = True

class RateLimits(BaseModel):
    requests_per_minute: int = Field(ge=0, default=20)
    requests_per_hour: int = Field(ge=0, default=100)
    requests_per_day: int = Field(ge=0, default=500)

class AIConfig(BaseModel):
    # Configs por tipo (usa default_factory p/ evitar mutável compartilhado)
    model_configs: Dict[ContentType, ModelConfig] = Field(default_factory=lambda: {
        ContentType.TITLES: ModelConfig(
            primary_model=AIModel.GPT4O_MINI, fallback_model=AIModel.GPT35_TURBO,
            temperature=0.7, max_tokens=1500, top_p=0.9
        ),
        ContentType.SCRIPTS: ModelConfig(
            primary_model=AIModel.GPT4O, fallback_model=AIModel.GPT4O_MINI,
            temperature=0.6, max_tokens=2500, top_p=0.8
        ),
        ContentType.EPISODES: ModelConfig(
            primary_model=AIModel.GPT4O, fallback_model=AIModel.GPT4O_MINI,
            temperature=0.5, max_tokens=2500, top_p=0.8
        ),
    })

    # métricas e thresholds
    quality_thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "min_engagement_score": 60.0,
        "min_seo_score": 50.0,
        "min_trend_score": 40.0,
        "min_overall_score": 70.0,
    })
    overall_weights: Dict[str, float] = Field(default_factory=lambda: {
        "engagement_potential": 0.4,
        "seo_score": 0.3,
        "trend_relevance": 0.3,
    })

    # retry e rate
    retry_config: RetryConfig = Field(default_factory=RetryConfig)
    rate_limits: RateLimits = Field(default_factory=RateLimits)

    # model de embeddings também faz parte do AIConfig
    embed_model: str = Field(default="text-embedding-3-small")

    @classmethod
    def from_env(cls) -> "AIConfig":
        cfg = cls()

        # Overrides globais
        primary_global = os.getenv("AI_PRIMARY_MODEL")
        if primary_global:
            # tenta mapear para Enum; se falhar, mantém original
            try:
                enum_val = AIModel(primary_global)
                for ct in ContentType:
                    mc = cfg.model_configs[ct].model_copy()
                    mc.primary_model = enum_val
                    cfg.model_configs[ct] = mc
            except ValueError:
                pass

        temp = os.getenv("AI_TEMPERATURE")
        if temp:
            t = float(temp)
            for ct in ContentType:
                mc = cfg.model_configs[ct].model_copy()
                mc.temperature = t
                cfg.model_configs[ct] = mc

        # Overrides por tipo (se existirem)
        per_type_env = {
            ContentType.TITLES: os.getenv("AI_TITLES_MODEL"),
            ContentType.SCRIPTS: os.getenv("AI_SCRIPTS_MODEL"),
            ContentType.EPISODES: os.getenv("AI_EPISODES_MODEL"),
        }
        for ct, val in per_type_env.items():
            if not val:
                continue
            try:
                enum_val = AIModel(val)
                mc = cfg.model_configs[ct].model_copy()
                mc.primary_model = enum_val
                cfg.model_configs[ct] = mc
            except ValueError:
                pass

        # Embed model
        cfg.embed_model = os.getenv("OPENAI_EMBED_MODEL", cfg.embed_model)

        return cfg

    def get_model_config(self, content_type: ContentType) -> ModelConfig:
        return self.model_configs.get(content_type, self.model_configs[ContentType.TITLES])

    def is_quality_acceptable(self, scores: Dict[str, float]) -> bool:
        """Verifica thresholds por métrica + overall ponderado."""
        eng = float(scores.get("engagement_potential", 0.0))
        seo = float(scores.get("seo_score", 0.0))
        trd = float(scores.get("trend_relevance", 0.0))

        # thresholds mínimos
        qt = self.quality_thresholds
        if not (eng >= qt["min_engagement_score"] and
                seo >= qt["min_seo_score"] and
                trd >= qt["min_trend_score"]):
            return False

        # overall ponderado
        w = self.overall_weights
        overall = (eng * w["engagement_potential"] +
                   seo * w["seo_score"] +
                   trd * w["trend_relevance"])
        return overall >= qt["min_overall_score"]

# instância global
ai_config = AIConfig.from_env()
