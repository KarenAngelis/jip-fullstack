"use client";
// ------------------------------------------------------------------
// HOOK para leitura do histórico no banco (NÃO altera useTitles).
// - Lista registros paginados de /api/titles
// - Filtros: topic, limit, offset, order
// - Estados independentes do hook de geração
// ------------------------------------------------------------------

import { useCallback, useEffect, useMemo, useState } from "react";
import { titlesAPI } from "@/lib/titles";

/** Tipos mínimos compatíveis com o JSON do banco (auto-contidos aqui) */
export type Order = "asc" | "desc";

export interface TitleScores {
  engagement: number;
  seo: number;
  trend: number;
  overall: number;
}

export interface GeneratedTitleItem {
  title: string;
  scores: TitleScores;
  trends_used?: string[];
  power_words?: string[];
}

export interface TitleRecord {
  id: number;
  topic: string;
  created_at: string; // ISO
  audience?: string;
  content_type?: string;
  tone?: string;
  quantity: number;
  titles_generated: GeneratedTitleItem[];
  total_titles?: number;
  trends_found?: string[];
  best_title?: string;
  best_score?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  generation_time?: number;
  status?: "success" | "error";
  error_message?: string | null;
}

export interface ListParams {
  topic?: string;
  limit?: number;
  offset?: number;
  order?: Order;
}

export type Paginated<T> = { items: T[]; total: number };

export function useTitleRecords(initial: ListParams = { limit: 20, order: "desc" }) {
  const [query, setQuery] = useState<ListParams>(initial);
  const [records, setRecords] = useState<TitleRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchList = useCallback(
    async (q: ListParams = query): Promise<Paginated<TitleRecord>> => {
      setLoading(true);
      setError(null);
      try {
        const { items, total } = await titlesAPI.list(q);
        setRecords(items);
        setTotal(total);
        return { items, total };
      } catch (e) {
        const msg =
          e instanceof Error ? e.message : "Falha ao carregar títulos do banco.";
        setError(msg);
        setRecords([]);
        setTotal(0);
        return { items: [], total: 0 };
      } finally {
        setLoading(false);
      }
    },
    [query]
  );

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  // helpers
  const setTopic = useCallback(
    (topic?: string) => {
      const next = { ...query, topic, offset: 0 };
      setQuery(next);
      fetchList(next);
    },
    [query, fetchList]
  );

  const setLimit = useCallback(
    (limit: number) => {
      const next = { ...query, limit, offset: 0 };
      setQuery(next);
      fetchList(next);
    },
    [query, fetchList]
  );

  const pagination = useMemo(() => {
    const size = query.limit ?? 20;
    return {
      next: () => {
        const next = { ...query, offset: (query.offset || 0) + size };
        setQuery(next);
        fetchList(next);
      },
      prev: () => {
        const next = { ...query, offset: Math.max(0, (query.offset || 0) - size) };
        setQuery(next);
        fetchList(next);
      },
      reset: () => {
        const next = { ...query, offset: 0 };
        setQuery(next);
        fetchList(next);
      },
    };
  }, [query, fetchList]);

  return {
    // estados
    loading,
    error,

    // dados
    records,
    total,
    query,

    // ações
    refresh: () => fetchList(),
    setQuery,
    setTopic,
    setLimit,
    pagination,
    setError,
  };
}
