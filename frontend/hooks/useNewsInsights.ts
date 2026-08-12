import { useRef, useState } from "react";
import {
  newsInsightsAPI,
  type NewsInsightsRequest,
  type NewsInsightsResponse,
} from "@/lib/api";

function isoNowMinus(hours: number) {
  const d = new Date(Date.now() - hours * 3600 * 1000);
  return d.toISOString();
}

export function useNewsInsights(defaults?: Partial<NewsInsightsRequest>) {
  const [data, setData] = useState<NewsInsightsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ridRef = useRef(0);

  async function run(query: string, override?: Partial<NewsInsightsRequest>) {
    const q = (query || "").trim();
    if (!q) return null;

    setLoading(true);
    setError(null);
    const rid = Date.now();
    ridRef.current = rid;

    const body: NewsInsightsRequest = {
      query: q,
      language: "pt",
      sort_by: "publishedAt",
      max_results: 20,
      from_date: isoNowMinus(24),
      to_date: new Date().toISOString(),
      ...(defaults || {}),
      ...(override || {}),
    };

    try {
      const res = await newsInsightsAPI.analyze(body);
      if (ridRef.current !== rid) return null;
      setData(res);
      return res;
    } catch (e: any) {
      if (ridRef.current !== rid) return null;
      setError(e?.message || "Erro ao buscar notícias");
      return null;
    } finally {
      if (ridRef.current === rid) setLoading(false);
    }
  }

  return { data, loading, error, run };
}

export type { NewsInsightsResponse };
