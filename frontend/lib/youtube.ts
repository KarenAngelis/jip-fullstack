// src/lib/youtube.ts
// -------------------------------------------------------------
// LIB pura (TypeScript) para buscar vídeos trending no YouTube
// via sua rota do backend: /api/youtube/search-trending
// NENHUM JSX/React aqui. Só tipos e funções.
// Usa NEXT_PUBLIC_API_URL e acrescenta /api caso necessário.
// -------------------------------------------------------------

import axios, { AxiosInstance } from "axios";

/* ===================== Base URL ===================== */
const RAW = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_ROOT = RAW.replace(/\/+$/, "");
export const API_BASE = API_ROOT.endsWith("/api") ? API_ROOT : `${API_ROOT}/api`;

const http: AxiosInstance = axios.create({
  baseURL: API_ROOT,
  headers: { "Content-Type": "application/json" },
});

/* ===================== Tipos ===================== */
export type YoutubeOrder = "relevance" | "date" | "rating" | "viewCount" | "title";

export interface YoutubeTrendingParams {
  theme: string;             // ex: "Enem 2025"
  region_code?: string;      // ex: "BR"
  max_results?: number;      // 1..50
  order?: YoutubeOrder;      // default do back: "relevance"
  published_after?: string;  // "YYYY-MM-DD"
}

export interface YoutubeTrendingItem {
  id: string;
  title: string;
  channel_title: string;
  channel_id: string;
  published_at: string;       // ISO
  view_count: number | null;
  like_count: number | null;
  comment_count: number | null;
  duration: string;           // ISO8601 "PT26M18S"
  thumbnail_url: string;
  description: string;
  category_id: string;
  category_name: string;
  tags: string[];
  trending_rank: number | null;
  trending_score: number | null;
}

/* ===================== API ===================== */
export async function searchYoutubeTrending(
  params: YoutubeTrendingParams
): Promise<YoutubeTrendingItem[]> {
  const {
    theme,
    region_code = "BR",
    max_results = 20,
    order = "relevance",
    published_after,
  } = params;

  if (!theme?.trim()) return [];

  const res = await http.get<YoutubeTrendingItem[]>(
    `${API_BASE}/youtube/search-trending`,
    { params: { theme, region_code, max_results, order, published_after } }
  );

  return Array.isArray(res.data) ? res.data : [];
}

/* ===================== Utils opcionais ===================== */
export const formatInt = (n: number | null | undefined) =>
  typeof n === "number" ? new Intl.NumberFormat("pt-BR").format(n) : "—";

export const isoToDateTime = (iso?: string) => {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(d);
};

// "PT26M18S" -> "26:18" (ou "1:02:05" se tiver horas)
export function durationToClock(isoDur?: string) {
  if (!isoDur?.startsWith("PT")) return "—";
  const m = isoDur.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
  if (!m) return "—";
  const h = Number(m[1] ?? 0);
  const mm = Number(m[2] ?? 0);
  const ss = Number(m[3] ?? 0);
  const pad = (x: number) => String(x).padStart(2, "0");
  return h > 0 ? `${h}:${pad(mm)}:${pad(ss)}` : `${mm}:${pad(ss)}`;
}
