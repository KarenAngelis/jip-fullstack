// web/src/hooks/useEpisodeHistory.ts
"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  episodesAPI,
  EpisodeHistoryBatch,
  EpisodeHistoryQuery,
} from "@/lib/episodes";

type UseEpisodeHistoryArgs = Partial<EpisodeHistoryQuery> & {
  auto?: boolean; // default true
};

export function useEpisodeHistory(args: UseEpisodeHistoryArgs = {}) {
  const {
    limit = 10,
    offset = 0,
    include_episodes = false,
    auto = true,
  } = args;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState<number>(0);
  const [batches, setBatches] = useState<EpisodeHistoryBatch[]>([]);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await episodesAPI.getHistory({
        limit,
        offset,
        include_episodes,
      });
      setTotal(res.total ?? res.data?.length ?? 0);
      setBatches(Array.isArray(res.data) ? res.data : []);
    } catch (e: any) {
      setError(e?.message || "Falha ao carregar histórico de episódios");
    } finally {
      setLoading(false);
    }
  }, [limit, offset, include_episodes]);

  const refresh = useCallback(() => {
    return fetchHistory();
  }, [fetchHistory]);

  // carrega 1 batch com include_episodes=true e mescla no estado
  const loadBatch = useCallback(
    async (batchId: number) => {
      try {
        const res = await episodesAPI.getHistory({
          limit: 1,
          offset: 0,
          include_episodes: true,
        });
        // alguns backends não filtram por batch_id nesse endpoint; então criamos um fallback:
        const fromList =
          Array.isArray(res.data) && res.data.find((b) => b.batch_id === batchId);
        if (!fromList) return null;

        setBatches((prev) =>
          prev.map((b) => (b.batch_id === batchId ? fromList : b))
        );
        return fromList;
      } catch {
        return null;
      }
    },
    []
  );

  useEffect(() => {
    if (auto) fetchHistory();
  }, [auto, fetchHistory]);

  const hasData = useMemo(() => batches.length > 0, [batches]);

  return {
    loading,
    error,
    total,
    batches,
    hasData,
    refresh,
    loadBatch,
  };
}
