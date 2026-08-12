// web/src/lib/episodes.ts
// ------------------------------------------------------------------
// LIB (SDK) para "sugestões de episódios"
// - Usa os helpers get/post já configurados em "@/lib/api" (cookies/token).
// - Tipos baseados na resposta real da API de episode-suggestions
// ------------------------------------------------------------------

import { get, post } from "@/lib/api";

/** ===== Tipos do contrato baseados na API real ===== */
export interface EpisodeSuggestionRequest {
  title: string;
  context: string;
  personal_input?: string;
  target_audience?: string;
  episode_format?: string;
}

export interface GuestSuggestion {
  name: string;
  expertise: string;
  relevance_score: number;
  justification: string;
  contact_suggestion: string;
}

export interface JipTrendAnalysis {
  trend_score: number;
  market_direction: string;
  competition_level: string;
  growth_prediction: number;
  opportunity_level: string;
}

export interface JipLegalAnalysis {
  status: string;
  confidence_score: number;
  issues_found: string[];
  recommendations: string[];
  risk_level: string;
}

export interface JipMarketAnalysis {
  audience_interest: number;
  content_saturation: string;
  best_timing: string;
  estimated_reach: number;
  engagement_prediction: string;
}

export interface EpisodeSuggestion {
  id: string;
  title: string;
  short_description: string;
  keywords: string[];
  guest_suggestions: GuestSuggestion[];
  success_probability: number;
  jip_trend_analysis: JipTrendAnalysis;
  jip_legal_analysis: JipLegalAnalysis;
  jip_market_analysis: JipMarketAnalysis;
  episode_news: unknown[];
  created_at: string;
  estimated_duration: number;
  difficulty_level: string;
  target_audience: string;
}

export interface EpisodeSuggestionsResponse {
  request_title: string;
  request_context: string;
  total_suggestions: number;
  suggestions: EpisodeSuggestion[];
  overall_trend_score: number;
  market_opportunity: string;
  recommended_timing: string;
  generated_at: string;
  processing_time_ms: number;
}

/** ===== Tipos do HISTÓRICO (batches) ===== */
export interface EpisodeBatchHeader {
  batch_id: number;
  request_title: string;
  request_context?: string | null;
  request_personal_input?: string | null;
  request_target_audience?: string | null;
  request_episode_format?: string | null;
  total_suggestions: number;
  overall_trend_score?: number | null;
  market_opportunity?: string | null;
  recommended_timing?: string | null;
  processing_time_ms: number;
  created_at: string; // ISO
  status: "success" | "error" | "partial" | string;
}

export interface EpisodeBatch extends EpisodeBatchHeader {
  episodes: EpisodeSuggestion[];
}

export interface EpisodeHistoryResponse {
  success: boolean;
  total: number;
  limit: number;
  offset: number;
  include_episodes: boolean;
  data: Array<EpisodeBatchHeader | EpisodeBatch>;
}

/** ===== API ===== */
export const episodesAPI = {
  /**
   * Gera sugestões de episódios usando o endpoint /api/episode-suggestions/generate
   */
  generateSuggestions: (payload: EpisodeSuggestionRequest): Promise<EpisodeSuggestionsResponse> => {
    return post<EpisodeSuggestionsResponse>("/api/episode-suggestions/generate", payload);
  },

  /**
   * Lista histórico de gerações (batches) do usuário.
   * Por padrão retorna apenas os HEADERS (sem os episódios) para ficar leve.
   * Passe include_episodes: true se quiser trazer os 12 episódios de cada batch.
   *
   * Exemplo:
   *   episodesAPI.history({ limit: 20, offset: 0 })               -> headers
   *   episodesAPI.history({ limit: 1, include_episodes: true })   -> batches completos
   */
  history: (params: { limit?: number; offset?: number; include_episodes?: boolean } = {}) => {
    const { limit = 20, offset = 0, include_episodes = false } = params;
    return get<EpisodeHistoryResponse>("/api/episode-suggestions/history", {
      params: { limit, offset, include_episodes },
    });
  },

  /**
   * Atalho para buscar batches já com episódios.
   * Equivalente a history({ include_episodes: true, ... }).
   */
  historyWithEpisodes: (params: { limit?: number; offset?: number } = {}) => {
    const { limit = 20, offset = 0 } = params;
    return get<EpisodeHistoryResponse>("/api/episode-suggestions/history", {
      params: { limit, offset, include_episodes: true },
    });
  },
};
