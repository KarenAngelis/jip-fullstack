# app/services/juridical/scraper.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup


class LegalScraper:
    """
    Scraper leve para fontes públicas (Planalto/JusBrasil/CDC).
    Use com 'async with LegalScraper() as s:' para garantir a sessão HTTP.
    """

    def __init__(self, *, timeout_seconds: int = 30, max_results: int = 5) -> None:
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout_seconds = timeout_seconds
        self.max_results = max_results
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; LegalComplianceBot/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    # ------------- context manager -------------

    async def __aenter__(self) -> "LegalScraper":
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=self.timeout_seconds),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    # ------------- helpers internos -------------

    def _require_session(self) -> aiohttp.ClientSession:
        if not self.session or self.session.closed:
            raise RuntimeError("LegalScraper: use 'async with LegalScraper()' para abrir a sessão HTTP.")
        return self.session

    async def _fetch_html(self, url: str, *, params: Optional[Dict[str, Any]] = None) -> str:
        """Faz GET e retorna o HTML (ou string vazia em erro controlado)."""
        session = self._require_session()
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    # Falha previsível (evita exception barulhenta)
                    print(f"[SCRAPER] GET {url} status={resp.status}")
                    return ""
                # Melhor esforço para decodificação
                text = await resp.text(errors="ignore")
                return text or ""
        except Exception as e:
            print(f"[SCRAPER] Erro GET {url}: {e}")
            return ""

    @staticmethod
    def _calculate_relevance(text: str, query: str) -> float:
        """Score simples de relevância [0,1] por palavras da query + boost jurídico."""
        text_lower = text.lower()
        query_words = [w.lower() for w in query.split() if len(w) > 2]
        if not query_words:
            return 0.0

        word_matches = sum(1 for w in query_words if w in text_lower)
        word_score = word_matches / max(len(query_words), 1)

        boost = 0.0
        for term in ("artigo", "lei", "código", "direito", "dever", "obrigação", "responsabilidade"):
            if term in text_lower:
                boost += 0.1

        return min(word_score + boost, 1.0)

    # ------------- fontes -------------

    async def search_planalto_constitution(self, query: str) -> List[Dict[str, Any]]:
        """
        Busca básica na Constituição Federal (Planalto).
        Heurística: varre <p> com padrão 'Art. <n>' e filtra por palavras da query.
        """
        url = "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm"
        html = await self._fetch_html(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        results: List[Dict[str, Any]] = []

        # Pega parágrafos que contenham "Art. N"
        paragraphs = soup.find_all("p", string=re.compile(r"Art\.?\s*\d+"))
        for p in paragraphs:
            text = p.get_text(" ", strip=True)
            if any(k.lower() in text.lower() for k in query.split()):
                m = re.search(r"Art\.?\s*(\d+)", text)
                art_num = m.group(1) if m else "N/A"
                results.append(
                    {
                        "source": "Constituição Federal",
                        "article": f"Artigo {art_num}",
                        "content": (text[:500] + "...") if len(text) > 500 else text,
                        "full_content": text,
                        "authority_level": 10,
                        "url": f"{url}#art{art_num}",
                        "relevance_score": self._calculate_relevance(text, query),
                    }
                )

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[: self.max_results]

    async def search_jusbrasil(self, query: str, law_type: str = "") -> List[Dict[str, Any]]:
        """
        Busca jurisprudência no JusBrasil (HTML público).
        Seletores são heurísticos e podem mudar no site.
        """
        url = "https://www.jusbrasil.com.br/busca"
        html = await self._fetch_html(url, params={"q": f"{query} {law_type}".strip(), "p": 1})
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        results: List[Dict[str, Any]] = []

        cards = soup.find_all("div", class_=re.compile(r"(SearchResult|search-result)"))
        for card in cards[: 10]:
            title_el = card.find(["h3", "h4", "a"], class_=re.compile(r"(title|Title)")) or card.find("a")
            content_el = card.find(["p", "div"], class_=re.compile(r"(content|snippet|excerpt)")) or card.find("p")

            if not title_el or not content_el:
                continue

            title = title_el.get_text(" ", strip=True)
            content = content_el.get_text(" ", strip=True)
            link_el = title_el if title_el.name == "a" else title_el.find("a")
            link = urljoin("https://www.jusbrasil.com.br", link_el.get("href")) if link_el and link_el.get("href") else ""

            results.append(
                {
                    "source": "JusBrasil",
                    "title": title,
                    "content": (content[:400] + "...") if len(content) > 400 else content,
                    "url": link,
                    "authority_level": 8,
                    "relevance_score": self._calculate_relevance(f"{title} {content}", query),
                }
            )

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[: max(self.max_results, 5)]  # JusBrasil geralmente rende mais itens úteis

    async def search_consumer_law(self, query: str) -> List[Dict[str, Any]]:
        """
        Busca no CDC (Planalto compilado).
        Heurística: varre <p> que começam com 'Art. N' e agrega parágrafos adjacentes.
        """
        url = "https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm"
        html = await self._fetch_html(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        results: List[Dict[str, Any]] = []

        articles = soup.find_all("p", string=re.compile(r"Art\.?\s*\d+"))
        for i, p in enumerate(articles[:50]):  # limita parsing
            text = p.get_text(" ", strip=True)

            # agrega parágrafos seguintes até próximo "Art."
            full_text = text
            sib = p.next_sibling
            while sib and len(full_text) < 900:
                if hasattr(sib, "get_text"):
                    t = sib.get_text(" ", strip=True)
                    if t and not t.startswith("Art."):
                        full_text += " " + t
                    elif t.startswith("Art."):
                        break
                sib = getattr(sib, "next_sibling", None)

            if any(k.lower() in full_text.lower() for k in query.split()):
                m = re.search(r"Art\.?\s*(\d+)", text)
                art_num = m.group(1) if m else str(i + 1)
                results.append(
                    {
                        "source": "Código de Defesa do Consumidor",
                        "article": f"Artigo {art_num} - CDC",
                        "content": (full_text[:500] + "...") if len(full_text) > 500 else full_text,
                        "full_content": full_text,
                        "authority_level": 10,
                        "url": f"{url}#art{art_num}",
                        "relevance_score": self._calculate_relevance(full_text, query),
                    }
                )

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[: self.max_results]
