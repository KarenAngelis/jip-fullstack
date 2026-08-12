"""
AIContentService — Serviço para gerar conteúdo com OpenAI

Conexões rápidas
- router = content_generation.py   (usa esse service nos endpoints)
- schema = content.py              (define os contratos de entrada/saída)

Resumo (versão reescrita)
- Saídas 100% estruturadas em JSON e validadas com Pydantic (nada de regex frágil).
- "Score" calculado no backend com métricas reais (embeddings + regras objetivas),
  e não extraído/opinião do modelo.
- Modelos configuráveis via .env: OPENAI_MODEL, OPENAI_FALLBACK_MODEL, OPENAI_EMBED_MODEL.
- Geração de TÍTULOS, ROTEIROS e ESTRUTURAS DE EPISÓDIO com prompts que exigem JSON.

Principais métodos
- generate_titles(topic, audience?, content_type?, tone?) -> List[Dict]
  * Retorna até 5 itens { content, score(0-100), metadata{...} } com notas de relevância/SEO/originalidade.
- generate_script(topic, duration="10", description="") -> List[Dict]
  * Retorna roteiro estruturado por seções (hook, intro, etc.), tempos, key_points e métricas de qualidade.
- generate_episode(title, series_type?, episode_number="1") -> List[Dict]
  * Retorna plano de episódio com objetivos, pré-requisitos, timeline, recursos e métricas de completude.

Helpers
- _prompt_*_json(...): prompts que forçam o modelo a responder apenas JSON.
- _embed/_cosine: utilidades para embeddings e similaridade.
- _score_title/_score_script/_score_episode: cálculo local de métricas/score.
- _parse_duration/_estimate_speaking_time: utilidades de tempo de fala.

Dependências/Config
- Requer OPENAI_API_KEY no ambiente.
- Modelos padrão: OPENAI_MODEL=gpt-4o-mini | OPENAI_FALLBACK_MODEL=gpt-3.5-turbo | OPENAI_EMBED_MODEL=text-embedding-3-small
"""

from __future__ import annotations

import os
import json
import logging
import math
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# =========================
# Pydantic Schemas (saída)
# =========================
class TitleItem(BaseModel):
    title: str = Field(..., min_length=8, max_length=120)
    engagement_notes: str = ""
    seo_notes: str = ""
    trend_notes: str = ""

class TitleResponse(BaseModel):
    items: List[TitleItem] = Field(..., min_items=3, max_items=8)

class ScriptSection(BaseModel):
    name: str
    script: str
    key_points: List[str] = Field(default_factory=list)
    est_seconds: int = Field(..., ge=5, le=900)

class ScriptResponse(BaseModel):
    sections: List[ScriptSection] = Field(..., min_items=3)

class TimelineItem(BaseModel):
    minute: int
    segment: str
    goals: List[str] = Field(default_factory=list)
    engagement_points: List[str] = Field(default_factory=list)

class EpisodePlan(BaseModel):
    executive_summary: str
    objectives: List[str] = Field(..., min_items=3)
    prerequisites: List[str] = Field(default_factory=list)
    timeline: List[TimelineItem] = Field(..., min_items=3)
    resources: List[str] = Field(default_factory=list)
    key_takeaways: List[str] = Field(default_factory=list)
    connections: Dict[str, Any] = Field(default_factory=dict)  # {"previous":..., "next":...}
    success_metrics: List[str] = Field(default_factory=list)
    extras: List[str] = Field(default_factory=list)


# =========================
# Serviço principal
# =========================
class AIContentService:
    def __init__(self, model: Optional[str] = None):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.fallback_model = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-3.5-turbo")
        self.embed_model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    # ---------------
    # Public methods
    # ---------------
    def generate_titles(
        self,
        topic: str,
        audience: str = "",
        content_type: str = "",
        tone: str = "",
        model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Gera títulos (JSON+Pydantic) e calcula score real no backend."""
        model_to_use = model or self.model
        try:
            resp = self.client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": "Você é um especialista de marketing. Produza apenas JSON válido."},
                    {"role": "user", "content": self._prompt_titles_json(topic, audience, content_type, tone)},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
                max_tokens=1200,
            )
            data = json.loads(resp.choices[0].message.content)
            validated = TitleResponse(**data)

            brief = f"Tema: {topic}. Público: {audience}. Tipo: {content_type}. Tom: {tone}."
            out: List[Dict[str, Any]] = []
            for item in validated.items[:5]:
                m = self._score_title(item.title, brief, recent=[])
                out.append(
                    {
                        "content": item.title,
                        "score": m["score"],
                        "metadata": {
                            "relevance": m["relevance"],
                            "len_ok": m["len_ok"],
                            "has_number": m["has_number"],
                            "has_brackets": m["has_brackets"],
                            "starts_strong": m["starts_strong"],
                            "originality": m["originality"],
                            "engagement_analysis": item.engagement_notes,
                            "seo_analysis": item.seo_notes,
                            "trend_analysis": item.trend_notes,
                        },
                    }
                )
            return out
        except (ValidationError, json.JSONDecodeError) as ve:
            logger.error(f"[titles] JSON inválido: {ve}")
        except Exception as e:
            logger.error(f"[titles] Erro com {model_to_use}: {e}")

        if model_to_use != self.fallback_model:
            return self.generate_titles(topic, audience, content_type, tone, self.fallback_model)
        return []

    def generate_script(
        self,
        topic: str,
        duration: str = "10",
        description: str = "",
        model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Gera roteiro estruturado (JSON+Pydantic) e calcula métricas reais."""
        model_to_use = model or self.model
        minutes = self._parse_duration(duration)
        try:
            resp = self.client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": "Você é roteirista profissional. Responda apenas JSON válido."},
                    {"role": "user", "content": self._prompt_script_json(topic, minutes, description)},
                ],
                temperature=0.4,
                response_format={"type": "json_object"},
                max_tokens=2200,
            )
            data = json.loads(resp.choices[0].message.content)
            validated = ScriptResponse(**data)

            # montar texto consolidado e métricas
            full_text = "\n\n".join([s.script for s in validated.sections])
            word_count = len(full_text.split())
            speak = self._estimate_speaking_time(full_text)
            total_est = sum(s.est_seconds for s in validated.sections)
            timing_accuracy = self._timing_accuracy(total_est, minutes)

            # cobertura estrutural básica
            names = " ".join([s.name.lower() for s in validated.sections])
            has_hook = any("hook" in s.name.lower() for s in validated.sections) or "hook" in names
            has_intro = any("intro" in s.name.lower() for s in validated.sections) or "introdu" in names
            has_conclusion = any("conclus" in s.name.lower() for s in validated.sections)
            structure_coverage = sum([has_hook, has_intro, has_conclusion]) / 3

            # relevância vs brief
            brief = f"Roteiro para {minutes} minutos. Tema: {topic}. Objetivos: {description}."
            rel = self._relevance(full_text, brief)

            score = self._score_script(structure_coverage, timing_accuracy, rel)

            item = {
                "content": full_text.strip(),
                "score": score,
                "metadata": {
                    "word_count": word_count,
                    "estimated_duration_range": speak,  # min/max by WPM
                    "target_minutes": minutes,
                    "timeline_total_seconds": total_est,
                    "timing_accuracy": timing_accuracy,
                    "structure": {
                        "has_hook": has_hook,
                        "has_intro": has_intro,
                        "has_conclusion": has_conclusion,
                    },
                    "relevance": round(rel, 3),
                    "sections": [s.model_dump() for s in validated.sections],
                },
            }
            return [item]
        except (ValidationError, json.JSONDecodeError) as ve:
            logger.error(f"[script] JSON inválido: {ve}")
        except Exception as e:
            logger.error(f"[script] Erro com {model_to_use}: {e}")

        if model_to_use != self.fallback_model:
            return self.generate_script(topic, duration, description, self.fallback_model)
        return []

    def generate_episode(
        self,
        title: str,
        series_type: str = "",
        episode_number: str = "1",
        model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Gera plano de episódio (JSON+Pydantic) e calcula métricas reais."""
        model_to_use = model or self.model
        try:
            resp = self.client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": "Você é produtor de conteúdo sênior. Responda apenas JSON válido."},
                    {"role": "user", "content": self._prompt_episode_json(title, series_type, episode_number)},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
                max_tokens=2400,
            )
            data = json.loads(resp.choices[0].message.content)
            validated = EpisodePlan(**data)

            # métricas: completude de seções & detalhamento
            completeness = self._episode_completeness(validated)
            detail_words = sum(len(x.split()) for x in [
                validated.executive_summary,
                *validated.objectives,
                *validated.prerequisites,
                *[ti.segment for ti in validated.timeline],
                *validated.resources,
                *validated.key_takeaways,
                *validated.success_metrics,
                *validated.extras,
            ])
            detail_score = min(100, detail_words // 20)
            score = int(0.65 * completeness + 0.35 * detail_score)

            content_text = self._episode_as_text(validated)

            item = {
                "content": content_text.strip(),
                "score": score,
                "metadata": {
                    "episode_title": title,
                    "series_type": series_type,
                    "episode_number": episode_number,
                    "completeness_score": completeness,
                    "detail_score": detail_score,
                    "sections_found": self._episode_sections_found(validated),
                    "timeline_items": len(validated.timeline),
                    "word_count": len(content_text.split()),
                },
            }
            return [item]
        except (ValidationError, json.JSONDecodeError) as ve:
            logger.error(f"[episode] JSON inválido: {ve}")
        except Exception as e:
            logger.error(f"[episode] Erro com {model_to_use}: {e}")

        if model_to_use != self.fallback_model:
            return self.generate_episode(title, series_type, episode_number, self.fallback_model)
        return []

    # ---------------
    # Prompt builders
    # ---------------
    def _prompt_titles_json(self, topic: str, audience: str, content_type: str, tone: str) -> str:
        aud = self._get_audience_context(audience)
        typ = self._get_content_type_context(content_type)
        ton = self._get_tone_context(tone)
        year = datetime.now().year
        return f"""
Responda APENAS JSON válido no formato:
{{"items":[{{"title":"...","engagement_notes":"...","seo_notes":"...","trend_notes":"..."}}]}}
Nada de markdown, texto fora do JSON, comentários ou chaves extras.

TÓPICO: {topic}
{aud}
{typ}
{ton}

Gere 5 títulos distintos.
Regras:
- 35–65 caracteres; evitar clickbait vazio.
- Use termos pesquisáveis (long-tail quando fizer sentido).
- Se citar ano, use {year}.
Campos obrigatórios por item: title, engagement_notes, seo_notes, trend_notes.
"""

    def _prompt_script_json(self, topic: str, minutes: int, description: str) -> str:
        target_words = minutes * 165
        return f"""
Responda APENAS JSON válido no formato:
{{"sections":[{{"name":"Hook","script":"...","key_points":["..."],"est_seconds":20}}]}}
Nada de markdown ou texto fora do JSON.

TÓPICO: {topic}
DURAÇÃO ALVO: {minutes} minutos (≈ {target_words} palavras)
{f"OBJETIVOS: {description}" if description else ""}

Estrutura obrigatória (nomes livres, mas precisa cobrir): Hook, Introdução, Desenvolvimento (>=1), Conclusão.
Cada seção deve conter: name, script, key_points (>=3 no total do roteiro), est_seconds.
Forneça tempos reais por seção para somar ~ {minutes*60} segundos.
"""

    def _prompt_episode_json(self, title: str, series_type: str, episode_number: str) -> str:
        return f"""
Responda APENAS JSON válido no formato de plano de episódio:
{{
  "executive_summary":"...",
  "objectives":["..."],
  "prerequisites":["..."],
  "timeline":[{"minute":0,"segment":"Hook","goals":["..."],"engagement_points":["..."]}],
  "resources":["..."],
  "key_takeaways":["..."],
  "connections": {"previous": "...", "next": "..."},
  "success_metrics":["..."],
  "extras":["..."]
}}
Nada de markdown ou texto fora do JSON.

SÉRIE: {series_type or "Série Educativa"}
EPISÓDIO #{episode_number}: {title}
Forneça uma timeline prática (itens por minuto ou bloco), recursos claros e objetivos mensuráveis.
"""

    # ---------------
    # Métricas & utilitários
    # ---------------
    def _embed(self, text: str) -> List[float]:
        e = self.client.embeddings.create(model=self.embed_model, input=text)
        return e.data[0].embedding

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return dot / (na * nb + 1e-12)

    def _relevance(self, text: str, brief: str) -> float:
        try:
            return self._cosine(self._embed(text), self._embed(brief))
        except Exception as e:
            logger.warning(f"[embed] falha na relevância: {e}")
            return 0.5

    def _score_title(self, title: str, brief: str, recent: List[str] | None = None) -> Dict[str, Any]:
        rel = self._relevance(title, brief)  # 0..1
        length = len(title)
        len_ok = 1.0 if 35 <= length <= 65 else max(0.0, 1 - abs(50 - length) / 50)
        has_number = 1.0 if re.search(r"\d", title) else 0.0
        has_brackets = 1.0 if re.search(r"[\[\]()]", title) else 0.0
        starts_strong = 1.0 if re.match(r"(?i)como|guia|aprenda|por que|lista|top|segredos", title.strip()) else 0.4
        originality = 1.0
        if recent:
            try:
                sims = [self._cosine(self._embed(title), self._embed(t)) for t in recent[:20]]
                originality = 1 - max(sims) if sims else 1.0
            except Exception:
                originality = 1.0
        score = (0.45 * rel + 0.25 * len_ok + 0.10 * has_number + 0.05 * has_brackets + 0.05 * (1.0 if starts_strong else 0.4) + 0.10 * originality)
        return {
            "score": round(100 * score, 1),
            "relevance": round(rel, 3),
            "len_ok": round(len_ok, 3),
            "has_number": bool(has_number),
            "has_brackets": bool(has_brackets),
            "starts_strong": bool(starts_strong == 1.0),
            "originality": round(originality, 3),
        }

    @staticmethod
    def _timing_accuracy(total_seconds: int, target_minutes: int) -> int:
        target = target_minutes * 60
        if target == 0:
            return 0
        diff = abs(total_seconds - target) / target
        return max(0, min(100, int((1 - diff) * 100)))

    @staticmethod
    def _estimate_speaking_time(text: str) -> Dict[str, Any]:
        wc = len(text.split())
        return {
            "wpm_min": 130,
            "wpm_max": 160,
            "min_minutes": round(wc / 160, 1),
            "max_minutes": round(wc / 130, 1),
            "words": wc,
        }

    @staticmethod
    def _parse_duration(duration: str) -> int:
        try:
            import re as _re
            return int(_re.search(r"\d+", str(duration)).group())
        except Exception:
            return 10

    @staticmethod
    def _get_audience_context(audience: str) -> str:
        contexts = {
            "iniciantes": "AUDIÊNCIA: Iniciantes — linguagem acessível, evitar jargões, foco em benefícios práticos.",
            "intermediario": "AUDIÊNCIA: Intermediário — termos técnicos moderados e aplicações.",
            "avancado": "AUDIÊNCIA: Avançado — terminologia técnica e casos complexos.",
            "todos_os_niveis": "AUDIÊNCIA: Todos os níveis — equilibrar acessibilidade e profundidade.",
        }
        return contexts.get(audience, "")

    @staticmethod
    def _get_content_type_context(content_type: str) -> str:
        contexts = {
            "tutorial": "TIPO: Tutorial — instruções passo a passo e resultado prático.",
            "dicas": "TIPO: Dicas e Truques — praticidade e economia de tempo.",
            "review": "TIPO: Review/Análise — prós, contras e comparações.",
            "comparacao": "TIPO: Comparação — use 'vs', números e decisão clara.",
            "projeto": "TIPO: Projeto — foco no resultado final e aprendizado hands-on.",
        }
        return contexts.get(content_type, "")

    @staticmethod
    def _get_tone_context(tone: str) -> str:
        contexts = {
            "casual": "TOM: Casual — linguagem descontraída, exemplos do dia a dia.",
            "profissional": "TOM: Profissional — tom autoritativo com dados.",
            "divertido": "TOM: Divertido — humor sutil e referências culturais.",
            "motivacional": "TOM: Motivacional — incentivo à ação, foco em transformação.",
            "educativo": "TOM: Educativo — didático e estruturado.",
        }
        return contexts.get(tone, "")

    @staticmethod
    def _episode_sections_found(ep: EpisodePlan) -> int:
        count = 0
        count += 1 if ep.executive_summary else 0
        count += 1 if ep.objectives else 0
        count += 1 if ep.prerequisites else 0
        count += 1 if ep.timeline else 0
        count += 1 if ep.resources else 0
        count += 1 if ep.key_takeaways else 0
        count += 1 if ep.connections else 0
        count += 1 if ep.success_metrics else 0
        count += 1 if ep.extras else 0
        return count

    @staticmethod
    def _episode_completeness(ep: EpisodePlan) -> int:
        total = 9
        found = AIContentService._episode_sections_found(ep)
        return int(found / total * 100)

    @staticmethod
    def _score_script(structure_coverage: float, timing_accuracy: int, relevance: float) -> int:
        # pesos simples; ajuste com dados reais quando houver
        score = 0.45 * (relevance) + 0.35 * (timing_accuracy / 100) + 0.20 * (structure_coverage)
        return max(0, min(100, int(round(100 * score))))

    @staticmethod
    def _episode_as_text(ep: EpisodePlan) -> str:
        parts = [
            "RESUMO EXECUTIVO:\n" + ep.executive_summary,
            "\nOBJETIVOS:\n- " + "\n- ".join(ep.objectives) if ep.objectives else "",
            "\nPRÉ-REQUISITOS:\n- " + "\n- ".join(ep.prerequisites) if ep.prerequisites else "",
            "\nTIMELINE:" + "".join([
                f"\n  [{t.minute:02d}m] {t.segment}\n    - Goals: " + ", ".join(t.goals) +
                ("\n    - Engajamento: " + ", ".join(t.engagement_points) if t.engagement_points else "")
                for t in ep.timeline
            ]),
            "\nRECURSOS:\n- " + "\n- ".join(ep.resources) if ep.resources else "",
            "\nTAKEAWAYS:\n- " + "\n- ".join(ep.key_takeaways) if ep.key_takeaways else "",
            "\nCONEXÕES:\n" + json.dumps(ep.connections, ensure_ascii=False, indent=2) if ep.connections else "",
            "\nMÉTRICAS DE SUCESSO:\n- " + "\n- ".join(ep.success_metrics) if ep.success_metrics else "",
            "\nEXTRAS:\n- " + "\n- ".join(ep.extras) if ep.extras else "",
        ]
        return "\n".join([p for p in parts if p])
