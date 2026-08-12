# app/services/juridical/document_templates.py

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class DocumentTemplate:
    name: str
    required_clauses: List[str]
    prohibited_terms: List[str]
    legal_references: List[str]
    specific_checks: List[str]


DOCUMENT_TEMPLATES: Dict[str, DocumentTemplate] = {
    "termos_uso_ecommerce": DocumentTemplate(
        name="Termos de Uso - E-commerce",
        required_clauses=[
            "prazo de entrega",
            "direito de arrependimento",
            "política de trocas e devoluções",
            "forma de pagamento",
            "atendimento ao consumidor",
            "foro de eleição",
            "proteção de dados pessoais",
        ],
        prohibited_terms=[
            "não nos responsabilizamos",
            "isenta de responsabilidade",
            "uso por sua conta e risco",
        ],
        legal_references=[
            "CDC - Código de Defesa do Consumidor",
            "Marco Civil da Internet",
            "LGPD",
        ],
        specific_checks=[
            "Prazo de arrependimento de 7 dias",
            "Informações claras sobre produto/serviço",
            "Canal de atendimento funcional",
        ],
    ),
    "politica_privacidade": DocumentTemplate(
        name="Política de Privacidade",
        required_clauses=[
            "tipos de dados coletados",
            "finalidade do tratamento",
            "base legal para tratamento",
            "compartilhamento de dados",
            "direitos do titular",
            "contato do encarregado",
            "prazo de armazenamento",
            "medidas de segurança",
        ],
        prohibited_terms=[
            "dados utilizados livremente",
            "transferência irrestrita",
        ],
        legal_references=[
            "LGPD - Lei Geral de Proteção de Dados",
            "Constituição Federal Art. 5º",
        ],
        specific_checks=[
            "Base legal específica para cada tratamento",
            "Direitos LGPD explícitos",
            "Canais para exercer direitos",
        ],
    ),
}


class SpecializedAnalyzer:
    # -----------------------
    # Helpers internos
    # -----------------------
    @staticmethod
    def _contains_all_words(text_lower: str, phrase: str) -> bool:
        """Retorna True se TODAS as palavras de 'phrase' existem em text_lower."""
        words = [w for w in phrase.lower().split() if w]
        return all(w in text_lower for w in words)

    @staticmethod
    def _score_cap(value: float) -> float:
        """Garante score entre 0.0 e 1.0, com 3 casas."""
        return round(max(0.0, min(1.0, value)), 3)

    # -----------------------
    # Análises especializadas
    # -----------------------
    @staticmethod
    async def analyze_ecommerce_terms(content: str) -> Dict[str, Any]:
        """Análise específica para Termos de Uso de e-commerce (CDC + boas práticas)."""
        template = DOCUMENT_TEMPLATES["termos_uso_ecommerce"]
        content_lower = content.lower()

        # 1) Cláusulas obrigatórias — exige TODAS as palavras da cláusula
        missing_clauses: List[str] = []
        for clause in template.required_clauses:
            if not SpecializedAnalyzer._contains_all_words(content_lower, clause):
                missing_clauses.append(f"Ausente: {clause}")

        # 2) Termos proibidos
        prohibited_found: List[str] = []
        for term in template.prohibited_terms:
            if term.lower() in content_lower:
                prohibited_found.append(f"Termo inadequado: '{term}'")

        # 3) Verificações específicas do CDC
        specific_violations: List[str] = []

        # Direito de arrependimento (art. 49, 7 dias)
        if "arrependimento" in content_lower and not (
            "7 dias" in content_lower or "sete dias" in content_lower
        ):
            specific_violations.append(
                "Prazo de arrependimento deve estar explícito (7 dias)"
            )

        # Informação adequada sobre produto/serviço (art. 31)
        info_terms = ["características", "qualidade", "preço", "prazo"]
        if not any(t in content_lower for t in info_terms):
            specific_violations.append(
                "Faltam informações adequadas sobre produtos/serviços (art. 31, CDC)"
            )

        # 4) Score simples (penaliza cada problema)
        penalties = len(missing_clauses) + len(prohibited_found) + len(specific_violations)
        score = SpecializedAnalyzer._score_cap(1 - penalties * 0.1)

        return {
            "template_used": template.name,
            "missing_clauses": missing_clauses,
            "prohibited_terms": prohibited_found,
            "specific_violations": specific_violations,
            "compliance_score": score,
            "legal_references": template.legal_references,
        }

    @staticmethod
    async def analyze_privacy_policy(content: str) -> Dict[str, Any]:
        """Análise específica para Política de Privacidade (LGPD)."""
        template = DOCUMENT_TEMPLATES["politica_privacidade"]
        content_lower = content.lower()

        # Requisitos LGPD essenciais por grupos de termos
        lgpd_requirements: Dict[str, List[str]] = {
            "base_legal": [
                "consentimento",
                "legítimo interesse",
                "execução contrato",
                "cumprimento obrigação legal",
            ],
            "direitos_titular": [
                "acesso",
                "correção",
                "anonimização",
                "eliminação",
                "portabilidade",
                "oposição",
            ],
            "dados_sensiveis": [
                "dados sensíveis",
                "categoria especial",
                "consentimento específico",
            ],
        }

        missing_lgpd: List[str] = []
        for label, keywords in lgpd_requirements.items():
            if not any(k in content_lower for k in keywords):
                missing_lgpd.append(f"LGPD: Ausente {label.replace('_', ' ')}")

        # DPO/Encarregado
        if "encarregado" not in content_lower and "dpo" not in content_lower:
            missing_lgpd.append("LGPD: Contato do Encarregado/DPO não informado")

        score = SpecializedAnalyzer._score_cap(1 - len(missing_lgpd) * 0.15)

        return {
            "template_used": template.name,
            "missing_lgpd_requirements": missing_lgpd,
            "compliance_score": score,
            "legal_references": template.legal_references,
        }
