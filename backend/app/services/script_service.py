"""
app/services/script_service.py

Serviço de geração e análise de roteiros para vídeo usando OpenAI.

O que faz:
- Gera um roteiro "pronto para gravação" com timing preciso por seção (HOOK, INTRODUÇÃO,
  CONTEÚDO PRINCIPAL, CONCLUSÃO), instruções técnicas ([PAUSA], [MOSTRAR TELA], etc.)
  e, opcionalmente, momentos de [INTERAÇÃO].
- Dimensiona o tamanho do texto pela duração alvo, usando 165 palavras/min (words_per_minute).
- Analisa o resultado: contagem de palavras, duração estimada, aderência à meta,
  presença de timestamps/seções, notas técnicas, legibilidade e um score geral.
- Analisa roteiros já existentes, gerando métricas e recomendações de melhoria.

Pontos principais da implementação:
- Classe ScriptService:
  - generate_script(topic, duration_minutes=10, objectives="", audience="geral",
    style="educativo", include_interactions=True) -> Dict
      * Constrói um prompt estruturado (_build_script_prompt) com palavras-alvo e
        contexto de audiência/estilo.
      * Chama OpenAI (modelo "gpt-4o-mini") via chat.completions.
      * Processa a resposta em _analyze_script e retorna conteúdo + metadados.
  - analyze_existing_script(content, target_duration=10) -> Dict
      * Calcula métricas de acurácia de tamanho, estrutura, legibilidade e recomendações.
- Helpers:
  - _get_system_prompt / _get_audience_context / _get_style_context: moldam o tom.
  - _analyze_structure: detecta seções (padrão "═══ ... ═══"), timestamps [MM:SS],
    interações e conta instruções técnicas [TAGS].
  - _calculate_accuracy / _calculate_readability / _calculate_overall_score:
    compõem o score final ponderado (palavras 30%, estrutura 40%, legibilidade 30%).
  - _format_time: converte minutos em "M:SS".
  - _create_error_response: padroniza retorno em caso de exceção.

Dependências/Config:
- Requer variável de ambiente OPENAI_API_KEY.
- Modelo padrão: "gpt-4o-mini"; temperature=0.6; top_p=0.8; max_tokens ≈ 1.5 * palavras-alvo.
- Log via logging.getLogger(__name__).

Observações/limites:
- max_tokens usa uma estimativa em palavras (pode ultrapassar limites de tokens do modelo).
- Legibilidade é heurística simples (média de palavras por sentença).
- Regex de timestamps procura padrão básico "[m:ss]".

Uso rápido:
    service = ScriptService()
    result = service.generate_script(topic="Kubernetes básico", duration_minutes=8)
    roteiro = result["content"]  # texto final
    metricas = result["metadata"] # scores e flags

Integrações/relacionamentos:
- Serviço isolado; integra apenas com a API da OpenAI. Outros módulos podem importar
  ScriptService para gerar/avaliar roteiros em fluxos de criação de conteúdo.
"""

# app/services/script_service.py
import os
import re
import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)

class ScriptService:
    """Serviço para geração de roteiros profissionais"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.words_per_minute = 165  # Velocidade padrão de fala
        
    def generate_script(self, 
                       topic: str, 
                       duration_minutes: int = 10,
                       objectives: str = "",
                       audience: str = "geral",
                       style: str = "educativo",
                       include_interactions: bool = True) -> Dict[str, Any]:
        """Gera roteiro profissional com timing preciso"""
        
        try:
            # Calcula palavras alvo
            target_words = duration_minutes * self.words_per_minute
            
            # Constrói prompt profissional
            prompt = self._build_script_prompt(
                topic=topic,
                duration_minutes=duration_minutes,
                target_words=target_words,
                objectives=objectives,
                audience=audience,
                style=style,
                include_interactions=include_interactions
            )
            
            # Chama OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_system_prompt(style)
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.6,
                max_tokens=int(target_words * 1.5),  # Margem para formatação
                top_p=0.8
            )
            
            content = response.choices[0].message.content
            
            # Processa e analisa resultado
            result = self._analyze_script(
                content=content,
                topic=topic,
                duration_minutes=duration_minutes,
                target_words=target_words
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao gerar roteiro: {e}")
            return self._create_error_response(str(e))
    
    def _build_script_prompt(self, **kwargs) -> str:
        """Constrói prompt profissional para roteiro"""
        
        topic = kwargs["topic"]
        duration_minutes = kwargs["duration_minutes"]
        target_words = kwargs["target_words"]
        objectives = kwargs["objectives"]
        audience = kwargs["audience"]
        style = kwargs["style"]
        include_interactions = kwargs["include_interactions"]
        
        # Contextos específicos
        audience_context = self._get_audience_context(audience)
        style_context = self._get_style_context(style)
        
        prompt = f"""
TAREFA: Criar roteiro profissional para vídeo educativo

ESPECIFICAÇÕES:
- TÓPICO: {topic}
- DURAÇÃO: {duration_minutes} minutos EXATOS
- PALAVRAS ALVO: ~{target_words} palavras (165 palavras/minuto)
- AUDIÊNCIA: {audience_context}
- ESTILO: {style_context}
{f"- OBJETIVOS: {objectives}" if objectives else ""}

ESTRUTURA OBRIGATÓRIA COM TIMING:

═══ HOOK [0:00-{self._format_time(duration_minutes * 0.1)}] ═══
- Problema/curiosidade que prende atenção
- Estatística ou pergunta provocativa  
- Promessa clara do valor que será entregue
- Criar urgência para continuar assistindo
[Palavras alvo: ~{int(target_words * 0.1)}]

═══ INTRODUÇÃO [{self._format_time(duration_minutes * 0.1)}-{self._format_time(duration_minutes * 0.25)}] ═══
- Apresentação breve (se aplicável)
- Por que este tópico é importante AGORA
- Preview dos pontos principais
- Estabelecer credibilidade
[Palavras alvo: ~{int(target_words * 0.15)}]

═══ CONTEÚDO PRINCIPAL [{self._format_time(duration_minutes * 0.25)}-{self._format_time(duration_minutes * 0.9)}] ═══
- Dividir em 3-5 pontos principais
- Exemplos práticos e concretos
- Transições fluidas entre tópicos
- Recapitulações estratégicas
{"- Momentos de interação [INTERAÇÃO]" if include_interactions else ""}
[Palavras alvo: ~{int(target_words * 0.65)}]

═══ CONCLUSÃO [{self._format_time(duration_minutes * 0.9)}-{self._format_time(duration_minutes)}] ═══
- Resumo dos pontos principais
- Call-to-action específico e claro
- Próximos passos ou recursos
- Encerramento marcante
[Palavras alvo: ~{int(target_words * 0.1)}]

FORMATAÇÃO OBRIGATÓRIA:
✅ Use marcações de timing: [0:00-1:30]
✅ Inclua instruções técnicas: [PAUSA], [MOSTRAR TELA], [TOM: DIDÁTICO]
✅ Marque transições: [TRANSIÇÃO SUAVE]
✅ Destaque pontos importantes: **palavra**
✅ Linguagem conversacional e natural
{"✅ Inclua momentos [INTERAÇÃO] com público" if include_interactions else ""}

EXEMPLO DE ANOTAÇÃO:
[ENERGIA: ALTA - OLHAR DIRETO PARA CÂMERA]
Você já se perguntou por que...
[PAUSA - 2 segundos]
[MOSTRAR GRÁFICO: Estatística relevante]

ENTREGUE: Roteiro COMPLETO e PRONTO PARA GRAVAÇÃO com {target_words} palavras aproximadamente.
"""
        
        return prompt
    
    def _get_system_prompt(self, style: str) -> str:
        """System prompt baseado no estilo"""
        
        base = "Você é um roteirista profissional especializado em conteúdo educativo para vídeo."
        
        style_prompts = {
            "educativo": "Foque em clareza didática, exemplos práticos e progressão lógica.",
            "casual": "Use linguagem descontraída, humor apropriado e conecte com experiências cotidianas.",
            "formal": "Mantenha tom profissional, terminologia técnica e estrutura acadêmica.",
            "motivacional": "Inspire ação, use histórias pessoais e foque na transformação.",
            "tutorial": "Seja extremamente prático, passo-a-passo, e antecipe dúvidas comuns."
        }
        
        return f"{base} {style_prompts.get(style, style_prompts['educativo'])}"
    
    def _get_audience_context(self, audience: str) -> str:
        """Contexto da audiência"""
        
        contexts = {
            "iniciantes": "Beginners - use linguagem acessível, defina termos técnicos",
            "intermediários": "Intermediate - pode assumir conhecimento básico",
            "avançados": "Advanced - use terminologia técnica, foque em insights únicos",
            "profissionais": "Professionals - seja direto, foque em aplicabilidade no trabalho",
            "estudantes": "Students - conecte com currículo acadêmico",
            "geral": "General audience - equilibre acessibilidade com profundidade"
        }
        
        return contexts.get(audience, contexts["geral"])
    
    def _get_style_context(self, style: str) -> str:
        """Contexto do estilo"""
        
        contexts = {
            "educativo": "Educational - didático, estruturado, com recapitulações",
            "casual": "Casual - descontraído, linguagem coloquial, humor apropriado",
            "formal": "Formal - profissional, estrutura acadêmica, linguagem técnica",
            "motivacional": "Motivational - inspirador, storytelling, call-to-action forte",
            "tutorial": "Tutorial - prático, passo-a-passo, orientado a resultado"
        }
        
        return contexts.get(style, contexts["educativo"])
    
    def _analyze_script(self, content: str, topic: str, duration_minutes: int, target_words: int) -> Dict[str, Any]:
        """Analisa qualidade do roteiro gerado"""
        
        # Métricas básicas
        actual_words = len(content.split())
        estimated_duration = actual_words / self.words_per_minute
        word_accuracy = self._calculate_accuracy(actual_words, target_words)
        
        # Análise estrutural
        structure_analysis = self._analyze_structure(content)
        
        # Score de legibilidade
        readability = self._calculate_readability(content)
        
        # Score geral
        overall_score = self._calculate_overall_score(
            word_accuracy, 
            structure_analysis["score"], 
            readability
        )
        
        return {
            "content": content.strip(),
            "score": overall_score,
            "metadata": {
                "topic": topic,
                "target_duration_minutes": duration_minutes,
                "estimated_duration_minutes": round(estimated_duration, 1),
                "target_words": target_words,
                "actual_words": actual_words,
                "word_accuracy": word_accuracy,
                "structure_score": structure_analysis["score"],
                "sections_found": structure_analysis["sections"],
                "has_timestamps": structure_analysis["timestamps"],
                "has_interactions": structure_analysis["interactions"],
                "readability_score": readability,
                "model_used": "gpt-4o-mini",
                "generation_timestamp": int(datetime.now().timestamp())
            }
        }
    
    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """Analisa estrutura do roteiro"""
        
        # Conta seções principais
        sections = len(re.findall(r'═══.*═══', content))
        
        # Verifica timestamps
        timestamps = bool(re.search(r'\[\d+:\d+', content))
        
        # Verifica interações
        interactions = bool(re.search(r'\[INTERAÇÃO\]|\[PERGUNTA\]', content, re.IGNORECASE))
        
        # Verifica instruções técnicas
        technical_notes = len(re.findall(r'\[([A-Z][^]]*)\]', content))
        
        # Score estrutural (0-100)
        score_components = [
            sections >= 3,      # Pelo menos 3 seções
            timestamps,         # Tem marcações de tempo
            technical_notes >= 5, # Pelo menos 5 instruções técnicas
            len(content) > 1000  # Conteúdo substancial
        ]
        
        structure_score = sum(score_components) * 25
        
        return {
            "score": structure_score,
            "sections": sections,
            "timestamps": timestamps,
            "interactions": interactions,
            "technical_notes": technical_notes
        }
    
    def _calculate_accuracy(self, actual: int, target: int) -> int:
        """Calcula precisão das palavras"""
        if target == 0:
            return 0
        deviation = abs(actual - target) / target
        return max(0, int((1 - deviation) * 100))
    
    def _calculate_readability(self, text: str) -> int:
        """Calcula score de legibilidade"""
        sentences = len(re.split(r'[.!?]+', text))
        words = len(text.split())
        
        if sentences == 0:
            return 0
        
        avg_sentence_length = words / sentences
        
        # Para roteiros, 12-18 palavras por sentença é ideal
        if 12 <= avg_sentence_length <= 18:
            return 90
        elif 8 <= avg_sentence_length <= 22:
            return 70
        else:
            return max(0, int(100 - abs(avg_sentence_length - 15) * 3))
    
    def _calculate_overall_score(self, word_accuracy: int, structure_score: int, readability: int) -> int:
        """Calcula score geral ponderado"""
        
        weights = {
            "words": 0.3,      # 30% - Precisão de palavras
            "structure": 0.4,  # 40% - Estrutura
            "readability": 0.3 # 30% - Legibilidade
        }
        
        final_score = (
            word_accuracy * weights["words"] +
            structure_score * weights["structure"] +
            readability * weights["readability"]
        )
        
        return int(final_score)
    
    def _format_time(self, minutes: float) -> str:
        """Formata minutos para MM:SS"""
        total_seconds = int(minutes * 60)
        mins = total_seconds // 60
        secs = total_seconds % 60
        return f"{mins}:{secs:02d}"
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Resposta de erro padronizada"""
        return {
            "content": f"Erro na geração do roteiro: {error_message}",
            "score": 0,
            "metadata": {
                "error": True,
                "error_message": error_message,
                "generation_timestamp": int(datetime.now().timestamp())
            }
        }
    
    def analyze_existing_script(self, content: str, target_duration: int = 10) -> Dict[str, Any]:
        """Analisa um roteiro existente"""
        
        words = len(content.split())
        target_words = target_duration * self.words_per_minute
        estimated_duration = words / self.words_per_minute
        
        word_accuracy = self._calculate_accuracy(words, target_words)
        structure_analysis = self._analyze_structure(content)
        readability = self._calculate_readability(content)
        
        # Gera recomendações
        recommendations = []
        
        if word_accuracy < 80:
            if words < target_words * 0.8:
                recommendations.append("Roteiro muito curto - adicione mais conteúdo")
            else:
                recommendations.append("Roteiro muito longo - considere editar para ser mais conciso")
        
        if structure_analysis["score"] < 75:
            recommendations.append("Melhore a estrutura: adicione seções claras com timing")
        
        if not structure_analysis["timestamps"]:
            recommendations.append("Adicione marcações de tempo para facilitar gravação")
        
        if readability < 70:
            recommendations.append("Use sentenças mais curtas para melhor legibilidade")
        
        return {
            "word_count": words,
            "estimated_duration": round(estimated_duration, 1),
            "target_duration": target_duration,
            "accuracy_percentage": word_accuracy,
            "structure_score": structure_analysis["score"],
            "readability_score": readability,
            "sections_identified": structure_analysis["sections"],
            "has_timestamps": structure_analysis["timestamps"],
            "has_interactions": structure_analysis["interactions"],
            "recommendations": recommendations
        }