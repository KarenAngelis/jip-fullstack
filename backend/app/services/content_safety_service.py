# app/services/content_safety_service.py
"""
Serviço de Content Safety e Compliance para episódios.
"""

import re
from typing import Dict, List, Optional, Tuple, Any  # ← IMPORT CORRIGIDO
from enum import Enum

class ContentRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SensitiveTopicCategory(str, Enum):
    MENTAL_HEALTH = "mental_health"
    MEDICAL = "medical"
    POLITICAL = "political"
    RELIGIOUS = "religious"
    REPRODUCTIVE = "reproductive"
    VIOLENCE = "violence"
    FINANCIAL = "financial"
    LEGAL = "legal"

class ContentSafetyService:
    """
    Analisa conteúdo e sugere melhorias de compliance
    """
    
    def __init__(self):
        # Palavras-chave que indicam temas sensíveis
        self.sensitive_keywords = {
            SensitiveTopicCategory.MENTAL_HEALTH: [
                "suicídio", "suicidio", "depressão", "depressao", "ansiedade", 
                "transtorno", "automutilação", "cortar", "matar-se", "morte",
                "overdose", "anorexia", "bulimia"
            ],
            SensitiveTopicCategory.MEDICAL: [
                "diagnóstico", "diagnostico", "tratamento", "remédio", "remedio",
                "doença", "doenca", "câncer", "cancer", "diabetes", "covid"
            ],
            SensitiveTopicCategory.REPRODUCTIVE: [
                "aborto", "gravidez", "anticoncepcional", "pílula", "pilula",
                "fertilidade", "misoprostol", "citotec"
            ],
            SensitiveTopicCategory.POLITICAL: [
                "bolsonaro", "lula", "pt", "psdb", "eleição", "eleicao",
                "governo", "partido", "esquerda", "direita"
            ],
            SensitiveTopicCategory.RELIGIOUS: [
                "inferno", "demônio", "demonio", "satanás", "satanas",
                "heresia", "blasfêmia", "blasfemia"
            ],
            SensitiveTopicCategory.VIOLENCE: [
                "violência", "violencia", "estupro", "abuso", "agressão", "agressao",
                "bullying", "harassment", "assédio", "assedio"
            ],
            SensitiveTopicCategory.FINANCIAL: [
                "investimento garantido", "ganhe dinheiro rápido", "pirâmide",
                "bitcoin garantido", "trader", "day trade"
            ],
            SensitiveTopicCategory.LEGAL: [
                "advogado", "processo", "tribunal", "prisão", "prisao",
                "crime", "ilegal", "lei"
            ]
        }
        
        # Templates de disclaimers
        self.disclaimers = {
            SensitiveTopicCategory.MENTAL_HEALTH: [
                "Este episódio aborda temas relacionados à saúde mental.",
                "Se você está passando por dificuldades, busque ajuda profissional.",
                "CVV: 188 (24h, gratuito). Chat: https://www.cvv.org.br"
            ],
            SensitiveTopicCategory.MEDICAL: [
                "Este conteúdo não substitui consulta médica profissional.",
                "Sempre consulte um profissional de saúde para decisões médicas.",
                "Experiências pessoais não devem ser generalizadas."
            ],
            SensitiveTopicCategory.REPRODUCTIVE: [
                "Este episódio trata de temas relacionados à reprodução.",
                "Respeitamos todas as perspectivas sobre estes temas complexos.",
                "Para orientação médica, consulte profissionais especializados."
            ],
            SensitiveTopicCategory.POLITICAL: [
                "Este conteúdo expressa opiniões pessoais sobre temas políticos.",
                "Respeitamos a diversidade de perspectivas políticas.",
                "Encorajamos o diálogo respeitoso e informado."
            ],
            SensitiveTopicCategory.RELIGIOUS: [
                "Este episódio aborda temas de fé e espiritualidade.",
                "Respeitamos todas as tradições religiosas e perspectivas.",
                "O conteúdo reflete experiências e crenças pessoais."
            ]
        }

    def analyze_content_safety(
        self, 
        titulo: str, 
        outline: Dict, 
        roteiro: Dict,
        historia_pessoal: Optional[str] = None
    ) -> Dict:
        """
        Analisa segurança do conteúdo e retorna relatório completo
        """
        # Combina todo o texto para análise
        full_content = self._extract_full_text(titulo, outline, roteiro, historia_pessoal)
        
        # Identifica temas sensíveis
        sensitive_topics = self._identify_sensitive_topics(full_content)
        
        # Calcula nível de risco
        risk_level = self._calculate_risk_level(sensitive_topics, full_content)
        
        # Gera disclaimers
        disclaimers = self._generate_disclaimers(sensitive_topics)
        
        # Sugere melhorias
        improvements = self._suggest_improvements(sensitive_topics, full_content)
        
        # Detecta linguagem problemática
        problematic_language = self._detect_problematic_language(full_content)
        
        return {
            "risk_level": risk_level,
            "sensitive_topics": [topic.value for topic in sensitive_topics],
            "disclaimers": disclaimers,
            "improvements": improvements,
            "problematic_language": problematic_language,
            "compliance_score": self._calculate_compliance_score(risk_level, problematic_language),
            "recommendations": self._generate_recommendations(risk_level, sensitive_topics)
        }

    def _extract_full_text(
        self, 
        titulo: str, 
        outline: Dict, 
        roteiro: Dict, 
        historia_pessoal: Optional[str]
    ) -> str:
        """Extrai todo o texto para análise"""
        texts = [titulo]
        
        if historia_pessoal:
            texts.append(historia_pessoal)
        
        # Extrai texto do outline
        if outline:
            texts.append(str(outline.get("introducao", "")))
            texts.extend(outline.get("desenvolvimento", []))
            texts.append(str(outline.get("conclusao", "")))
        
        # Extrai texto do roteiro
        if roteiro:
            texts.append(str(roteiro.get("abertura", "")))
            
            blocos = roteiro.get("blocos", [])
            for bloco in blocos:
                texts.append(str(bloco.get("conteudo", "")))
            
            texts.append(str(roteiro.get("encerramento", "")))
        
        return " ".join(texts).lower()

    def _identify_sensitive_topics(self, content: str) -> List[SensitiveTopicCategory]:
        """Identifica temas sensíveis no conteúdo"""
        identified_topics = set()
        
        for category, keywords in self.sensitive_keywords.items():
            for keyword in keywords:
                if keyword.lower() in content.lower():
                    identified_topics.add(category)
                    break
        
        return list(identified_topics)

    def _calculate_risk_level(
        self, 
        sensitive_topics: List[SensitiveTopicCategory], 
        content: str
    ) -> ContentRiskLevel:
        """Calcula nível de risco baseado nos temas identificados"""
        
        if not sensitive_topics:
            return ContentRiskLevel.LOW
        
        # Temas de alto risco
        high_risk_topics = [
            SensitiveTopicCategory.MENTAL_HEALTH,
            SensitiveTopicCategory.MEDICAL,
            SensitiveTopicCategory.VIOLENCE
        ]
        
        # Verifica se tem temas críticos
        critical_keywords = ["suicídio", "suicidio", "matar-se", "overdose"]
        if any(keyword in content for keyword in critical_keywords):
            return ContentRiskLevel.CRITICAL
        
        # Verifica temas de alto risco
        if any(topic in high_risk_topics for topic in sensitive_topics):
            return ContentRiskLevel.HIGH
        
        # Múltiplos temas sensíveis = risco médio
        if len(sensitive_topics) > 2:
            return ContentRiskLevel.MEDIUM
        
        return ContentRiskLevel.MEDIUM if sensitive_topics else ContentRiskLevel.LOW

    def _generate_disclaimers(self, sensitive_topics: List[SensitiveTopicCategory]) -> List[str]:
        """Gera disclaimers apropriados"""
        disclaimers = []
        
        for topic in sensitive_topics:
            if topic in self.disclaimers:
                disclaimers.extend(self.disclaimers[topic])
        
        # Disclaimer geral sempre presente
        general_disclaimer = [
            "As opiniões expressas são pessoais e não representam aconselhamento profissional.",
            "Este conteúdo é apenas para fins informativos e educacionais."
        ]
        
        return general_disclaimer + disclaimers

    def _detect_problematic_language(self, content: str) -> List[Dict]:
        """Detecta linguagem potencialmente problemática"""
        problematic_patterns = [
            {
                "pattern": r"\b(sempre|nunca|todos|ninguém)\b",
                "type": "generalization",
                "description": "Uso de generalizações absolutas",
                "suggestion": "Use termos como 'geralmente', 'na maioria dos casos', 'muitas pessoas'"
            },
            {
                "pattern": r"\b(devastador|terrível|horrível|catastrófico)\b",
                "type": "dramatic_language",
                "description": "Linguagem excessivamente dramática",
                "suggestion": "Use termos mais neutros como 'desafiador', 'difícil', 'complexo'"
            },
            {
                "pattern": r"\b(você deve|precisa|tem que)\b",
                "type": "prescriptive",
                "description": "Linguagem muito prescritiva",
                "suggestion": "Use 'considere', 'pode ser útil', 'uma opção é'"
            }
        ]
        
        issues = []
        for pattern_info in problematic_patterns:
            matches = re.findall(pattern_info["pattern"], content, re.IGNORECASE)
            if matches:
                issues.append({
                    "type": pattern_info["type"],
                    "description": pattern_info["description"],
                    "matches": matches,
                    "suggestion": pattern_info["suggestion"]
                })
        
        return issues

    def _suggest_improvements(
        self, 
        sensitive_topics: List[SensitiveTopicCategory], 
        content: str
    ) -> List[str]:
        """Sugere melhorias específicas"""
        improvements = []
        
        if SensitiveTopicCategory.REPRODUCTIVE in sensitive_topics:
            improvements.extend([
                "Use linguagem mais neutra: 'considerou diferentes opções' em vez de 'estava prestes a abortar'",
                "Adicione perspectivas múltiplas sobre temas reprodutivos",
                "Evite linguagem que possa soar julgmental"
            ])
        
        if SensitiveTopicCategory.MENTAL_HEALTH in sensitive_topics:
            improvements.extend([
                "Inclua recursos de ajuda (CVV, terapeutas, etc.)",
                "Evite romantizar ou dramatizar problemas de saúde mental",
                "Use terminologia clinicamente apropriada"
            ])
        
        if SensitiveTopicCategory.MEDICAL in sensitive_topics:
            improvements.extend([
                "Deixe claro que não é aconselhamento médico",
                "Sugira consultar profissionais de saúde",
                "Evite fazer afirmações médicas definitivas"
            ])
        
        return improvements

    def _calculate_compliance_score(
        self, 
        risk_level: ContentRiskLevel, 
        problematic_language: List[Dict]
    ) -> float:
        """Calcula score de compliance de 0-100"""
        base_score = 100.0
        
        # Penalidades por nível de risco
        risk_penalties = {
            ContentRiskLevel.LOW: 0,
            ContentRiskLevel.MEDIUM: 15,
            ContentRiskLevel.HIGH: 30,
            ContentRiskLevel.CRITICAL: 50
        }
        
        base_score -= risk_penalties[risk_level]
        
        # Penalidades por linguagem problemática
        base_score -= len(problematic_language) * 5
        
        return max(0, base_score)

    def _generate_recommendations(
        self, 
        risk_level: ContentRiskLevel, 
        sensitive_topics: List[SensitiveTopicCategory]
    ) -> List[str]:
        """Gera recomendações baseadas no nível de risco"""
        recommendations = []
        
        if risk_level == ContentRiskLevel.CRITICAL:
            recommendations.extend([
                "RECOMENDAÇÃO CRÍTICA: Revisar completamente o conteúdo antes da publicação",
                "Consultar especialistas em saúde mental",
                "Considerar se o conteúdo é apropriado para o formato de podcast"
            ])
        
        elif risk_level == ContentRiskLevel.HIGH:
            recommendations.extend([
                "Adicionar disclaimers no início do episódio",
                "Incluir recursos de ajuda nas notas do episódio",
                "Revisar linguagem para garantir sensibilidade"
            ])
        
        elif risk_level == ContentRiskLevel.MEDIUM:
            recommendations.extend([
                "Adicionar contexto apropriado",
                "Considerar disclaimers relevantes",
                "Revisar para linguagem inclusiva"
            ])
        
        return recommendations