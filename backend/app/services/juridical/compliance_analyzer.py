# app/services/juridical/compliance_analyzer.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import os
import re
import json
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup
import asyncio

# Se você usa o SDK novo da OpenAI:
import openai as openai_pkg
from openai import OpenAI


@dataclass
class ComplianceAnalysis:
    status: str
    confidence_score: float
    violations: List[str]
    recommendations: List[str]
    risk_level: str
    summary: str
    detailed_analysis: str
    legal_basis: List[Dict[str, Any]]


# ========= Scraper real (equivalente ao que você já tem no main) =========
class _RealLegalScraper:
    def __init__(self) -> None:
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        }
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def search_all_sources(self, query: str, context_area: str = "geral") -> List[Dict[str, Any]]:
        tasks = [
            self._search_planalto_constitution(query),
            self._search_cdc(query),
        ]
        if 'trabalhista' in context_area.lower():
            tasks.append(self._search_clt(query))
        if 'lgpd' in context_area.lower() or 'dados' in context_area.lower():
            tasks.append(self._search_lgpd(query))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_items: List[Dict[str, Any]] = []
        for r in results:
            if isinstance(r, list):
                all_items.extend(r)

        # de-dup simples por conteúdo
        seen = set()
        uniq: List[Dict[str, Any]] = []
        for it in all_items:
            key = it['content'][:120]
            if key not in seen:
                seen.add(key)
                uniq.append(it)
        uniq.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return uniq[:8]

    async def _fetch(self, url: str) -> Optional[str]:
        try:
            async with aiohttp.ClientSession(headers=self.headers, timeout=self.timeout) as s:
                async with s.get(url) as resp:
                    if resp.status != 200:
                        return None
                    return await resp.text()
        except Exception:
            return None

    def _calc_rel(self, text: str, query: str) -> float:
        text_lower = text.lower()
        words = [w for w in query.lower().split() if len(w) > 2]
        if not words:
            return 0.0
        base = sum(1 for w in words if w in text_lower) / max(len(words), 1)
        boost = 0.0
        for t in ('direito','lei','código','artigo','constituição','dever','obrigação','responsabilidade','consumidor'):
            if t in text_lower:
                boost += 0.05
        return min(base + boost, 1.0)

    def _extract_article(self, text: str) -> str:
        for pat in (r'Art\.?\s*(\d+)[º°]?', r'Artigo\s*(\d+)', r'§\s*(\d+)[º°]?'):
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                return f"Art. {m.group(1)}"
        return "Dispositivo legal"

    async def _generic_parse(self, url: str, label: str, cap: int = 3) -> List[Dict[str, Any]]:
        html = await self._fetch(url)
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        out: List[Dict[str, Any]] = []
        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if len(text) < 30:
                continue
            out.append({
                "source": label,
                "source_type": "legislation",
                "authority_level": 10,
                "article": self._extract_article(text),
                "content": text[:600] + "..." if len(text) > 600 else text,
                "url": url,
                "relevance_score": 0.0,  # ajustado depois
            })
        return out[:cap]

    async def _search_planalto_constitution(self, query: str) -> List[Dict[str, Any]]:
        url = "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm"
        items = await self._generic_parse(url, "Constituição Federal", cap=30)
        for it in items:
            it["relevance_score"] = self._calc_rel(it["content"], query)
        items = [i for i in items if i["relevance_score"] > 0.1]
        items.sort(key=lambda x: x["relevance_score"], reverse=True)
        return items[:3]

    async def _search_cdc(self, query: str) -> List[Dict[str, Any]]:
        url = "https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm"
        items = await self._generic_parse(url, "Código de Defesa do Consumidor (Lei 8.078/90)", cap=30)
        for it in items:
            it["relevance_score"] = self._calc_rel(it["content"], query)
        items = [i for i in items if i["relevance_score"] > 0.1]
        items.sort(key=lambda x: x["relevance_score"], reverse=True)
        return items[:3]

    async def _search_clt(self, query: str) -> List[Dict[str, Any]]:
        url = "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm"
        items = await self._generic_parse(url, "CLT - Consolidação das Leis do Trabalho", cap=30)
        for it in items:
            it["relevance_score"] = self._calc_rel(it["content"], query)
        items = [i for i in items if i["relevance_score"] > 0.1]
        items.sort(key=lambda x: x["relevance_score"], reverse=True)
        return items[:2]

    async def _search_lgpd(self, query: str) -> List[Dict[str, Any]]:
        url = "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm"
        items = await self._generic_parse(url, "LGPD - Lei Geral de Proteção de Dados (Lei 13.709/18)", cap=30)
        for it in items:
            it["relevance_score"] = self._calc_rel(it["content"], query)
        items = [i for i in items if i["relevance_score"] > 0.1]
        items.sort(key=lambda x: x["relevance_score"], reverse=True)
        return items[:2]


# ========= Analyzer que usa o scraper real + OpenAI =========
class LegalComplianceAnalyzer:
    def __init__(self, openai_api_key: Optional[str] = None) -> None:
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY não configurada.")
        # SDK novo:
        self.client: OpenAI = OpenAI(api_key=api_key)
        self.scraper = _RealLegalScraper()

    async def analyze_compliance(
        self,
        content_to_analyze: str,
        context_area: str = "geral",
        specific_laws: Optional[List[str]] = None,
    ) -> ComplianceAnalysis:
        # 1) Busca real nas fontes
        legal_sources = await self.scraper.search_all_sources(content_to_analyze, context_area)

        # 2) Prompt para o modelo (JSON estrito)
        legal_context = "\n".join([
            f"**{s['source']}** ({s.get('article','N/A')}):\n{s['content']}\n"
            for s in legal_sources[:4]
        ])
        prompt = f"""
Você é um advogado especialista em direito brasileiro. Analise a conformidade legal do conteúdo usando as fontes jurídicas REAIS consultadas.

CONTEXTO: {context_area}

CONTEÚDO:
{content_to_analyze}

FONTES JURÍDICAS REAIS CONSULTADAS:
{legal_context}

RESPONDA EM JSON VÁLIDO:
{{
  "conformidade_status": "compliant|non_compliant|partially_compliant|unclear",
  "confidence_score": 0.85,
  "violations": ["violação específica com Art. X"],
  "legal_articles_cited": ["Art. 5º da CF/88", "Art. 6º do CDC"],
  "recommendations": ["recomendação específica 1", "recomendação 2"],
  "risk_level": "low|medium|high|critical",
  "summary": "Resumo em 2-3 frases",
  "detailed_analysis": "Análise detalhada citando os dispositivos consultados"
}}
        """.strip()

        # 3) Chamada ao modelo (thread-safe)
        resp = await asyncio.to_thread(
            self.client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um advogado especialista em direito brasileiro. SEMPRE responda em JSON válido."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1500,
        )

        text = resp.choices[0].message.content.strip()
        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()

        try:
            parsed = json.loads(text)
        except Exception:
            # fallback simples para nunca quebrar o router
            parsed = {
                "conformidade_status": "unclear",
                "confidence_score": 0.0,
                "violations": ["Erro ao interpretar resposta do modelo"],
                "recommendations": ["Tente novamente"],
                "risk_level": "medium",
                "summary": "Falha de parsing",
                "detailed_analysis": text[:800],
            }

        return ComplianceAnalysis(
            status=parsed.get("conformidade_status", "unclear"),
            confidence_score=float(parsed.get("confidence_score", 0.0) or 0.0),
            violations=list(parsed.get("violations") or []),
            recommendations=list(parsed.get("recommendations") or []),
            risk_level=str(parsed.get("risk_level", "medium")),
            summary=str(parsed.get("summary", "")),
            detailed_analysis=str(parsed.get("detailed_analysis", "")),
            legal_basis=legal_sources[:5],
        )
