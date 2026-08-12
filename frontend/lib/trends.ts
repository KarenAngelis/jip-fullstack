// src/lib/trends.ts
// ------------------------------------------------------------------
// Camada fina de Trends delegando para lib/api.ts (Axios + interceptors).
// Usa trendsAPI.analyze/opportunities/suggestions já padronizados.
// Mantém os tipos/funcões utilitárias da UI.
// ------------------------------------------------------------------

import {
  trendsAPI,
  type TrendAnalysisResult as TrendData,
  type TrendTargetKeyword as TargetKeyword,
  type ContentOpportunity as LegacyContentOpportunity, // legado (se endpoint /opportunities retornar esse shape)
} from "@/lib/api";

/* ======================= Tipos do backend (mantidos) ======================= */

export type GeographicInsight = {
  region: string;
  state_code?: string;     // UF (opcional no backend)
  interest_score: number;  // 0..100
  interest_rank?: number;  // 1..N
};

export type OverallMetrics = {
  current_interest: number;
  peak_interest: number;
  average_interest: number;
  growth_rate: number | null;
  volatility: number | null;
  trend_direction: "crescendo" | "estavel" | "decaindo" | "desconhecido";
};

export type BackendContentOpportunity = {
  topic: string;
  hook: string;
  opportunity_type: string;
  market_analysis?: Record<string, any>;
  competition_analysis?: Record<string, any>;
  content_angles?: string[];
  target_keywords?: TargetKeyword[];
  content_types?: string[];
  urgency_level?: "baixa" | "media" | "alta" | "critica";
  best_channels?: string[];
  estimated_roi?: string;
  target_personas?: string[] | string;
  audience_size?: string;
};

/* ======================= Opções ======================= */

export interface TrendQueryOptions {
  timeframe?: string; // 'today 12-m'
  geo?: string;       // 'BR'
  category?: number | null;  // 0
  include_predictions?: boolean;
  include_opportunities?: boolean;
  include_related?: boolean; // ✅ novo
}

/* ======================= Tipos p/ UI ======================= */

export type Topico = {
  title: string;
  category: string;   // "Termo" | "Top" | "Rising"
  buscas: string;     // "55 interesse" | "80 pts" | "90%"
  difficulty: "Easy" | "Medium" | "Hard" | string;
  growth: string;     // "+42%" | ""
  score?: number;
};

export interface RegionValue { region: string; value: number; }

export interface TrendMetrics {
  series: number[];
  first: number;
  last: number;
  growthPct: number;
  avgInterest: number;
  peak: { value: number; date: string };
  topRelated: TargetKeyword[];    // de opportunities[0].target_keywords
  risingRelated: TargetKeyword[]; // vazio (por enquanto)
  topRegions: RegionValue[];      // de geographical_breakdown
}

export interface TrendWithMetrics {
  raw: TrendData;
  metrics: TrendMetrics;
}

/* ===== Oportunidades exportadas p/ o front (legado) ===== */
export type OpportunityType = "alta_oportunidade" | "trending_topic" | "nicho_especifico";
export type CompetitionLevel = "baixo" | "medio" | "alto";

export interface ContentOpportunity {
  topic: string;
  opportunity_type: OpportunityType;
  interest_level: number;             // 0..100
  competition_level: CompetitionLevel;
  target_audience: string;
  suggested_content_types: string[];
  estimated_traffic_potential?: string;
  description: string;
}

/* ======================= Helpers ======================= */

const difficultyFromPct = (pct?: number | null): Topico["difficulty"] => {
  if (pct == null) return "Medium";
  if (pct < 30) return "Easy";
  if (pct < 70) return "Medium";
  return "Hard";
};

function calcAvg(arr: number[]): number {
  if (!arr.length) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function pickValue(obj: Record<string, any>, key: string): number {
  const v = obj?.[key];
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  for (const val of Object.values(obj || {})) {
    if (typeof val === "number" && !Number.isNaN(val)) return val;
  }
  return 0;
}

/** extrai série numérica a partir do TrendAnalysisResult (historical_performance) */
function extractSeries(raw: TrendData): { key: string; series: number[] } {
  const hist = Array.isArray(raw.historical_performance) ? raw.historical_performance : [];
  if (!hist.length) return { key: raw.keyword, series: [] };

  // detecta a chave da série (qualquer chave numérica ≠ "date")
  const keys = Object.keys(hist[0]).filter((k) => k !== "date");
  const valueKey =
    keys.find((k) => k.toLowerCase() === raw.keyword.toLowerCase()) ||
    keys[0] ||
    raw.keyword;

  const series = hist.map((p) => pickValue(p, valueKey));
  return { key: valueKey, series };
}

/** converte uma oportunidade no formato legado (endpoint dedicado antigo)
 * para o formato moderno esperado pelo front (BackendContentOpportunity). */
function mapLegacyOppToBackend(o: LegacyContentOpportunity): BackendContentOpportunity {
  return {
    topic: o.topic,
    hook: `Guia Definitivo: ${o.topic?.toString().trim().replace(/^./, c => c.toUpperCase())}`,
    opportunity_type: o.opportunity_type, // mantém como string; backend normaliza
    market_analysis: {
      current_interest: o.interest_level,
    },
    competition_analysis: {
      level: o.competition_level,
    },
    content_angles: [o.description].filter(Boolean),
    target_keywords: [], // legado não traz, mantemos vazio
    content_types: o.suggested_content_types ?? [],
    urgency_level: "media",
    best_channels: [],
    estimated_roi: o.estimated_traffic_potential,
    target_personas: o.target_audience ? [o.target_audience] : [],
    audience_size: o.estimated_traffic_potential,
  };
}

/* ======================= API de alto nível (via trendsAPI) ======================= */

/** Busca 1 termo e devolve dados + métricas calculadas (rota: /api/trends/analyze) */
export async function getTrendWithMetrics(
  term: string,
  opts: TrendQueryOptions = {}
): Promise<TrendWithMetrics> {
  const raw = await trendsAPI.analyze({
    keywords: [term],                             // delega p/ lib/api.ts (normaliza keyword/keywords)
    timeframe: opts.timeframe ?? "today 12-m",
    geo: opts.geo ?? "BR",
    category: opts.category ?? null,
    include_predictions: opts.include_predictions ?? true,
    include_opportunities: opts.include_opportunities ?? true,
    include_related: opts.include_related ?? true, // ✅ passa adiante
  });

  // Série / métricas básicas
  const { key: valueKey, series } = extractSeries(raw);
  const first = series[0] ?? 0;
  const last = series[series.length - 1] ?? 0;
  const growthPct = first === 0 ? (last > 0 ? 100 : 0) : ((last - first) / Math.max(1, first)) * 100;
  const avgInterest = calcAvg(series);

  // Pico
  let peak = { value: 0, date: "" };
  (raw.historical_performance || []).forEach((p) => {
    const v = pickValue(p, valueKey);
    if (v > peak.value) peak = { value: v, date: p.date as any };
  });

  // Related a partir de opportunities[0].target_keywords
  const opp0 = Array.isArray(raw.opportunities) && raw.opportunities.length ? raw.opportunities[0] : undefined;
  const topRelated: TargetKeyword[] = opp0?.target_keywords
    ? [...opp0.target_keywords].sort((a, b) => (Number(b.opportunity_score ?? 0) - Number(a.opportunity_score ?? 0)))
    : [];
  const risingRelated: TargetKeyword[] = []; // aguardando backend expor "rising"

  // Regiões a partir de geographical_breakdown
  const topRegions: RegionValue[] = (raw.geographical_breakdown || [])
    .map((g) => ({ region: g.region, value: (g as any).interest_score }))
    .sort((a, b) => b.value - a.value);

  return {
    raw,
    metrics: { series, first, last, growthPct, avgInterest, peak, topRelated, risingRelated, topRegions },
  };
}

/** Constrói cards (Topico[]) p/ a UI a partir do payload do backend */
export function buildTopicosFromTrends(
  raw: TrendData,
  metrics?: TrendMetrics
): Topico[] {
  const overall = (raw as any).overall_metrics ?? ({} as OverallMetrics);
  const series = metrics?.series ?? extractSeries(raw).series;

  // 1) Termo principal
  const main: Topico = {
    title: raw.keyword.toLowerCase(),
    category: "Termo",
    buscas: `${overall.current_interest ?? (series[series.length - 1] ?? 0)} interesse`,
    difficulty: difficultyFromPct(100 - Math.min(100, overall.current_interest ?? 0)),
    growth:
      overall.growth_rate != null
        ? `${overall.growth_rate >= 0 ? "+" : ""}${Math.round(overall.growth_rate)}%`
        : "",
    score: Math.min(99, 70 + Math.round((overall.current_interest ?? 0) * 0.2)),
  };

  // 2) Relacionados (opportunities[0].target_keywords)
  const related: Topico[] = ((raw.opportunities?.[0]?.target_keywords ?? []) as TargetKeyword[]).map((rq) => ({
    title: rq.text.toLowerCase(),
    category: "Top",
    buscas: `${rq.opportunity_score} pts`,
    difficulty: difficultyFromPct(60),
    growth: "",
    score: rq.opportunity_score,
  }));

  return [main, ...related];
}

/** Tendências diárias — delega (se existir no backend) */
export async function getDailyTrends(geo = "BR", limit = 20): Promise<any[]> {
  try {
    const res = await trendsAPI.daily?.(geo, limit);
    return Array.isArray(res) ? res : [];
  } catch {
    return [];
  }
}

/** Sugestões de palavra-chave — delega à lib/api.ts */
export async function getKeywordSuggestions(seedKeyword: string): Promise<{ suggestions: string[] }> {
  try {
    const out = await trendsAPI.suggestions?.(seedKeyword);
    const list = Array.isArray((out as any)?.suggestions) ? (out as any).suggestions : [];
    return { suggestions: list.map((s: any) => String(s)) };
  } catch {
    return { suggestions: [] };
  }
}

/** Oportunidades de conteúdo — tenta endpoint dedicado, senão deriva do analyze */
export async function getContentOpportunities(keywords: string[]): Promise<BackendContentOpportunity[]> {
  // 1) endpoint dedicado (se existir)
  try {
    const list = await trendsAPI.opportunities?.(keywords);
    if (Array.isArray(list)) {
      // se veio no formato legado, mapeia; se já estiver no formato backend, só retorna
      const first = list[0] as any;
      const isLegacyShape =
        first &&
        typeof first.topic === "string" &&
        "opportunity_type" in first &&
        "interest_level" in first; // campo típico do legado

      if (isLegacyShape) {
        return (list as LegacyContentOpportunity[]).map(mapLegacyOppToBackend);
      }
      return list as unknown as BackendContentOpportunity[];
    }
  } catch {
    // fallback
  }

  // 2) fallback: usa analyze na 1ª keyword
  try {
    if (keywords.length) {
      const first = await getTrendWithMetrics(keywords[0], {
        include_opportunities: true,
        include_predictions: false,
        include_related: true,
      });
      const opps = Array.isArray(first.raw?.opportunities) ? first.raw.opportunities : [];
      return opps as BackendContentOpportunity[];
    }
  } catch {
    // ignora
  }

  return [];
}

/** Dados prontos p/ gráfico (labels e série) a partir do TrendAnalysisResult */
export function toChartSeries(data: TrendData): { labels: string[]; values: number[] } {
  const hist = Array.isArray(data?.historical_performance) ? data.historical_performance : [];
  if (!hist.length) return { labels: [], values: [] };

  const keys = Object.keys(hist[0] ?? {}).filter((k) => k !== "date");
  const valueKey =
    keys.find((k) => k.toLowerCase() === data.keyword.toLowerCase()) ||
    keys[0] ||
    data.keyword;

  const labels = hist.map((p) => {
    const d = new Date(p.date as any);
    return isNaN(d.getTime())
      ? String(p.date)
      : d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  });

  const values = hist.map((p) => pickValue(p as any, valueKey));
  return { labels, values };
}

/** Score simples (0..100) combinando atual, pico, crescimento e estabilidade */
export function simpleTrendScoreFromOverall(overall: OverallMetrics): number {
  const current = clamp01((overall.current_interest ?? 0) / 100);
  const peak = clamp01((overall.peak_interest ?? 0) / 100);
  const growth = clamp01(Math.max(0, (overall.growth_rate ?? 0)) / 100); // só positivos
  const stability = 1 - clamp01(overall.volatility ?? 0);                // menor volatilidade = melhor
  const score = 0.4 * current + 0.2 * peak + 0.25 * growth + 0.15 * stability;
  return Math.round(score * 100);
}

/** Mantém assinatura antiga (recebe TrendMetrics) */
export function simpleTrendScore(m: TrendMetrics): number {
  const last = clamp01((m.last ?? 0) / 100);
  const avg = clamp01((m.avgInterest ?? 0) / 100);
  const growth = clamp01(Math.max(0, (m.growthPct ?? 0)) / 100);
  const score = 0.5 * last + 0.3 * avg + 0.2 * growth;
  return Math.round(score * 100);
}

function clamp01(x: number) {
  if (Number.isNaN(x)) return 0;
  return Math.max(0, Math.min(1, x));
}
