/**
 * src/hooks/useScriptGenerator.ts
 *
 * Hook React para consumir as rotas de roteiros da API (script_router).
 *
 * 🔗 Ligação com backend:
 * - POST /generate-script → conecta com ScriptService.generate_script()
 *   Campos enviados (ScriptRequest):
 *     • topic             → "Tópico do vídeo"
 *     • duration_minutes  → "Duração (minutos)"
 *     • objectives        → "Descrição/Objetivos" (campo extra do layout)
 *     • target_audience   → "Audiência alvo" (geral, iniciantes, etc.)
 *     • script_style      → "Estilo" (educativo, casual, motivacional, etc.)
 *     • include_interactions → incluir [INTERAÇÃO] no roteiro
 *     • model (opcional)  → permite escolher modelo do OpenAI (ex.: gpt-4o-mini)
 *
 *   ⚠️ Se alterar ScriptRequest no back (script_router.py), atualizar esta interface também.
 *
 * - POST /analyze-script → conecta com ScriptService.analyze_existing_script()
 *   Retorna métricas de qualidade e recomendações.
 *
 * - GET /script-templates → retorna templates e guias de timing (estático no router).
 * - GET /script-styles    → retorna estilos disponíveis (estático no router).
 *
 * Estados internos:
 * - loading → indica chamada em andamento
 * - error → guarda mensagem de erro da API
 * - generatedScript → último roteiro gerado (conteúdo + metadata)
 *
 * Métodos expostos:
 * - generateScript(request: ScriptRequest) → gera novo roteiro
 * - analyzeScript(content, targetDuration) → analisa roteiro existente
 * - getTemplates() → busca templates pré-definidos
 * - getStyles() → busca estilos disponíveis
 * - clearError() / clearScript() → resetam estado local
 */

import { useState } from 'react';
import { http } from '@/lib/api';

interface ScriptRequest {
  topic: string;
  duration_minutes: number;
  objectives?: string;          // <- corresponde ao campo "Descrição/Objetivos" no layout
  target_audience: string;
  script_style: string;
  include_interactions: boolean;
  model?: string;
}

interface ScriptMetadata {
  topic: string;
  target_duration_minutes: number;
  estimated_duration_minutes: number;
  target_words: number;
  actual_words: number;
  word_accuracy: number;
  structure_score: number;
  sections_found: number;
  has_timestamps: boolean;
  has_interactions: boolean;
  readability_score: number;
  model_used: string;
}

interface GeneratedScript {
  content: string;
  score: number;
  metadata: ScriptMetadata;
}

interface ScriptResponse {
  success: boolean;
  message: string;
  script?: GeneratedScript;
}

export const useScriptGenerator = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedScript, setGeneratedScript] = useState<GeneratedScript | null>(null);

  const generateScript = async (request: ScriptRequest): Promise<ScriptResponse> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await http.post<ScriptResponse>('/generate-script', request);
      
      if (response.data.success && response.data.script) {
        setGeneratedScript(response.data.script);
      } else {
        setError(response.data.message);
      }
      
      return response.data;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Erro ao gerar roteiro';
      setError(errorMessage);
      return {
        success: false,
        message: errorMessage
      };
    } finally {
      setLoading(false);
    }
  };

  const analyzeScript = async (content: string, targetDuration: number = 10) => {
    try {
      const response = await http.post('/analyze-script', {
        content,
        target_duration: targetDuration
      });
      return response.data;
    } catch (err: any) {
      console.error('Erro ao analisar roteiro:', err);
      return null;
    }
  };

  const getTemplates = async () => {
    try {
      const response = await http.get('/script-templates');
      return response.data;
    } catch (err: any) {
      console.error('Erro ao buscar templates:', err);
      return null;
    }
  };

  const getStyles = async () => {
    try {
      const response = await http.get('/script-styles');
      return response.data;
    } catch (err: any) {
      console.error('Erro ao buscar estilos:', err);
      return null;
    }
  };

  const clearError = () => setError(null);
  const clearScript = () => setGeneratedScript(null);

  return {
    loading,
    error,
    generatedScript,
    generateScript,
    analyzeScript,
    getTemplates,
    getStyles,
    clearError,
    clearScript
  };
};
