// src/hooks/useRoteiros.ts
"use client";

import { useCallback, useState } from "react";
import { roteirosAPI, type EpisodeRequest, type EpisodeResponse } from "@/lib/roteiros";

export function useRoteiros() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [episode, setEpisode] = useState<EpisodeResponse | null>(null);

  const generate = useCallback(async (req: EpisodeRequest) => {
    setLoading(true);
    setError(null);
    setEpisode(null);

    try {
      const res = await roteirosAPI.generate(req);
      setEpisode(res);
      return { ok: true as const, data: res };
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Falha ao gerar roteiro";
      setError(msg);
      return { ok: false as const, error: msg };
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setEpisode(null);
    setError(null);
  }, []);

  return { loading, error, episode, generate, clear };
}

export type UseRoteirosReturn = ReturnType<typeof useRoteiros>;
