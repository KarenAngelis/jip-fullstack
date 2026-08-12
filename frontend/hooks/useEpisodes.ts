// web/src/hooks/useEpisodes.ts
"use client";
// ------------------------------------------------------------------
// HOOK para orquestrar a chamada de geração de sugestões de episódios
// - Encapsula loading, error e resultados.
// - Exposto como useEpisodes().
// ------------------------------------------------------------------

import { useCallback, useState } from "react";
import {
  episodesAPI,
  type EpisodeSuggestionRequest,
  type EpisodeSuggestionsResponse,
  type EpisodeSuggestion
} from "@/lib/episodes";

export function useEpisodes() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<EpisodeSuggestion[]>([]);
  const [response, setResponse] = useState<EpisodeSuggestionsResponse | null>(null);

  const generate = useCallback(async (req: EpisodeSuggestionRequest) => {
    setLoading(true);
    setError(null);

    try {
      const data = await episodesAPI.generateSuggestions(req);
      
      setSuggestions(data.suggestions || []);
      setResponse(data);
      return { ok: true as const, data };
      
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erro inesperado ao gerar episódios.";
      setError(msg);
      setSuggestions([]);
      setResponse(null);
      return { ok: false as const, error: msg };
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    suggestions,
    response,
    generate,
    clear: () => {
      setSuggestions([]);
      setResponse(null);
      setError(null);
    },
    setError,
  };
}