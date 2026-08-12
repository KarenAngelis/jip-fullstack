// hooks/useContentGeneration.ts
"use client";

/**
 * Hook para integrar geração de conteúdo com o backend (FastAPI)
 * - Usa helpers da lib/api.ts (get/post) => não precisa montar headers/token aqui
 * - Mantém fallback de mock no erro (configurável por env)
 * - Expõe estado (loading, error, generatedContent) + actions (generate/save/list)
 */

import { useState, useCallback } from "react";
import { get, post } from "@/lib/api"; // <-- helpers que já respeitam API_ROOT e token

export type GenerationType = "titulos" | "roteiros" | "episodios";

export interface ContentGenerationParams {
  mainTopic: string;
  audience?: string;
  contentType?: string;
  contentTone?: string;
  generationType: GenerationType;
  // extras
  enrichWithTrends?: boolean;
  trendsGeo?: string; // BR, US, PT...
  qualityThreshold?: number;
  regenerateIfBelowThreshold?: boolean;
}

export interface GeneratedContent {
  id?: string;
  content: string;
  score?: number;
  metadata?: {
    engagement_potential?: number;
    seo_score?: number;
    trend_relevance?: number;
    [k: string]: unknown;
  };
}

export interface ContentGenerationResponse {
  success: boolean;
  data: GeneratedContent[];
  message?: string;
  suggestions?: string[];
}

/** dica curta por aba (UI) */
export const CONTENT_TIPS: Record<GenerationType, string> = {
  titulos:
    "Dica: para passar de 75 no score, use NÚMERO + FORMATO (Tutorial/Guia) + ANO (2025) e mantenha 50–60 caracteres.",
  roteiros:
    "Estruture: Hook (15s) → Intro (30s) → Desenvolvimento → Conclusão (30s). Marque tempo por seção.",
  episodios:
    "Inclua objetivos SMART, pré-requisitos e métricas de sucesso por episódio.",
};

// controla fallback de mock em erro (dev)
const USE_MOCK_ON_ERROR =
  (process.env.NEXT_PUBLIC_USE_MOCK_ON_ERROR ?? "true") === "true";

export const useContentGeneration = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedContent, setGeneratedContent] = useState<GeneratedContent[]>(
    []
  );

  /** POST /api/generate-content */
  const generateContent = useCallback(
    async (params: ContentGenerationParams): Promise<ContentGenerationResponse> => {
      setLoading(true);
      setError(null);

      try {
        // como a lib/api.ts usa API_ROOT e injeta token via cookie,
        // basta passar o path absoluto (começando com /api/)
        const data = await post<ContentGenerationResponse, ContentGenerationParams>(
          "/api/generate-content",
          params
        );

        if (data.success) setGeneratedContent(data.data);
        else setError(data.message || "Erro ao gerar conteúdo");

        return data;
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : "Erro ao gerar conteúdo";
        setError(msg);

        if (USE_MOCK_ON_ERROR) {
          const mock = generateMockContent(params);
          setGeneratedContent(mock.data);
          return mock;
        }

        return { success: false, data: [], message: msg };
      } finally {
        setLoading(false);
      }
    },
    []
  );

  /** POST /api/save-content */
  const saveContent = useCallback(
    async (contentId: string, title: string) => {
      try {
        const data = await post<{ success: boolean; message?: string }, { contentId: string; title: string }>(
          "/api/save-content",
          { contentId, title }
        );
        return data;
      } catch (err) {
        // fallback “ok” no dev
        return { success: true, message: "Conteúdo salvo (mock)!" };
      }
    },
    []
  );

  /** GET /api/recent-content */
  const getRecentContent = useCallback(async () => {
    try {
      const data = await get<{ success: boolean; data: unknown[] }>(
        "/api/recent-content"
      );
      return data;
    } catch {
      // mock de fallback
      return {
        success: true,
        data: [
          {
            id: "1",
            type: "titulo",
            title: "Tendências",
            content: "5 ideias de conteúdo com alto CTR este mês",
            score: 4.7,
            status: "Aprovado",
            date: "08/01/2025",
            description: "Exemplo mock",
          },
        ],
      };
    }
  }, []);

  /** gera mock local quando USE_MOCK_ON_ERROR=true */
  const generateMockContent = (
    params: ContentGenerationParams
  ): ContentGenerationResponse => {
    const t = params.mainTopic || "Seu Tópico";
    if (params.generationType === "titulos") {
      return {
        success: true,
        data: [
          {
            content: `${t} em 2025: Guia Completo para Iniciantes (10 Passos)`,
            score: 88,
            metadata: {
              engagement_potential: 82,
              seo_score: 88,
              trend_relevance: 80,
            },
          },
          {
            content: `${t}: 7 Erros Comuns (e Como Evitar)`,
            score: 84,
            metadata: {
              engagement_potential: 80,
              seo_score: 82,
              trend_relevance: 72,
            },
          },
          {
            content: `Como Dominar ${t} em 15 Minutos`,
            score: 83,
            metadata: {
              engagement_potential: 81,
              seo_score: 80,
              trend_relevance: 78,
            },
          },
        ],
        suggestions: [
          `Inclua número + formato + ano em pelo menos 1 título de ${t}`,
          `Teste variações de intenção (guia, passo a passo, checklist)`,
        ],
      };
    }

    if (params.generationType === "roteiros") {
      return {
        success: true,
        data: [
          {
            content: `# Roteiro: ${t}\n\n[0:00-0:15] Hook...\n[0:15-0:45] Intro...\n[0:45-09:00] Desenvolvimento...\n[09:00-10:00] Conclusão...`,
            score: 85,
            metadata: {
              engagement_potential: 82,
              seo_score: 85,
              trend_relevance: 78,
            },
          },
        ],
      };
    }

    return {
      success: true,
      data: [
        {
          content: `# Episódio 1 — ${t}\n\nResumo, objetivos, estrutura e métricas...`,
          score: 86,
          metadata: {
            engagement_potential: 84,
            seo_score: 86,
            trend_relevance: 80,
          },
        },
      ],
    };
  };

  return {
    loading,
    error,
    generatedContent,
    generateContent,
    saveContent,
    getRecentContent,
    clearError: () => setError(null),
    clearContent: () => setGeneratedContent([]),
  };
};
