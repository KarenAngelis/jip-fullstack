"use client";

import React, { useRef, useState } from "react";
import {
  Search, TrendingUp, Target, Eye, Lightbulb, ArrowUp, Users, Calendar, Zap,
  Loader2, Play, ArrowRightLeft, Info, MapPin, BarChart3,
} from "lucide-react";
import { useNewsInsights } from "@/hooks/useNewsInsights"; // 🆕
import {
  trendsAPI,
  youtubeAPI,                                  // 👈 novo
  type YoutubeTrendingItem,   
  type ContentOpportunity, // legado de /api/trends/opportunities
  type RelatedQuery,
  type TrendAnalysisResult,
  type TrendGeoInsight,
  type TrendTargetKeyword,
} from "@/lib/api";

/* ===================== Tipos só da UI ===================== */
type MainCard = {
  title: string;
  interesse: number; // 0..100
  growthPct: number; // %
  difficulty: "Easy" | "Medium" | "Hard";
  score: number;
};

type Preview = {
  tema: string;
  categoria?: string;
  viabilidade_score: number;
  oportunidade?: { label?: string };
  trend_growth_pct?: number | null;
  volume_estimado?: number | null;
  tempo_estimado_preparo?: string;
  dificuldade?: "Easy" | "Medium" | "Hard" | string;
  badges?: string[];
  insights?: string[];
  palavras_chave?: string[];
  cta?: { label?: string };
};

/* ===================== Helpers ===================== */
const nf = (n: number) =>
  new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(n);

const difficultyClass = (d?: string) => {
  switch ((d || "").toLowerCase()) {
    case "easy":
      return "bg-green-600 text-green-100";
    case "medium":
      return "bg-yellow-600 text-yellow-100";
    case "hard":
      return "bg-red-600 text-red-100";
    default:
      return "bg-gray-600 text-gray-100";
  }
};

const sentimentBadgeClass = (s?: string) => {
  switch ((s || "").toLowerCase()) {
    case "positive":
      return "bg-green-700 text-green-100";
    case "negative":
      return "bg-red-700 text-red-100";
    case "mixed":
      return "bg-yellow-700 text-yellow-100";
    default:
      return "bg-gray-700 text-gray-100"; // neutral ou desconhecido
  }
};

const fmtDateTime = (iso?: string) =>
  iso ? new Date(iso).toLocaleString("pt-BR") : "—";


const scoreColor = (score = 0) =>
  score >= 85 ? "text-green-400" : score >= 65 ? "text-yellow-400" : "text-red-400";

const diffFromPct = (pct: number): MainCard["difficulty"] => {
  if (pct < 30) return "Easy";
  if (pct < 70) return "Medium";
  return "Hard";
};

const pct = (v: number) => (v >= 0 ? `+${v}%` : `${v}%`);

// === Helpers YouTube ===
const fmtYTDuration = (iso?: string) => {
  if (!iso || !iso.startsWith("PT")) return "—";
  const m = iso.match(/^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/);
  const h = Number(m?.[1] || 0);
  const mi = Number(m?.[2] || 0);
  const s = Number(m?.[3] || 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(mi)}:${pad(s)}` : `${mi}:${pad(s)}`;
};

const fmtDateBR = (iso?: string) => {
  const d = iso ? new Date(iso) : null;
  return d && !isNaN(d.getTime()) ? d.toLocaleDateString("pt-BR") : "—";
};



/* ======= number parsing robusto ======= */
const toNum = (v: any): number | undefined => {
  const n =
    typeof v === "number"
      ? v
      : typeof v === "string"
      ? Number(v.replace(",", ".")) : NaN;
  return Number.isFinite(n) ? n : undefined;
};

/* ======= Parse de search_volume ("500K-2M", "2M+", "800") ======= */
const parseSearchVolume = (label?: string): number | undefined => {
  if (!label) return;
  const s = label.toString().trim().toUpperCase().replace(/\s/g, "");
  const scale = (n: number, u?: string) =>
    Math.round(n * (u === "K" ? 1e3 : u === "M" ? 1e6 : u === "B" ? 1e9 : 1));
  const parsePart = (p: string) => {
    const m = p.match(/^([\d.,]+)([KMB])?\+?$/);
    if (!m) return NaN;
    return scale(parseFloat(m[1].replace(",", ".")), m[2]);
  };
  if (s.includes("-")) {
    const [a, b] = s.split("-");
    const min = parsePart(a);
    const max = parsePart(b);
    if (Number.isFinite(min) && Number.isFinite(max)) return Math.round((min + max) / 2);
  }
  const single = parsePart(s.replace(/\+$/, ""));
  return Number.isFinite(single) ? single : undefined;
};

/* ======= Normalizador do /trends/analyze (snake_case ↔ camelCase) ======= */
const str = (v: any) => (typeof v === "string" ? v : undefined);

function normalizeAnalysis(raw: any): TrendAnalysisResult {
  const data = raw?.data ?? raw;
  const om = data?.overall_metrics ?? data?.overallMetrics ?? {};
  return {
    keyword: str(data?.keyword) ?? str(data?.term) ?? "",
    analysis_date: data?.analysis_date ?? data?.analysisDate ?? new Date().toISOString(),
    overall_metrics: {
      current_interest: toNum(om.current_interest) ?? toNum(om.currentInterest) ?? 0,
      peak_interest: toNum(om.peak_interest) ?? toNum(om.peakInterest) ?? 0,
      average_interest: toNum(om.average_interest) ?? toNum(om.averageInterest) ?? 0,
      growth_rate: toNum(om.growth_rate) ?? toNum(om.growthRate) ?? 0,
      volatility: toNum(om.volatility) ?? null,
      trend_direction:
        str(om.trend_direction) ?? str(om.trendDirection) ?? "desconhecido",
    },
    geographical_breakdown:
      data?.geographical_breakdown ?? data?.geographicalBreakdown ?? [],
    historical_performance:
      data?.historical_performance ?? data?.historicalPerformance ?? [],
    seasonal_patterns: data?.seasonal_patterns ?? data?.seasonalPatterns ?? null,
    future_predictions: data?.future_predictions ?? data?.futurePredictions ?? null,
    related_topics: data?.related_topics ?? data?.relatedTopics ?? [],
    competitor_content: data?.competitor_content ?? [],
    content_gaps: data?.content_gaps ?? [],
    opportunities: data?.opportunities ?? data?.opps ?? [],
    quick_wins: data?.quick_wins ?? [],
    long_term_strategy: data?.long_term_strategy ?? {},
    provenance: data?.provenance ?? null,
  } as TrendAnalysisResult;
}

/* ======= Interesse/Crescimento com fallback consistente ======= */
const computeInterest = (_opp?: Partial<ContentOpportunity>, analysis?: TrendAnalysisResult | null) => {
  const v = analysis?.overall_metrics?.current_interest;
  const n = toNum(v);
  return n != null ? Math.max(0, Math.min(100, Math.round(n))) : 0;
};

const computeGrowth = (_opp?: Partial<ContentOpportunity>, analysis?: TrendAnalysisResult | null) => {
  const g = analysis?.overall_metrics?.growth_rate;
  const n = toNum(g);
  return n != null ? Math.round(n) : null;
};

/* ===================== Componente ===================== */
const PesquisaInsightsDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<
    "tendencias" | "analise" | "youtube" | "noticias"
  >("tendencias");

  // chips de contexto
  const [geo] = useState<"BR">("BR");
  const [timeframe] = useState<"today 12-m">("today 12-m");
  const [categoryLabel] = useState("Todas categorias");

  // loading
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [isLoadingTermTrending, setIsLoadingTermTrending] = useState(false);
  const [isLoadingOpportunities, setIsLoadingOpportunities] = useState(false);

  // busca
  const [searchTerm, setSearchTerm] = useState("");

  // dados
  const [preview, setPreview] = useState<Preview | null>(null);
  const [mainCard, setMainCard] = useState<MainCard | null>(null);
  const [relatedTop, setRelatedTop] = useState<RelatedQuery[]>([]);
  const [relatedRising, setRelatedRising] = useState<RelatedQuery[]>([]);
  const [realTimeOpportunities, setRealTimeOpportunities] = useState<
    ContentOpportunity[]
  >([]);
  const [analysis, setAnalysis] = useState<TrendAnalysisResult | null>(null);
  const [topRegions, setTopRegions] = useState<TrendGeoInsight[]>([]);
  const [kwTargets, setKwTargets] = useState<TrendTargetKeyword[]>([]);

  // YouTube
  const [isLoadingYouTube, setIsLoadingYouTube] = useState(false);
  const [youtube, setYoutube] = useState<YoutubeTrendingItem[]>([]);

  // 🆕 Notícias & Insights (hook)
  const {
    data: newsData,
    loading: isLoadingNews,
    error: newsError,
    run: runNews,
  } = useNewsInsights({
    language: "pt",
    sort_by: "publishedAt",
    max_results: 20,
  });

  // request-id para evitar race-condition
  const reqRef = useRef(0);

  /* ---------------- TENDÊNCIAS (usa /search adaptado do analyze) ---------------- */
  async function loadTermTrending(term: string, rid: number) {
    const t = term.trim();
    if (!t) return;

    if (!trendsAPI.search) {
      setRelatedTop([]);
      setRelatedRising([]);
      return;
    }

    setIsLoadingTermTrending(true);
    try {
      const res = await trendsAPI.search({
        keywords: [t],
        timeframe,
        geo,
        category: 0,
      });
      if (reqRef.current !== rid) return;

      const data = (res as any)?.data ?? res;
      const list: RelatedQuery[] = data?.related_queries ?? [];

      const top = (list || [])
        .filter((r) => r.type === "top")
        .sort((a, b) => Number(b.value) - Number(a.value))
        .slice(0, 10);

      const rising = (list || [])
        .filter((r) => r.type === "rising")
        .sort((a, b) => Number(b.value) - Number(a.value))
        .slice(0, 10);

      setRelatedTop(top);
      setRelatedRising(rising);
    } catch {
      if (reqRef.current !== rid) return;
      setRelatedTop([]);
      setRelatedRising([]);
    } finally {
      if (reqRef.current === rid) setIsLoadingTermTrending(false);
    }
  }

  /* ---------------- OPORTUNIDADES (/trends/opportunities – legado) ---------------- */
  async function loadRealTimeOpportunities(term: string, rid: number) {
    const t = term.trim();
    if (!t) return;

    setIsLoadingOpportunities(true);
    try {
      const list = await (trendsAPI as any).opportunities?.([t]);
      if (reqRef.current !== rid) return;

      const safe: ContentOpportunity[] = Array.isArray(list)
        ? (list as ContentOpportunity[]).map((opp) => ({
            topic: String(opp.topic ?? t),
            opportunity_type: opp.opportunity_type as any,
            interest_level: Number(opp.interest_level ?? 0),
            competition_level: opp.competition_level as any,
            target_audience: String(opp.target_audience ?? ""),
            suggested_content_types: Array.isArray(opp.suggested_content_types)
              ? opp.suggested_content_types
              : [],
            estimated_traffic_potential:
              typeof opp.estimated_traffic_potential === "string"
                ? opp.estimated_traffic_potential
                : undefined,
            description:
              typeof opp.description === "string" ? opp.description : "",
          }))
        : [];

      setRealTimeOpportunities(safe.slice(0, 3));
    } catch {
      if (reqRef.current !== rid) return;
      setRealTimeOpportunities([]);
    } finally {
      if (reqRef.current === rid) setIsLoadingOpportunities(false);
    }
  }

  /* ---------------- ANALYZE (/trends/analyze) ---------------- */
  async function loadAnalysis(term: string, rid: number) {
    const t = term.trim();
    if (!t) return;

    const raw = await trendsAPI.analyze({
      keywords: [t],
      timeframe,
      geo,
      category: 0, // 0 não é enviado (sanitizado no api.ts)
      include_predictions: true,
      include_opportunities: true,
    });
    if (reqRef.current !== rid) return;

    const a = normalizeAnalysis(raw);
    setAnalysis(a);

    // regiões
    const regions = (a.geographical_breakdown ?? []).map(
      (g: any, i: number) => ({
        ...g,
        interest_rank: toNum(g?.interest_rank) ?? i + 1,
        interest_score: toNum(g?.interest_score) ?? 0,
      })
    ) as TrendGeoInsight[];
    setTopRegions(regions.slice(0, 10));

    const opp = a.opportunities?.[0];
    const kw = (opp?.target_keywords ?? []).map((k: any) => ({
      text: k.text,
      search_volume: String(k.search_volume ?? ""),
      difficulty: String(k.difficulty ?? ""),
      opportunity_score: toNum(k.opportunity_score) ?? 0,
      intent: k.intent,
    })) as TrendTargetKeyword[];
    setKwTargets(kw);

    // Card principal
    const interesse = Math.round(
      toNum(a.overall_metrics.current_interest) ?? 0
    );
    const growthPct = toNum(a.overall_metrics.growth_rate) ?? null;
    setMainCard({
      title: a.keyword,
      interesse,
      growthPct: Math.round(growthPct ?? 0),
      difficulty: diffFromPct(100 - interesse),
      score: Math.min(99, 70 + Math.round(interesse * 0.2)),
    });

    // Fallback de "Top" com target_keywords (se /search não trouxe nada)
    if (!relatedTop.length && kw.length > 0) {
      const mapped: RelatedQuery[] = kw.slice(0, 10).map((k) => ({
        query: k.text,
        value: Math.round(Number(k.opportunity_score ?? 0)),
        type: "top",
      }));
      setRelatedTop(mapped);
    }

    // Preview (aba Análise)
    const level = (opp as any)?.competition_analysis?.level as
      | "baixo"
      | "medio"
      | "alto"
      | "media"
      | undefined;

    const dificuldade: "Easy" | "Medium" | "Hard" =
      level === "baixo" ? "Easy" : level === "alto" ? "Hard" : "Medium";

    const primaryKW =
      kw.find((k) => k.text?.toLowerCase() === a.keyword?.toLowerCase()) ||
      [...kw].sort(
        (x, y) =>
          (Number(y.opportunity_score ?? 0) || 0) -
          (Number(x.opportunity_score ?? 0) || 0)
      )[0];
    const volumeEstimado = parseSearchVolume(primaryKW?.search_volume) ?? null;

    setPreview({
      tema: a.keyword,
      categoria: "Trends",
      viabilidade_score: interesse,
      oportunidade: { label: (opp as any)?.opportunity_type || "Oportunidade" },
      trend_growth_pct: growthPct,
      volume_estimado: volumeEstimado,
      tempo_estimado_preparo: "2-3 horas",
      dificuldade,
      badges:
        (opp as any)?.content_types && Array.isArray((opp as any).content_types)
          ? (opp as any).content_types
          : ["artigo", "video"],
      insights: [
        `Direção: ${a.overall_metrics.trend_direction}`,
        `Média: ${Math.round(
          toNum(a.overall_metrics.average_interest) ?? 0
        )}/100 • Pico: ${toNum(a.overall_metrics.peak_interest) ?? 0}/100`,
        (opp as any)?.estimated_roi
          ? `ROI estimado: ${(opp as any).estimated_roi}`
          : "",
        (a as any)?.future_predictions?.next_30_days
          ? `30d: ${(a as any).future_predictions.next_30_days}`
          : "",
      ].filter(Boolean) as string[],
      palavras_chave: [a.keyword],
      cta: { label: "Gerar Pauta com IA" },
    });
  }

  /* ---------------- YOUTUBE (/youtube/search-trending) ---------------- */
  async function loadYouTubeTrending(term: string, rid: number) {
    const t = term.trim();
    if (!t) {
      setYoutube([]);
      return;
    }
    setIsLoadingYouTube(true);
    try {
      const items = await youtubeAPI.searchTrending({
        theme: t,
        region_code: geo,
        max_results: 20,
        order: "relevance",
        // published_after: opcional: "2025-01-01"
      });
      if (reqRef.current !== rid) return;
      setYoutube(Array.isArray(items) ? items : []);
    } catch {
      if (reqRef.current !== rid) return;
      setYoutube([]);
    } finally {
      if (reqRef.current === rid) setIsLoadingYouTube(false);
    }
  }

  /* ---------------- Busca principal (concorrência segura) ---------------- */
  async function handleSearch() {
    if (!searchTerm.trim()) return;

    setActiveTab("tendencias");
    setIsLoadingPreview(true);

    const rid = Date.now();
    reqRef.current = rid;

    void loadTermTrending(searchTerm, rid);
    void loadRealTimeOpportunities(searchTerm, rid);
    void runNews(searchTerm);
    void loadYouTubeTrending(searchTerm, rid);
    try {
      await loadAnalysis(searchTerm, rid);
    } finally {
      if (reqRef.current === rid) setIsLoadingPreview(false);
    }
  }

  /* ===================== UI ===================== */
  return (
    <div className="min-h-screen bg-gray-900 text-white text-[15px] md:text-[16px] lg:text-[17px] leading-relaxed">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <h1 className="text-2xl font-bold text-white">
              Pesquisa & Insights
            </h1>
            <p className="mt-1 text-sm text-gray-400">
              Descubra tendências, analise tópicos e encontre oportunidades de
              conteúdo
            </p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Busca */}
        <div className="bg-gray-800 rounded-lg shadow-sm border border-gray-700 p-6 mb-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="text"
                  placeholder="Ex: Enem 2025, IA Generativa, Black Friday…"
                  className="w-full pl-10 pr-4 py-3 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-gray-400"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
              </div>
            </div>
            <button
              onClick={handleSearch}
              disabled={!searchTerm.trim() || isLoadingPreview}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isLoadingPreview || isLoadingTermTrending ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Buscando…
                </>
              ) : (
                "Pesquisar"
              )}
            </button>
          </div>
        </div>

        {/* Chips */}
        <div className="mb-8 flex flex-wrap items-center gap-2 text-xs">
          <span className="px-2.5 py-1 rounded-full bg-gray-800 border border-gray-700 text-gray-300">
            Geo: {geo}
          </span>
          <span className="px-2.5 py-1 rounded-full bg-gray-800 border border-gray-700 text-gray-300">
            Período: hoje 12m
          </span>
          <span className="px-2.5 py-1 rounded-full bg-gray-800 border border-gray-700 text-gray-300">
            Categoria: {categoryLabel}
          </span>
          <span className="inline-flex items-center gap-1 text-gray-400 ml-2">
            <Info className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">
              Interesse (0–100) • Top (0–100) • Rising (% vs período anterior)
            </span>
          </span>
        </div>

        {/* Tabs */}
        <div className="bg-gray-800 rounded-lg shadow-sm border border-gray-700 mb-8">
          <div className="border-b border-gray-700">
            <nav className="flex space-x-8 px-6">
              {[
                { id: "tendencias", label: "Tendências" },
                { id: "analise", label: "Análise de Busca" },
                { id: "youtube", label: "YouTube Trends" },
                { id: "noticias", label: "Notícias & Insights" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === (tab.id as any)
                      ? "border-blue-500 text-blue-400"
                      : "border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Conteúdo */}
          <div className="p-6">
            {/* TENDÊNCIAS */}
            {activeTab === "tendencias" && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2">
                  <div className="flex items-center gap-2 mb-6">
                    <TrendingUp className="w-5 h-5 text-gray-300" />
                    <h2 className="text-lg font-semibold text-white">
                      Tópicos em Alta
                    </h2>
                    {isLoadingTermTrending && (
                      <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                    )}
                  </div>

                  {/* Card principal */}
                  {!mainCard && !isLoadingTermTrending ? (
                    <div className="text-sm text-gray-400">
                      Faça uma pesquisa para ver o termo e as consultas
                      relacionadas.
                    </div>
                  ) : isLoadingTermTrending ? (
                    <div className="bg-gray-700 border border-gray-600 rounded-lg p-4 animate-pulse">
                      <div className="h-4 bg-gray-600 rounded w-3/4 mb-2" />
                      <div className="h-3 bg-gray-600 rounded w-1/2" />
                    </div>
                  ) : mainCard ? (
                    <div className="space-y-6">
                      <div className="bg-gray-700 border border-gray-600 rounded-lg p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-yellow-500 text-yellow-900">
                                #1
                              </span>
                              <h3 className="font-semibold text-white">
                                {mainCard.title}
                              </h3>
                              <span className="text-xs px-2 py-1 rounded-full bg-gray-600 text-gray-300">
                                Termo
                              </span>
                              <span
                                className={`text-xs font-bold ${scoreColor(
                                  mainCard.score
                                )}`}
                              >
                                {mainCard.score} pts
                              </span>
                            </div>
                            <div className="flex items-center gap-4 text-sm text-gray-400">
                              <div
                                className="flex items-center gap-1"
                                title="Interesse (0–100) no período"
                              >
                                <Users className="w-4 h-4" />
                                {mainCard.interesse}/100 interesse
                              </div>
                              <span
                                className={`px-2 py-1 rounded-full text-xs ${difficultyClass(
                                  mainCard.difficulty
                                )}`}
                              >
                                {mainCard.difficulty}
                              </span>
                            </div>
                          </div>
                          <div className="text-right">
                            <div
                              className={`flex items-center gap-1 ${
                                mainCard.growthPct >= 0
                                  ? "text-green-400"
                                  : "text-red-400"
                              } font-semibold`}
                            >
                              <ArrowUp className="w-4 h-4" />
                              {pct(mainCard.growthPct)}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Top */}
                      <div className="bg-gray-800 border border-gray-700 rounded-lg">
                        <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-2">
                          <ArrowRightLeft className="w-4 h-4 text-gray-300" />
                          <h4 className="text-sm font-semibold text-white">
                            Consultas relacionadas (Top)
                          </h4>
                          <span className="text-[11px] text-gray-400">
                            0–100
                          </span>
                        </div>
                        <ul className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                          {relatedTop.map((rq, i) => (
                            <li
                              key={`top-${i}-${rq.query}`}
                              className="bg-gray-700/60 border border-gray-600 rounded-lg px-3 py-2 flex items-center justify-between"
                            >
                              <div className="flex items-center gap-2">
                                <span className="text-xs px-2 py-1 rounded-full bg-blue-600 text-blue-100">
                                  Top
                                </span>
                                <span className="text-sm text-white">
                                  {rq.query}
                                </span>
                              </div>
                              <span className="text-xs text-gray-300">
                                {rq.value}/100
                              </span>
                            </li>
                          ))}
                          {!relatedTop.length && (
                            <li className="text-xs text-gray-400">
                              Nenhuma consulta Top.
                            </li>
                          )}
                        </ul>
                      </div>

                      {/* Rising */}
                      <div className="bg-gray-800 border border-gray-700 rounded-lg">
                        <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-2">
                          <TrendingUp className="w-4 h-4 text-gray-300" />
                          <h4 className="text-sm font-semibold text-white">
                            Em ascensão (Rising)
                          </h4>
                          <span className="text-[11px] text-gray-400">
                            % vs período anterior
                          </span>
                        </div>
                        <ul className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                          {relatedRising.map((rq, i) => (
                            <li
                              key={`rising-${i}-${rq.query}`}
                              className="bg-gray-700/60 border border-gray-600 rounded-lg px-3 py-2 flex items-center justify-between"
                            >
                              <div className="flex items-center gap-2">
                                <span className="text-xs px-2 py-1 rounded-full bg-orange-600 text-orange-100">
                                  Rising
                                </span>
                                <span className="text-sm text-white">
                                  {rq.query}
                                </span>
                              </div>
                              <span className="text-xs font-semibold text-green-400">
                                +{rq.value}%
                              </span>
                            </li>
                          ))}
                          {!relatedRising.length && (
                            <li className="text-xs text-gray-400">
                              Nenhuma consulta em ascensão.
                            </li>
                          )}
                        </ul>
                      </div>

                      {/* Resumo do Analyze */}
                      {analysis && (
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          {/* KPIs */}
                          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                            <div className="flex items-center gap-2 mb-2">
                              <BarChart3 className="w-4 h-4 text-gray-300" />
                              <h4 className="text-sm font-semibold text-white">
                                KPIs do tema
                              </h4>
                            </div>
                            <div className="text-xs text-gray-300 space-y-1">
                              <div>
                                Atual:{" "}
                                {analysis.overall_metrics.current_interest}/100
                              </div>
                              <div>
                                Média:{" "}
                                {Math.round(
                                  Number(
                                    analysis.overall_metrics.average_interest
                                  )
                                )}
                                /100
                              </div>
                              <div>
                                Pico: {analysis.overall_metrics.peak_interest}
                                /100
                              </div>
                              <div
                                className={`${
                                  (analysis.overall_metrics.growth_rate ?? 0) >=
                                  0
                                    ? "text-green-400"
                                    : "text-red-400"
                                }`}
                              >
                                {(analysis.overall_metrics.growth_rate ?? 0) >=
                                0
                                  ? "+"
                                  : ""}
                                {Math.round(
                                  Number(
                                    analysis.overall_metrics.growth_rate ?? 0
                                  )
                                )}
                                % (12m)
                              </div>
                              <div>
                                Direção:{" "}
                                {analysis.overall_metrics.trend_direction}
                              </div>
                            </div>
                          </div>

                          {/* Sazonalidade & Previsão */}
                          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                            <div className="text-xs text-gray-400 mb-1">
                              Picos sazonais
                            </div>
                            <div className="flex flex-wrap gap-1">
                              {(analysis as any).seasonal_patterns?.peak_months
                                ?.length ? (
                                (
                                  analysis as any
                                ).seasonal_patterns.peak_months.map(
                                  (m: string, i: number) => (
                                    <span
                                      key={i}
                                      className="px-2 py-0.5 rounded-full bg-gray-600 text-gray-100 text-[11px]"
                                    >
                                      {m}
                                    </span>
                                  )
                                )
                              ) : (
                                <span className="text-xs text-gray-500">—</span>
                              )}
                            </div>
                            <div className="text-xs text-gray-400 mt-3">
                              Previsão 30d
                            </div>
                            <div className="text-sm text-gray-200">
                              {(analysis as any).future_predictions
                                ?.next_30_days ?? "—"}
                            </div>
                          </div>

                          {/* Geografia */}
                          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                            <div className="flex items-center gap-2 mb-2">
                              <MapPin className="w-4 h-4 text-gray-300" />
                              <h4 className="text-sm font-semibold text-white">
                                Top regiões
                              </h4>
                            </div>
                            <div className="space-y-2">
                              {topRegions.length ? (
                                topRegions.map((g: any, i) => (
                                  <div
                                    key={i}
                                    className="text-xs text-gray-300"
                                  >
                                    <div className="flex justify-between">
                                      <span>
                                        #{g.interest_rank ?? i + 1} {g.region}
                                      </span>
                                      <span>{g.interest_score}/100</span>
                                    </div>
                                    <div className="h-1.5 bg-gray-700 rounded">
                                      <div
                                        className="h-1.5 bg-blue-500 rounded"
                                        style={{
                                          width: `${Math.min(
                                            100,
                                            g.interest_score ?? 0
                                          )}%`,
                                        }}
                                      />
                                    </div>
                                  </div>
                                ))
                              ) : (
                                <div className="text-xs text-gray-500">—</div>
                              )}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Keywords-alvo sugeridas */}
                      {kwTargets.length > 0 && (
                        <div className="bg-gray-800 border border-gray-700 rounded-lg mt-4">
                          <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-2">
                            <TrendingUp className="w-4 h-4 text-gray-300" />
                            <h4 className="text-sm font-semibold text-white">
                              Palavras-chave sugeridas (análise)
                            </h4>
                            <span className="text-[11px] text-gray-400">
                              priorize as de maior score
                            </span>
                          </div>
                          <ul className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                            {kwTargets.map((k, i) => (
                              <li
                                key={`${k.text}-${i}`}
                                className="bg-gray-700/60 border border-gray-600 rounded-lg px-3 py-2"
                              >
                                <div className="flex items-center justify-between">
                                  <span className="text-sm text-white">
                                    {k.text}
                                  </span>
                                  <span className="text-xs text-gray-300">
                                    {k.search_volume}
                                  </span>
                                </div>
                                <div className="mt-1 flex items-center justify-between text-[11px] text-gray-400">
                                  <span>Dificuldade: {k.difficulty}</span>
                                  <span>
                                    Score:{" "}
                                    {Math.round(
                                      Number(k.opportunity_score ?? 0)
                                    )}
                                  </span>
                                </div>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : null}
                </div>

                {/* Oportunidades Reais */}
                <div>
                  <div className="flex items-center gap-2 mb-6">
                    <Lightbulb className="w-5 h-5 text-gray-300" />
                    <h2 className="text-lg font-semibold text-white">
                      Oportunidades de Conteúdo
                    </h2>
                    {isLoadingOpportunities && (
                      <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                    )}
                  </div>

                  <div className="space-y-4">
                    {realTimeOpportunities.length > 0 ? (
                      realTimeOpportunities.map((opp, idx) => (
                        <div
                          key={idx}
                          className={`border-2 rounded-lg p-4 bg-gray-700 ${
                            opp.opportunity_type === "alta_oportunidade"
                              ? "border-green-500 bg-green-900/20"
                              : opp.opportunity_type === "trending_topic"
                              ? "border-blue-500 bg-blue-900/20"
                              : "border-purple-500 bg-purple-900/20"
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <div className="text-gray-300 mt-0.5">
                              {opp.opportunity_type === "alta_oportunidade" ? (
                                <Target className="w-5 h-5" />
                              ) : opp.opportunity_type === "trending_topic" ? (
                                <TrendingUp className="w-5 h-5" />
                              ) : (
                                <Eye className="w-5 h-5" />
                              )}
                            </div>
                            <div className="flex-1">
                              <h3 className="font-medium text-white mb-1">
                                {opp.opportunity_type === "alta_oportunidade"
                                  ? "Alta Oportunidade"
                                  : opp.opportunity_type === "trending_topic"
                                  ? "Trending Topic"
                                  : "Nicho Específico"}
                              </h3>
                              <p className="text-sm text-gray-300 mb-2">
                                <span className="font-medium">
                                  "{opp.topic}"
                                </span>
                              </p>

                              {opp.description && (
                                <p className="text-xs text-gray-400 mb-2">
                                  {opp.description}
                                </p>
                              )}

                              <div className="text-xs text-gray-400 mb-2">
                                {(() => {
                                  const interestValue = computeInterest(
                                    opp,
                                    analysis
                                  );
                                  const growth = computeGrowth(opp, analysis);
                                  return (
                                    <>
                                      Interesse:{" "}
                                      <span className="font-semibold text-gray-200">
                                        {interestValue}/100
                                      </span>
                                      {growth !== null && (
                                        <>
                                          {" "}
                                          •{" "}
                                          <span
                                            className={
                                              growth >= 0
                                                ? "text-green-400 font-semibold"
                                                : "text-red-400 font-semibold"
                                            }
                                          >
                                            {growth >= 0 ? "+" : ""}
                                            {growth}%
                                          </span>
                                        </>
                                      )}{" "}
                                      • {opp.target_audience || "—"}
                                    </>
                                  );
                                })()}
                              </div>

                              <div className="flex flex-wrap gap-1">
                                {(opp.suggested_content_types ?? [])
                                  .slice(0, 3)
                                  .map((type, i) => (
                                    <span
                                      key={i}
                                      className="px-2 py-1 bg-gray-600 text-gray-300 rounded text-xs"
                                    >
                                      {type}
                                    </span>
                                  ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : !isLoadingOpportunities ? (
                      <div className="text-sm text-gray-400">
                        Pesquise um termo para ver oportunidades personalizadas.
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            )}

            {/* ANÁLISE */}
            {activeTab === "analise" && (
              <div>
                {isLoadingPreview ? (
                  <div className="text-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-white mb-2">
                      Analisando tema…
                    </h3>
                    <p className="text-gray-400">
                      Buscando dados de tendências e oportunidades
                    </p>
                  </div>
                ) : preview ? (
                  <div className="space-y-6">
                    <div className="bg-gray-700 rounded-lg p-6 border border-gray-600">
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="text-xl font-bold text-white mb-1">
                            {preview.tema}
                          </h3>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            {preview.categoria || "geral"}
                          </span>
                        </div>
                        <div
                          className={`text-center px-4 py-2 rounded-lg border ${
                            preview.viabilidade_score >= 85
                              ? "text-green-400 bg-green-900/20 border-green-500"
                              : preview.viabilidade_score >= 65
                              ? "text-yellow-400 bg-yellow-900/20 border-yellow-500"
                              : "text-red-400 bg-red-900/20 border-red-500"
                          }`}
                        >
                          <div className="text-2xl font-bold">
                            {preview.viabilidade_score}
                          </div>
                          <div className="text-xs font-medium">Score</div>
                        </div>
                      </div>

                      <p className="text-sm font-medium text-gray-300 mb-4">
                        {preview.oportunidade?.label || "Oportunidade"}
                      </p>

                      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                        <div className="text-center">
                          <div className="text-xl font-bold text-blue-400">
                            {preview.trend_growth_pct != null &&
                            preview.trend_growth_pct >= 0
                              ? "+"
                              : ""}
                            {preview.trend_growth_pct ?? 0}%
                          </div>
                          <div className="text-xs text-gray-400">
                            Crescimento
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="text-xl font-bold text-green-400">
                            {preview.volume_estimado != null
                              ? nf(preview.volume_estimado)
                              : "—"}
                          </div>
                          <div className="text-xs text-gray-400">Volume</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xl font-bold text-purple-400">
                            {preview.tempo_estimado_preparo || "—"}
                          </div>
                          <div className="text-xs text-gray-400">
                            Prep. Time
                          </div>
                        </div>
                        <div className="text-center">
                          <span
                            className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${difficultyClass(
                              preview.dificuldade
                            )}`}
                          >
                            {preview.dificuldade || "Medium"}
                          </span>
                          <div className="text-xs text-gray-400 mt-1">
                            Dificuldade
                          </div>
                        </div>
                      </div>

                      {preview.badges?.length ? (
                        <div className="flex flex-wrap gap-2 mb-6">
                          {preview.badges.map((b, i) => (
                            <span
                              key={`${b}-${i}`}
                              className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800"
                            >
                              {b}
                            </span>
                          ))}
                        </div>
                      ) : null}

                      {preview.insights?.length ? (
                        <div className="mb-6">
                          <h4 className="text-sm font-semibold text-white mb-3">
                            Insights
                          </h4>
                          <ul className="space-y-2">
                            {preview.insights.map((ins, i) => (
                              <li
                                key={`${ins}-${i}`}
                                className="text-sm text-gray-300 flex items-start gap-2"
                              >
                                <ArrowUp className="w-3 h-3 text-blue-500 mt-0.5 flex-shrink-0" />
                                {ins}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}

                      {preview.palavras_chave?.length ? (
                        <div className="mb-6">
                          <h4 className="text-sm font-semibold text-white mb-3">
                            Palavras-chave
                          </h4>
                          <div className="flex flex-wrap gap-2">
                            {preview.palavras_chave.map((k, i) => (
                              <span
                                key={`${k}-${i}`}
                                className="px-3 py-1 bg-gray-600 text-gray-300 rounded-full text-sm"
                              >
                                {k}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition-colors">
                        {preview.cta?.label || "Gerar Pauta Completa"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <div className="inline-flex items-center gap-2 text-gray-400 mb-4">
                      <Calendar className="w-8 h-8" />
                    </div>
                    <h3 className="text-lg font-medium text-white mb-2">
                      Análise de Busca
                    </h3>
                    <p className="text-gray-400">
                      Faça uma pesquisa para ver análises detalhadas.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* YOUTUBE */}
            {activeTab === "youtube" && (
              <div>
                <div className="flex items-center gap-2 mb-6">
                  <Play className="w-5 h-5 text-gray-300" />
                  <h2 className="text-lg font-semibold text-white">
                    YouTube Trends
                  </h2>
                  {isLoadingYouTube && (
                    <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                  )}
                </div>

                {!youtube.length && !isLoadingYouTube ? (
                  <div className="text-center py-12 text-gray-400">
                    Faça uma pesquisa para ver vídeos em alta relacionados ao
                    tema.
                  </div>
                ) : isLoadingYouTube ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <div
                        key={i}
                        className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden animate-pulse"
                      >
                        <div className="h-40 bg-gray-700" />
                        <div className="p-4 space-y-2">
                          <div className="h-4 bg-gray-700 rounded w-3/4" />
                          <div className="h-3 bg-gray-700 rounded w-1/2" />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {youtube.map((v) => (
                      <div
                        key={v.id}
                        className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden flex flex-col"
                      >
                        {/* Thumb */}
                        <a
                          href={`https://www.youtube.com/watch?v=${encodeURIComponent(
                            v.id
                          )}`}
                          target="_blank"
                          rel="noreferrer"
                          className="relative block"
                        >
                          <img
                            src={v.thumbnail_url}
                            alt={v.title}
                            className="w-full h-40 object-cover"
                            loading="lazy"
                          />
                          <span className="absolute bottom-2 right-2 text-xs bg-black/70 text-white px-2 py-0.5 rounded">
                            {fmtYTDuration(v.duration)}
                          </span>
                        </a>

                        {/* Body */}
                        <div className="p-4 flex-1 flex flex-col gap-2">
                          <a
                            href={`https://www.youtube.com/watch?v=${encodeURIComponent(
                              v.id
                            )}`}
                            target="_blank"
                            rel="noreferrer"
                            className="font-semibold text-white line-clamp-2 hover:underline"
                            title={v.title}
                          >
                            {v.title}
                          </a>

                          <div className="text-xs text-gray-400 flex items-center justify-between">
                            <a
                              href={`https://www.youtube.com/channel/${encodeURIComponent(
                                v.channel_id
                              )}`}
                              target="_blank"
                              rel="noreferrer"
                              className="hover:text-gray-300"
                              title={v.channel_title}
                            >
                              {v.channel_title}
                            </a>
                            <span>{fmtDateBR(v.published_at)}</span>
                          </div>

                          <div className="mt-2 grid grid-cols-3 gap-2 text-[11px] text-gray-300">
                            <div className="bg-gray-700/50 rounded px-2 py-1 text-center">
                              {v.view_count != null
                                ? nf(Number(v.view_count))
                                : "—"}{" "}
                              views
                            </div>
                            <div className="bg-gray-700/50 rounded px-2 py-1 text-center">
                              {v.like_count != null
                                ? nf(Number(v.like_count))
                                : "—"}{" "}
                              likes
                            </div>
                            <div className="bg-gray-700/50 rounded px-2 py-1 text-center">
                              {v.comment_count != null
                                ? nf(Number(v.comment_count))
                                : "—"}{" "}
                              coments
                            </div>
                          </div>

                          <div className="flex flex-wrap gap-2 mt-2">
                            {v.trending_rank != null && (
                              <span className="text-[11px] px-2 py-0.5 rounded bg-yellow-600 text-yellow-100">
                                #{v.trending_rank}
                              </span>
                            )}
                            {v.trending_score != null && (
                              <span className="text-[11px] px-2 py-0.5 rounded bg-blue-600 text-blue-100">
                                score {Math.round(Number(v.trending_score))}
                              </span>
                            )}
                            {!!v.category_name && (
                              <span className="text-[11px] px-2 py-0.5 rounded bg-gray-600 text-gray-100">
                                {v.category_name}
                              </span>
                            )}
                          </div>

                          {/* Description (opcional, com clamp) */}
                          {v.description && (
                            <p className="text-xs text-gray-400 mt-2 line-clamp-3">
                              {v.description}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "noticias" && (
              <div>
                {isLoadingNews ? (
                  <div className="text-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-white mb-2">
                      Analisando notícias…
                    </h3>
                    <p className="text-gray-400">
                      Buscando artigos e gerando insights
                    </p>
                  </div>
                ) : !newsData ? (
                  <div className="text-center py-12">
                    <div className="inline-flex items-center gap-2 text-gray-400 mb-4">
                      <Zap className="w-8 h-8" />
                    </div>
                    <h3 className="text-lg font-medium text-white mb-2">
                      Notícias & Insights
                    </h3>
                    <p className="text-gray-400">
                      Faça uma pesquisa para ver notícias recentes.
                    </p>
                    {newsError && (
                      <p className="mt-2 text-red-400 text-sm">{newsError}</p>
                    )}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Lista de artigos */}
                    <div className="lg:col-span-2 space-y-4">
                      {newsData.articles.map((a) => (
                        <a
                          key={a.id}
                          href={a.url}
                          target="_blank"
                          rel="noreferrer"
                          className="block bg-gray-700 border border-gray-600 rounded-lg overflow-hidden hover:border-blue-500"
                        >
                          <div className="flex">
                            {a.url_to_image && (
                              <img
                                src={a.url_to_image}
                                alt={a.title}
                                className="hidden sm:block w-40 h-28 object-cover"
                              />
                            )}
                            <div className="p-4 flex-1">
                              <div className="text-xs text-gray-400 mb-1">
                                {a.source?.name || "—"} •{" "}
                                {fmtDateTime(a.published_at)}
                              </div>
                              <div className="font-semibold text-white">
                                {a.title}
                              </div>
                              {a.description && (
                                <p className="text-sm text-gray-300 mt-1 line-clamp-2">
                                  {a.description}
                                </p>
                              )}
                              <div className="mt-2 text-[11px] text-gray-400 flex flex-wrap gap-2">
                                {a.category && (
                                  <span className="px-2 py-0.5 rounded bg-gray-600 text-gray-100">
                                    {a.category}
                                  </span>
                                )}
                                <span
                                  className={`px-2 py-0.5 rounded ${sentimentBadgeClass(
                                    a.sentiment
                                  )}`}
                                >
                                  {a.sentiment || "neutral"}
                                </span>
                                {typeof a.trending_score === "number" && (
                                  <span className="px-2 py-0.5 rounded bg-gray-600 text-gray-100">
                                    Trend {Math.round(a.trending_score)}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </a>
                      ))}
                      {!newsData.articles.length && (
                        <div className="text-sm text-gray-400">
                          Nenhum artigo encontrado.
                        </div>
                      )}
                    </div>

                    {/* Painéis laterais: Insights e Tópicos em alta */}
                    <div className="space-y-4">
                      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                        <h4 className="text-sm font-semibold text-white mb-3">
                          Insights
                        </h4>
                        {newsData.insights?.length ? (
                          <ul className="space-y-3">
                            {newsData.insights.slice(0, 5).map((ins) => (
                              <li
                                key={ins.id}
                                className="text-sm text-gray-300"
                              >
                                <div className="font-medium text-white">
                                  {ins.title}
                                </div>
                                <div className="text-xs text-gray-400">
                                  {ins.description}
                                </div>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <div className="text-xs text-gray-400">—</div>
                        )}
                      </div>

                      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                        <h4 className="text-sm font-semibold text-white mb-3">
                          Tópicos em alta
                        </h4>
                        {newsData.trending_topics?.length ? (
                          <ul className="space-y-2">
                            {newsData.trending_topics.slice(0, 6).map((t) => (
                              <li
                                key={t.topic}
                                className="flex justify-between text-sm text-gray-300"
                              >
                                <span>{t.topic}</span>
                                {typeof t.growth_rate === "number" && (
                                  <span className="text-gray-400">
                                    {Math.round(t.growth_rate)}%
                                  </span>
                                )}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <div className="text-xs text-gray-400">—</div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};


export default PesquisaInsightsDashboard;
