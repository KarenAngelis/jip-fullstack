// web/src/hooks/useTrends.ts
// ------------------------------------------------------------------
// Hook para Trends: busca 1 termo (com métricas), tendências diárias,
// sugestões de keywords e oportunidades de conteúdo.
// Depende de src/lib/trends.ts
// ------------------------------------------------------------------

import { useCallback, useRef, useState } from "react";
import {
  getTrendWithMetrics,
  getDailyTrends,
  getKeywordSuggestions,
  getContentOpportunities,
  toChartSeries,
  simpleTrendScore,
  type TrendWithMetrics,
  type TrendQueryOptions,
  type ContentOpportunity,
} from "@/lib/trends";
import type { TrendingTopic } from "@/lib/api";

/** Resultado “ok/erro” simples */
export type OpResult<T = void> =
  | { ok: true; data?: T }
  | { ok: false; error: string };

export function useTrends() {
  // ----------------------- state base -----------------------
  const [term, setTerm] = useState("");
  const [error, setError] = useState<string | null>(null);

  // loading granular
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [loadingDaily, setLoadingDaily] = useState(false);
  const [loadingSuggest, setLoadingSuggest] = useState(false);
  const [loadingOpps, setLoadingOpps] = useState(false);

  // dados principais
  const [trend, setTrend] = useState<TrendWithMetrics | null>(null);
  const [chart, setChart] = useState<{ labels: string[]; values: number[] } | null>(null);
  const [score, setScore] = useState<number | null>(null);

  // auxiliares
  const [daily, setDaily] = useState<TrendingTopic[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [opportunities, setOpportunities] = useState<ContentOpportunity[]>([]);

  // evita condição de corrida entre buscas rápidas
  const reqIdRef = useRef(0);

  // ----------------------- ações -----------------------
  const clear = useCallback(() => {
    setError(null);
    setTrend(null);
    setChart(null);
    setScore(null);
    setDaily([]);
    setSuggestions([]);
    setOpportunities([]);
  }, []);

  /** Busca 1 termo em Trends e calcula métricas/score */
  const search = useCallback(
    async (q: string, opts: TrendQueryOptions = {}): Promise<OpResult<TrendWithMetrics>> => {
      const query = (q || "").trim();
      if (!query) {
        setError("Digite um termo para pesquisar.");
        return { ok: false, error: "empty" };
      }

      setError(null);
      setTerm(query);
      setLoadingSearch(true);
      const id = ++reqIdRef.current;

      try {
        const res = await getTrendWithMetrics(query, opts);
        // se outra busca começou, descarta esta resposta
        if (id !== reqIdRef.current) return { ok: false, error: "stale" };

        setTrend(res);
        setChart(toChartSeries(res.raw));
        setScore(simpleTrendScore(res.metrics));

        return { ok: true, data: res };
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Falha ao carregar tendências";
        setError(msg);
        setTrend(null);
        setChart(null);
        setScore(null);
        return { ok: false, error: msg };
      } finally {
        if (id === reqIdRef.current) setLoadingSearch(false);
      }
    },
    []
  );

  /** Tendências diárias (Google Trends daily/realtime) */
  const getDaily = useCallback(
    async (geo = "BR", limit = 20): Promise<OpResult<TrendingTopic[]>> => {
      setLoadingDaily(true);
      setError(null);
      try {
        const data = await getDailyTrends(geo, limit);
        setDaily(data || []);
        return { ok: true, data };
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Falha ao carregar tendências diárias";
        setError(msg);
        setDaily([]);
        return { ok: false, error: msg };
      } finally {
        setLoadingDaily(false);
      }
    },
    []
  );

  /** Sugestões de palavra-chave (seed) */
  const getSuggestions = useCallback(
    async (seed: string): Promise<OpResult<string[]>> => {
      const s = (seed || "").trim();
      if (!s) return { ok: true, data: [] };

      setLoadingSuggest(true);
      setError(null);
      try {
        const raw = await getKeywordSuggestions(s);
        const list = Array.isArray(raw?.suggestions) ? raw.suggestions : [];
        setSuggestions(list);
        return { ok: true, data: list };
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Falha ao carregar sugestões";
        setError(msg);
        setSuggestions([]);
        return { ok: false, error: msg };
      } finally {
        setLoadingSuggest(false);
      }
    },
    []
  );

  /** Oportunidades de conteúdo para 1..N keywords */
  const getOpportunities = useCallback(
    async (keywords: string[]): Promise<OpResult<ContentOpportunity[]>> => {
      const ks = (keywords || []).map((k) => k.trim()).filter(Boolean);
      if (!ks.length) return { ok: true, data: [] };

      setLoadingOpps(true);
      setError(null);
      try {
        const list = await getContentOpportunities(ks);
        setOpportunities(list || []);
        return { ok: true, data: list || [] };
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Falha ao carregar oportunidades";
        setError(msg);
        setOpportunities([]);
        return { ok: false, error: msg };
      } finally {
        setLoadingOpps(false);
      }
    },
    []
  );

  // ----------------------- selectors/helpers -----------------------
  const topRelated = useCallback((n = 10) => trend?.metrics.topRelated.slice(0, n) ?? [], [trend]);
  const risingRelated = useCallback((n = 10) => trend?.metrics.risingRelated.slice(0, n) ?? [], [trend]);
  const topRegions = useCallback((n = 10) => trend?.metrics.topRegions.slice(0, n) ?? [], [trend]);

  // loading agregado
  const loading = {
    search: loadingSearch,
    daily: loadingDaily,
    suggestions: loadingSuggest,
    opportunities: loadingOpps,
    any: loadingSearch || loadingDaily || loadingSuggest || loadingOpps,
  };

  return {
    // estado
    term,
    setTerm,
    error,
    loading,

    // dados
    trend,        // TrendWithMetrics | null
    chart,        // {labels, values} | null
    score,        // number | null
    daily,        // TrendingTopic[]
    suggestions,  // string[]
    opportunities,// ContentOpportunity[]

    // ações
    search,
    getDaily,
    getSuggestions,
    getOpportunities,
    clear,

    // helpers
    topRelated,
    risingRelated,
    topRegions,
  };
}

export type UseTrendsReturn = ReturnType<typeof useTrends>;
