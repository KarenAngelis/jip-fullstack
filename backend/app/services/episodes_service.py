# app/services/episodes_service.py
"""
Service para geração de episódios usando OpenAI.
Versão com suporte a storytelling pessoal.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)

class EpisodesAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def generate_episode_content(
        self, 
        titulo: str, 
        tipo_serie: str, 
        numero_episodio: int,
        contexto_insights: List[Dict] = None,
        duracao_estimada: int = 15,
        historia_pessoal: Optional[str] = None,
        buscar_dados_reais: bool = True,
        nivel_controversia: str = "moderado"
    ) -> Dict[str, Any]:
        """
        Gera conteúdo completo do episódio usando ChatGPT com storytelling pessoal
        """
        try:
            # Constrói o prompt estruturado com história pessoal
            prompt = self._build_episode_prompt(
                titulo=titulo, 
                tipo_serie=tipo_serie, 
                numero_episodio=numero_episodio, 
                contexto_insights=contexto_insights, 
                duracao_estimada=duracao_estimada,
                historia_pessoal=historia_pessoal,
                buscar_dados_reais=buscar_dados_reais,
                nivel_controversia=nivel_controversia
            )
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.8 if historia_pessoal else 0.7,  # Mais criativo se tem história
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            return self._parse_episode_response(content)
            
        except Exception as e:
            logger.error(f"Erro ao gerar episódio: {e}")
            # Fallback com estrutura padrão
            return self._generate_fallback_episode(titulo, tipo_serie, numero_episodio, duracao_estimada, historia_pessoal)
    
    def _get_system_prompt(self) -> str:
        """Prompt do sistema melhorado para episódios com storytelling"""
        return """
        Você é um especialista em storytelling e criação de conteúdo viral para podcasts e vídeos.
        
        SUAS ESPECIALIDADES:
        - Transformar histórias pessoais em narrativas cativantes e específicas
        - Criar ganchos emocionais que prendem a atenção nos primeiros 30 segundos
        - Desenvolver roteiros com timing preciso e momentos de alta emoção
        - Gerar CTAs estratégicos que convertem audiência em ação
        - Usar dados e estatísticas de forma impactante
        
        PRINCÍPIOS DE STORYTELLING VIRAL:
        - ESPECIFICIDADE: Use números, datas, valores, nomes concretos
        - EMOÇÃO: Crie momentos de tensão, surpresa, alívio, inspiração
        - PROGRESSÃO: Problema → Luta → Descoberta → Transformação → Lição
        - UNIVERSALIDADE: Conecte experiência pessoal com problemas universais
        - AUTENTICIDADE: Mantenha tom genuíno e vulnerável quando apropriado
        
        TIPOS DE SÉRIE E ABORDAGENS:
        - Motivacional: História de superação + lições práticas + desafio inspirador
        - Tutorial: Problema real + solução testada + passos específicos
        - Tendências: Insight pessoal + dados de mercado + previsões acionáveis
        - Review: Experiência real + critérios claros + comparação honesta
        - Notícias: Perspectiva única + contexto pessoal + impacto prático
        - Entretenimento: Situação curiosa + desenvolvimento divertido + moral da história
        
        ESTRUTURA DE RESPOSTA OBRIGATÓRIA (JSON):
        {
            "outline": {
                "introducao": "gancho emocional/estatística + contexto + preview",
                "desenvolvimento": [
                    "Ponto 1: contexto/problema específico",
                    "Ponto 2: história pessoal detalhada",
                    "Ponto 3: lição/insight descoberto", 
                    "Ponto 4: aplicação prática universal"
                ],
                "conclusao": "resumo transformacional + CTA + gancho próximo episódio"
            },
            "roteiro": {
                "abertura": "script de 30-60s com gancho forte",
                "blocos": [
                    {
                        "titulo": "nome descritivo do bloco",
                        "conteudo": "script completo com emoções marcadas",
                        "tempo_estimado": "X minutos"
                    }
                ],
                "encerramento": "script com múltiplos CTAs estratégicos"
            },
            "metadados": {
                "tempo_total_estimado": "X minutos",
                "principais_ctas": ["CTA específico 1", "CTA específico 2"],
                "hashtags_sugeridas": ["#hashtag1", "#hashtag2"],
                "pontos_chave": ["insight específico 1", "insight específico 2"]
            }
        }
        """
    
    def _build_episode_prompt(
        self, 
        titulo: str, 
        tipo_serie: str, 
        numero_episodio: int,
        contexto_insights: List[Dict] = None,
        duracao_estimada: int = 15,
        historia_pessoal: Optional[str] = None,
        buscar_dados_reais: bool = True,
        nivel_controversia: str = "moderado"
    ) -> str:
        """Constrói prompt com storytelling pessoal integrado"""
        
        # Seção de história pessoal
        storytelling_section = ""
        if historia_pessoal and historia_pessoal.strip():
            storytelling_section = f"""
            
🎭 HISTÓRIA PESSOAL OBRIGATÓRIA PARA USAR:
"{historia_pessoal}"

IMPORTANTE: Esta história DEVE ser usada como elemento central do episódio.
- Torne-a específica com detalhes emocionais
- Use números, datas, situações concretas
- Conecte com a lição universal do tema
- Crie tensão narrativa até a resolução
            """
        else:
            storytelling_section = f"""
            
⚠️ CRIAR HISTÓRIA PESSOAL ESPECÍFICA:
Como não foi fornecida história pessoal, você DEVE criar uma história detalhada e realista 
sobre alguém que enfrentou desafios relacionados a "{titulo}".

Use: números específicos, datas aproximadas, situações concretas, emoções reais.
Exemplo: "Em março de 2019, eu tinha apenas R$ 247 na conta e duas filhas pequenas..."
            """
        
        # Contexto de insights
        contexto_texto = ""
        if contexto_insights:
            contexto_texto = "\n\n📊 INSIGHTS DISPONÍVEIS:\n"
            for insight in contexto_insights[:3]:
                contexto_texto += f"- {insight.get('titulo', 'N/A')}: {insight.get('resumo', insight.get('descricao', 'N/A'))}\n"
        
        # Nível de controvérsia
        controversia_map = {
            "conservador": "Mantenha abordagem segura e consensual",
            "moderado": "Inclua 1-2 perspectivas que desafiem o senso comum de forma respeitosa",
            "alto": "Seja provocativo! Questione verdades aceitas e apresente ângulos polêmicos (mas respeitosos)"
        }
        controversia_instruction = controversia_map.get(nivel_controversia, controversia_map["moderado"])
        
        # Estratégias por tipo
        estrategias_tipo = {
            "motivacional": f"""
            FÓRMULA MOTIVACIONAL VIRAL:
            - Abertura: Estatística emocional + gancho pessoal
            - Desenvolvimento: História de luta → Momento de virada → Transformação
            - CTAs: Desafio específico de 7 dias + compartilhamento da história
            - Tom: Inspirador, vulnerável, empoderador
            - {controversia_instruction}
            """,
            "tutorial": f"""
            FÓRMULA TUTORIAL VIRAL:
            - Abertura: Resultado específico que será alcançado
            - Desenvolvimento: Erro que cometi → Como descobri a solução → Passos exatos
            - CTAs: Implementação imediata + compartilhamento do resultado
            - Tom: Didático, confiante, prático
            - {controversia_instruction}
            """,
            "tendências": f"""
            FÓRMULA TENDÊNCIAS VIRAL:
            - Abertura: Dados surpreendentes + insight pessoal
            - Desenvolvimento: O que observei → Análise do mercado → Previsões ousadas
            - CTAs: Ação para aproveitar a tendência + discussão nos comentários
            - Tom: Analítico, visionário, provocativo
            - {controversia_instruction}
            """,
            "review": f"""
            FÓRMULA REVIEW VIRAL:
            - Abertura: Expectativa vs realidade
            - Desenvolvimento: Teste real → Descobertas inesperadas → Veredicto honesto
            - CTAs: Decisão baseada no perfil + pergunta para audiência
            - Tom: Honesto, detalhado, imparcial
            - {controversia_instruction}
            """,
            "notícias": f"""
            FÓRMULA NOTÍCIAS VIRAL:
            - Abertura: Fato + perspectiva única pessoal
            - Desenvolvimento: Contexto que mídia não conta → Impacto real → Opinião fundamentada
            - CTAs: Discussão informada + compartilhamento consciente
            - Tom: Informativo, crítico, contextual
            - {controversia_instruction}
            """,
            "entretenimento": f"""
            FÓRMULA ENTRETENIMENTO VIRAL:
            - Abertura: Situação bizarra/engraçada real
            - Desenvolvimento: Como aconteceu → Desdobramentos → Lição divertida
            - CTAs: Compartilhar história similar + interação divertida
            - Tom: Autêntico, divertido, espontâneo
            - {controversia_instruction}
            """
        }
        
        estrategia = estrategias_tipo.get(tipo_serie.lower(), estrategias_tipo["motivacional"])
        
        prompt = f"""
CRIE UM EPISÓDIO VIRAL COM STORYTELLING IMPACTANTE:

📋 BRIEFING COMPLETO:
- Título: "{titulo}"
- Tipo: {tipo_serie}
- Episódio: #{numero_episodio}
- Duração: {duracao_estimada} minutos
- Controvérsia: {nivel_controversia}

{storytelling_section}

{contexto_texto}

🎯 ESTRATÉGIA ESPECÍFICA:
{estrategia}

🚀 REQUISITOS VIRAIS OBRIGATÓRIOS:

1. GANCHO PODEROSO (30 segundos):
   - Estatística surpreendente OU pergunta provocativa OU história chocante
   - Preview específico do que o ouvinte vai descobrir
   - Promessa de transformação concreta

2. STORYTELLING ESTRUTURADO:
   - Use a história pessoal como COLUNA VERTEBRAL do episódio
   - Crie TENSÃO narrativa com problema específico
   - Momento de DESCOBERTA/VIRADA clara
   - LIÇÃO universal aplicável por todos

3. ELEMENTOS DE ENGAJAMENTO:
   - 2-3 momentos de interação direta com audiência
   - Pausas estratégicas para reflexão
   - Perguntas retóricas que geram pensamento

4. CTAS ESTRATÉGICOS:
   - CTA de engajamento (comentário/like) no minuto 3-4
   - CTA de ação (implementar algo) no final do desenvolvimento  
   - CTA de crescimento (inscrição/compartilhamento) no encerramento

5. DIFERENCIAÇÃO:
   - Pelo menos 1 perspectiva que desafia o senso comum
   - Ângulo único que ninguém está abordando
   - Insights baseados em experiência real

ENTREGUE conteúdo que faz as pessoas pararem de scrollar e prestarem atenção!
        """
        
        return prompt
    
    def _parse_episode_response(self, content: str) -> Dict[str, Any]:
        """Parse com validação aprimorada para storytelling"""
        try:
            # Limpeza do conteúdo
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Parse do JSON
            parsed = json.loads(content)
            
            # Validação estrutural
            required_keys = ["outline", "roteiro", "metadados"]
            if not all(key in parsed for key in required_keys):
                raise ValueError("Estrutura JSON incompleta")
            
            # Validações específicas para storytelling
            self._validate_storytelling_content(parsed)
            
            return parsed
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Resposta inválida, usando fallback: {e}")
            return self._extract_content_from_text(content)
    
    def _validate_storytelling_content(self, parsed: Dict[str, Any]) -> None:
        """Valida se o conteúdo tem elementos de storytelling adequados"""
        roteiro = parsed.get("roteiro", {})
        
        # Garante que tem blocos suficientes
        if not roteiro.get("blocos") or len(roteiro["blocos"]) < 2:
            logger.warning("Roteiro sem blocos suficientes para storytelling")
        
        # Enriquece metadados se necessário
        metadados = parsed.get("metadados", {})
        if not metadados.get("pontos_chave"):
            metadados["pontos_chave"] = self._extract_key_points(parsed)
        
        # Garante CTAs se não existem
        if not metadados.get("principais_ctas"):
            metadados["principais_ctas"] = [
                "Compartilhe sua história nos comentários",
                "Inscreva-se para mais episódios",
                "Marque alguém que precisa ouvir isso"
            ]
    
    def _generate_fallback_episode(
        self, 
        titulo: str, 
        tipo_serie: str, 
        numero_episodio: int, 
        duracao_estimada: int,
        historia_pessoal: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fallback melhorado com storytelling básico"""
        logger.warning("Usando episódio fallback com storytelling")
        
        # Use história pessoal no fallback se disponível
        storytelling_block = ""
        if historia_pessoal:
            storytelling_block = f"Quero compartilhar uma experiência pessoal: {historia_pessoal[:200]}..."
        else:
            storytelling_block = f"Deixe-me contar uma história real sobre {titulo} que mudou minha perspectiva."
        
        return {
            "outline": {
                "introducao": f"Você sabia que a maioria das pessoas luta com {titulo}? Hoje vou compartilhar minha experiência pessoal e como isso pode transformar sua abordagem.",
                "desenvolvimento": [
                    f"O desafio universal com {titulo}",
                    "Minha história pessoal e o momento de mudança",
                    "As lições que aprendi no processo",
                    "Como você pode aplicar isso na sua vida"
                ],
                "conclusao": "Agora você tem uma nova perspectiva. Sua missão é implementar uma coisa hoje mesmo. No próximo episódio, vamos aprofundar ainda mais."
            },
            "roteiro": {
                "abertura": f"Você já se sentiu perdido com {titulo}? Eu já. E hoje vou contar exatamente como superei isso e como você pode fazer o mesmo. Fique até o final porque vou compartilhar algo que pode mudar tudo para você.",
                "blocos": [
                    {
                        "titulo": "O Problema Real",
                        "conteudo": f"Vamos começar sendo honestos: {titulo} é um desafio para a maioria de nós. E não é por falta de vontade.",
                        "tempo_estimado": f"{duracao_estimada // 4} minutos"
                    },
                    {
                        "titulo": "Minha História",
                        "conteudo": storytelling_block,
                        "tempo_estimado": f"{duracao_estimada // 2} minutos"
                    },
                    {
                        "titulo": "A Transformação",
                        "conteudo": "O que mudou tudo foi entender que pequenas ações consistentes superam grandes planos mal executados.",
                        "tempo_estimado": f"{duracao_estimada // 4} minutos"
                    }
                ],
                "encerramento": "Se essa história fez sentido para você, deixe um comentário contando sua experiência. Inscreva-se no canal e compartilhe com alguém que está passando pelo mesmo. Seu apoio faz toda diferença!"
            },
            "metadados": {
                "tempo_total_estimado": f"{duracao_estimada} minutos",
                "principais_ctas": [
                    "Compartilhe sua experiência nos comentários",
                    "Inscreva-se para mais histórias reais",
                    "Marque alguém que precisa ouvir isso"
                ],
                "hashtags_sugeridas": [
                    f"#{tipo_serie}",
                    "#storytelling",
                    "#experienciapessoal",
                    "#transformacao",
                    "#vidareal"
                ],
                "pontos_chave": [
                    "Experiência pessoal autêntica",
                    "Lições práticas aplicáveis",
                    "Conexão emocional genuína"
                ]
            }
        }
    
    # Métodos auxiliares mantidos do código original
    def _extract_content_from_text(self, text: str) -> Dict[str, Any]:
        """Extrai conteúdo estruturado de texto não-JSON"""
        lines = text.split('\n')
        
        return {
            "outline": {
                "introducao": "Introdução com storytelling baseada no conteúdo gerado",
                "desenvolvimento": self._extract_development_points(lines),
                "conclusao": "Conclusão inspiradora com call to action"
            },
            "roteiro": {
                "abertura": text[:300] + "...",
                "blocos": [
                    {
                        "titulo": "História Principal",
                        "conteudo": text,
                        "tempo_estimado": "10-12 minutos"
                    }
                ],
                "encerramento": "Obrigado por ouvir minha história! Compartilhe a sua nos comentários."
            },
            "metadados": {
                "tempo_total_estimado": "15 minutos",
                "principais_ctas": ["Compartilhe sua história", "Inscreva-se", "Deixe um like"],
                "hashtags_sugeridas": ["#storytelling", "#experienciapessoal", "#viral"],
                "pontos_chave": self._extract_key_points_from_text(text)
            }
        }
    
    def _extract_section(self, lines: List[str], section: str) -> Optional[str]:
        """Extrai seção específica do texto"""
        section_lower = section.lower()
        for i, line in enumerate(lines):
            if section_lower in line.lower():
                content_lines = lines[i+1:i+4]
                return " ".join([l.strip() for l in content_lines if l.strip()])
        return None
    
    def _extract_development_points(self, lines: List[str]) -> List[str]:
        """Extrai pontos de desenvolvimento"""
        points = []
        for line in lines:
            line = line.strip()
            if line.startswith(('-', '•', '1.', '2.', '3.', '4.')):
                points.append(line[2:].strip())
        
        if not points:
            points = [
                "Contexto pessoal do tema",
                "Momento de descoberta",
                "Lições aprendidas",
                "Aplicação prática"
            ]
        
        return points[:4]
    
    def _extract_key_points_from_text(self, text: str) -> List[str]:
        """Extrai pontos-chave com foco em storytelling"""
        sentences = text.split('.')
        key_points = []
        
        storytelling_keywords = ['história', 'experiência', 'descobri', 'aprendi', 'transformou', 'mudança']
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in storytelling_keywords):
                clean_sentence = sentence.strip()
                if 10 < len(clean_sentence) < 100:
                    key_points.append(clean_sentence)
        
        if not key_points:
            key_points = [
                "História pessoal autêntica",
                "Lições práticas aplicáveis",
                "Conexão emocional real"
            ]
        
        return key_points[:5]
    
    def _extract_key_points(self, parsed_content: Dict) -> List[str]:
        """Extrai pontos-chave do conteúdo parsed"""
        points = []
        
        if isinstance(parsed_content.get("outline", {}).get("desenvolvimento"), list):
            points.extend(parsed_content["outline"]["desenvolvimento"][:3])
        
        while len(points) < 3:
            points.append("Insight importante sobre storytelling")
        
        return points
    
    def generate_quick_summary(self, titulo: str, tipo_serie: str) -> str:
        """Gera resumo com foco em storytelling"""
        try:
            prompt = f"""
            Crie um resumo atrativo de 2-3 linhas para um episódio de {tipo_serie} 
            sobre "{titulo}" que usa storytelling pessoal.
            
            O resumo deve:
            - Despertar curiosidade sobre a história pessoal
            - Prometer transformação/lição específica
            - Usar linguagem emocional e próxima
            - Incluir elemento de suspense ou surpresa
            
            Exemplo: "A história de como perdi tudo em 2019 e o que descobri nos 6 meses 
            seguintes mudou completamente minha visão sobre sucesso. Prepare-se para 
            questionar tudo que você acredita."
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {e}")
            fallbacks = {
                "motivacional": f"História pessoal sobre {titulo} que vai inspirar você a ver as coisas de forma diferente.",
                "tutorial": f"Como descobri na prática o melhor jeito de {titulo} - e como você pode replicar.",
                "tendências": f"Minha experiência com {titulo} revela tendências que poucos estão percebendo.",
                "review": f"Testei {titulo} na vida real - os resultados vão te surpreender.",
                "notícias": f"Minha perspectiva única sobre {titulo} e o que isso muda para todos nós.",
                "entretenimento": f"A história bizarra sobre {titulo} que aconteceu comigo e mudou tudo."
            }
            
            return fallbacks.get(tipo_serie.lower(), f"História real sobre {titulo} que você precisa ouvir.")