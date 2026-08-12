# app/services/juridical/sources.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class LegalSourceType(str, Enum):
    """Categorias de fontes jurídicas suportadas."""

    FEDERAL_LAW = "lei_federal"
    CONSTITUTION = "constituicao"
    CONSUMER_LAW = "direito_consumidor"
    LABOR_LAW = "direito_trabalhista"
    TAX_LAW = "direito_tributario"
    JURISPRUDENCE = "jurisprudencia"
    REGULATORY = "norma_regulamentadora"


@dataclass(frozen=True)
class LegalSource:
    """
    Representa uma fonte jurídica.
    `authority_level`: peso de 1–10 (10 = mais autoritativo).
    `scraping_rules`: dicas de CSS/xpath para scrapers.
    """

    name: str
    base_url: str
    search_endpoint: str
    source_type: LegalSourceType
    authority_level: int
    scraping_rules: Dict[str, str]

    @property
    def full_url(self) -> str:
        """URL completa para a página inicial de busca/consulta."""
        return f"{self.base_url}{self.search_endpoint}"


# Fontes jurídicas brasileiras mapeadas
LEGAL_SOURCES: Dict[str, LegalSource] = {
    "planalto": LegalSource(
        name="Planalto - Legislação Federal",
        base_url="https://www.planalto.gov.br",
        search_endpoint="/ccivil_03/constituicao/constituicao.htm",
        source_type=LegalSourceType.CONSTITUTION,
        authority_level=10,
        scraping_rules={
            "article_selector": ".artigo",
            "text_selector": ".texto-artigo",
        },
    ),
    "jusbrasil": LegalSource(
        name="JusBrasil",
        base_url="https://www.jusbrasil.com.br",
        search_endpoint="/busca",
        source_type=LegalSourceType.JURISPRUDENCE,
        authority_level=8,
        scraping_rules={
            "result_selector": ".SearchResult",
            "title_selector": ".SearchResult-title",
            "content_selector": ".SearchResult-content",
        },
    ),
    "stf": LegalSource(
        name="STF - Supremo Tribunal Federal",
        base_url="https://portal.stf.jus.br",
        search_endpoint="/jurisprudencia/",
        source_type=LegalSourceType.JURISPRUDENCE,
        authority_level=10,
        scraping_rules={
            "decision_selector": ".decisao",
            "ementa_selector": ".ementa",
        },
    ),
    "stj": LegalSource(
        name="STJ - Superior Tribunal de Justiça",
        base_url="https://www.stj.jus.br",
        search_endpoint="/sites/portalp/Jurisprudencia",
        source_type=LegalSourceType.JURISPRUDENCE,
        authority_level=9,
        scraping_rules={
            "acordao_selector": ".acordao",
            "relator_selector": ".relator",
        },
    ),
    "procon": LegalSource(
        name="PROCON - Direito do Consumidor",
        base_url="https://www.procon.org.br",
        search_endpoint="/legislacao",
        source_type=LegalSourceType.CONSUMER_LAW,
        authority_level=8,
        scraping_rules={
            "lei_selector": ".lei-content",
            "artigo_selector": ".artigo",
        },
    ),
}
