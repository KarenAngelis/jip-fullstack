// src/lib/api.ts
// =========================================================
// Cliente HTTP (Axios) + SDK: authAPI, newsAPI, pautasAPI,
// trendsAPI, youtubeAPI, newsInsightsAPI e helpers.
// - Usa NEXT_PUBLIC_API_URL
// - Injeta token (cookie/localStorage) no Authorization
// - Normaliza erros do FastAPI (inclui 422)
// - Trends: analyze(payload) é a ASSINATURA principal
//   (aceita {keywords: string[]} ou {keyword: string})
//   e search() adapta p/ shape legado a partir do analyze.
// - Sanitiza body de /trends/analyze (nunca envia include_related;
//   não envia category quando for 0/null/undefined).
// =========================================================

import axios, {
  AxiosHeaders,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
  type AxiosError,
  isAxiosError,
} from "axios";
import Cookies from "js-cookie";

/* ==================== Base URLs ==================== */
const RAW = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const API_ROOT = RAW.replace(/\/+$/, "");
export const API_BASE = API_ROOT.endsWith("/api") ? API_ROOT : `${API_ROOT}/api`;

/* =================== Axios Instance =================== */
const http: AxiosInstance = axios.create({
  baseURL: API_ROOT, // passamos "/api/..." nas rotas abaixo
  headers: {
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
  },
  timeout: 120_000,
  withCredentials: false, // usando Bearer token, não cookies HTTPOnly
});

/* ================= Helpers internos (token/header) ================= */
function getToken(): string | undefined {
  if (typeof window === "undefined") return undefined;
  const cookie = Cookies.get("access_token");
  return cookie ?? localStorage.getItem("access_token") ?? undefined;
}

/** Define/remove Authorization no axios.defaults de forma tipada */
function setGlobalAuthHeader(token?: string) {
  const headersAsAxios = http.defaults.headers as unknown as AxiosHeaders;
  const hasSet = typeof (headersAsAxios as any).set === "function";
  const hasDelete = typeof (headersAsAxios as any).delete === "function";

  if (hasSet && hasDelete) {
    if (token) {
      headersAsAxios.set("Authorization", `Bearer ${token}`);
    } else {
      if ((headersAsAxios as any).has?.("Authorization")) {
        (headersAsAxios as any).delete("Authorization");
      }
    }
    return;
  }

  // Fallback: shape antigo (common.Authorization)
  const anyHeaders = http.defaults.headers as Record<string, any>;
  anyHeaders.common = { ...(anyHeaders.common || {}) };
  if (token) anyHeaders.common.Authorization = `Bearer ${token}`;
  else delete anyHeaders.common.Authorization;
}

/* ============ Injeta token (cookie OU localStorage) ============ */
http.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getToken();

    if (token) {
      const h = (config.headers = new AxiosHeaders(config.headers));
      h.set("Authorization", `Bearer ${token}`);
      if (process.env.NODE_ENV !== "production") {
        console.log("🔑 Authorization: Bearer", token.slice(0, 10) + "…");
      }
    } else if (process.env.NODE_ENV !== "production") {
      console.log("⚠️ Sem token para Authorization");
    }

    // opcional: mantém defaults alinhados
    setGlobalAuthHeader(getToken());

    // 👇 Sanitização extra para /trends/analyze (defensivo)
    if (config.url?.includes("/api/trends/analyze") && config.data && typeof config.data === "object") {
      // nunca envie include_related (backend rejeita)
      if ("include_related" in (config.data as any)) {
        delete (config.data as any).include_related;
      }
      // remova category inválida (0/null/undefined)
      const cat = (config.data as any).category;
      if (cat == null || Number(cat) === 0) {
        delete (config.data as any).category;
      }
    }

    if (process.env.NODE_ENV !== "production") {
      console.log("📡 Request:", (config.baseURL || "") + (config.url || ""));
    }
    return config;
  },
  (error) => {
    console.error("❌ Erro no interceptor de request:", error);
    return Promise.reject(error);
  }
);

/* ======== Type-guards p/ normalizar erros do FastAPI ======== */
type UnknownRecord = Record<string, unknown>;

interface FastAPIValidationItem {
  loc: Array<string | number>;
  msg: string;
  type?: string;
}
type FastAPIDetail = string | FastAPIValidationItem[] | UnknownRecord;

interface ErrorPayload {
  detail?: FastAPIDetail;
  message?: string;
}

const isObject = (v: unknown): v is UnknownRecord =>
  typeof v === "object" && v !== null;

const isValidationItem = (v: unknown): v is FastAPIValidationItem =>
  isObject(v) &&
  "loc" in v &&
  Array.isArray((v as { loc: unknown }).loc) &&
  "msg" in v &&
  typeof (v as { msg: unknown }).msg === "string";

const isValidationArray = (v: unknown): v is FastAPIValidationItem[] =>
  Array.isArray(v) && v.every(isValidationItem);

const isErrorPayload = (v: unknown): v is ErrorPayload =>
  isObject(v) && ("detail" in v || "message" in v);

function parseFastAPIDetail(detail: FastAPIDetail): string {
  if (isValidationArray(detail)) {
    return detail
      .map((d) => {
        const loc = d.loc.join(".");
        return loc ? `${loc}: ${d.msg}` : d.msg;
      })
      .join(" | ");
  }
  if (typeof detail === "string") return detail;
  try {
    return JSON.stringify(detail);
  } catch {
    return String(detail);
  }
}

/* ============ Normalização de erros (sem assertions) ============ */
http.interceptors.response.use(
  (res) => res,
  (unknownErr: unknown) => {
    if (!isAxiosError(unknownErr)) {
      return Promise.reject(
        unknownErr instanceof Error ? unknownErr : new Error(String(unknownErr))
      );
    }

    const err = unknownErr as AxiosError<unknown>;
    const status = err.response?.status;
    const data = err.response?.data;

    console.error(`❌ Erro na API [${status}]:`, err.message);
    if (process.env.NODE_ENV !== "production") {
      console.error("↳ Response data:", data);
    }

    if (isErrorPayload(data)) {
      if (typeof data.message === "string") {
        err.message = `[${status}] ${data.message}`;
      } else if (data.detail !== undefined) {
        err.message = `[${status}] ${parseFastAPIDetail(data.detail)}`;
      }
    } else if (!status) {
      err.message = "Falha de rede ou servidor indisponível.";
    }

    if (status === 401) {
      console.log("🔄 401: limpando credenciais…");
      Cookies.remove("access_token", { path: "/" });
      Cookies.remove("user_data", { path: "/" });
      if (typeof window !== "undefined") localStorage.removeItem("access_token");
      setGlobalAuthHeader(undefined);
    }

    return Promise.reject(err);
  }
);

/* ==================== Helpers HTTP ==================== */
export const get = async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  const res = await http.get<T>(url, config);
  return res.data;
};
export const post = async <T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig
): Promise<T> => {
  const res = await http.post<T>(url, body, config);
  return res.data;
};

/* ===================== Tipos Comuns ===================== */
export interface User {
  id: number;
  email: string;
  nome?: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}
export interface LoginData { email: string; password: string; }
export interface RegisterData { email: string; password: string; nome?: string; }

/* ======================== Auth API ======================== */
const LOGIN_URL = "/api/auth/login";
const REGISTER_URL = "/api/auth/register";
const ME_URL = "/api/auth/me";
const VERIFY_URL = "/api/auth/verify-token";

export const authAPI = {
  login: async (data: LoginData) => {
    console.log("🔐 Fazendo login…");
    const out = await post<{ access_token: string; token_type: string; user: User }>(
      LOGIN_URL,
      data
    );

    // Salva token e usuário
    const cookieOptions = {
      expires: 7,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax" as const,
      path: "/",
    };
    Cookies.set("access_token", out.access_token, cookieOptions);
    Cookies.set("user_data", JSON.stringify(out.user), cookieOptions);

    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", out.access_token);
    }

    // Header global para próximas requisições axios
    setGlobalAuthHeader(out.access_token);

    console.log("✅ Login ok •", out.user.email);
    return out;
  },

  register: (data: RegisterData) => post<User>(REGISTER_URL, data),

  verifyToken: () => get<{ message: string; user: User }>(VERIFY_URL),

  getMe: () => get<User>(ME_URL),

  logout: () => {
    Cookies.remove("access_token", { path: "/" });
    Cookies.remove("user_data", { path: "/" });
    if (typeof window !== "undefined") localStorage.removeItem("access_token");
    setGlobalAuthHeader(undefined);
  },
};

/* ======================= Pautas ======================= */
export interface ArtigoRef {
  titulo: string;
  fonte: string;
  data: string;
  url: string;
  resumo: string;
  confiabilidade: string;
}
export interface TrendsDetalhadas {
  keywords: string[];
  volume_busca_mensal: number;
  crescimento_30_dias: string;
  tendencia: string;
  popularidade_score: number;
  pico_interesse: string;
  previsao_proximo_mes: string;
  interesse_regional: Record<string, number>;
}
export interface DeepResearch { validacao: string[]; }
export interface RoteiroEstruturado {
  abertura: string;
  bloco_1: string;
  bloco_2: string;
  bloco_3: string;
  conclusao: string;
}
export interface PautaResponse {
  tema: string;
  duracao_min: number;
  resumo_executivo: string[];
  titulos_sugeridos: string[];
  perguntas_sugeridas: string[];
  artigos_referencia: ArtigoRef[];
  trends_detalhadas: TrendsDetalhadas;
  deep_research: DeepResearch;
  roteiro_estruturado: RoteiroEstruturado;
  status: string;
}
export interface PautaRequest { tema: string; duracao_desejada: number; }

/** ⚠️ Tipo de item que vem da listagem do backend */
export interface PautaListItem {
  id: number;
  tema: string;
  duracao_min: number;
  status: string;
  resumo_executivo?: string[] | null;
  titulos_sugeridos?: string[] | null;
  perguntas_sugeridas?: string[] | null;
  artigos_referencia?: ArtigoRef[] | null;
  trends_detalhadas?: TrendsDetalhadas | Record<string, any> | null;
  deep_research?: DeepResearch | Record<string, any> | null;
  roteiro_estruturado?: RoteiroEstruturado | Record<string, any> | null;
  volume_busca_mensal?: number | null;
  popularidade_score?: number | null;
  crescimento_30_dias?: number | null;
  tendencia?: string | null;
  user_id?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export const pautasAPI = {
  generate: (data: PautaRequest) => post<PautaResponse>("/api/pautas/generate", data),

  // ✅ agora compatível com o backend: { pautas: [...], total }
  list: () => get<{ pautas: PautaListItem[]; total: number }>("/api/pautas"),

  getById: (id: string) => get<PautaResponse>(`/api/pautas/${id}`),
};

/* ===================== Títulos (tipos p/ outro módulo) ===================== */
export interface TitleItem {
  title: string;
  score: number;
  engagement: number;
  seo: number;
  trend: number;
  trends_used: string[];
  power_words: string[];
}
export interface TitlesResponse {
  success: boolean;
  titles: TitleItem[];
  trends_found: string[];
  generation_time: number;
}
export interface TitlesRequest {
  topic: string;
  audience: string;
  tone: string;
  quantity: number;
}

/* ===================== Scripts (tipos p/ outro módulo) ===================== */
export interface ScriptMetadata {
  topic: string;
  estimated_duration_minutes: number;
  actual_words: number;
  structure_score: number;
  readability_score: number;
  model_used: string;
}
export interface ScriptItem { content: string; score: number; metadata: ScriptMetadata; }
export interface ScriptResponse { success: boolean; script?: ScriptItem; message: string; }
export interface ScriptRequest {
  topic: string;
  duration_minutes: number;
  objectives: string;
  target_audience: string;
  script_style: string;
  include_interactions: boolean;
}

/* ===================== Episódios (tipos p/ outro módulo) ===================== */
export type RiskTolerance = "low" | "medium" | "high";

export interface EpisodeRequest {
  titulo: string;
  tipo_serie: string;
  numero_episodio: number;
  duracao_estimada: number;
  historia_pessoal: string;
  enable_safety_check: boolean;
  risk_tolerance: RiskTolerance;
}
export interface EpisodeOutline { introducao: string; desenvolvimento: string[]; conclusao: string; }
export interface EpisodeBlock { titulo: string; conteudo: string; tempo_estimado: string; }
export interface EpisodeRoteiro { abertura: string; blocos: EpisodeBlock[]; encerramento: string; }

export interface ContentSafetyMeta {
  risk_level: RiskTolerance;
  compliance_score: number;
  has_disclaimers: boolean;
}
export interface EpisodeMetadados {
  tempo_total_estimado: string;
  principais_ctas: string[];
  hashtags_sugeridas: string[];
  pontos_chave: string[];
  disclaimers: string[];
  content_safety: ContentSafetyMeta;
}
export interface SafetyAnalysis {
  risk_level: RiskTolerance;
  compliance_score: number;
  sensitive_topics: string[];
  disclaimers: string[];
  improvements: string[];
  recommendations: string[];
}
export interface EpisodeResponse {
  titulo: string;
  tipo_serie: string;
  numero_episodio: number;
  outline: EpisodeOutline;
  roteiro: EpisodeRoteiro;
  metadados: EpisodeMetadados;
  tempo_geracao: number;
  safety_analysis: SafetyAnalysis;
  warnings: string | null;
}

/* ======================= Trends – Tipos ======================= */
export type TrendOverallMetrics = {
  current_interest: number;
  peak_interest: number;
  average_interest: number;
  growth_rate: number | null;
  volatility?: number | null;
  trend_direction: "crescendo" | "estavel" | "decaindo" | string;
};

export type TrendGeoInsight = {
  region: string;
  state_code?: string;
  interest_score: number;
  interest_rank?: number;
};

export type TrendTargetKeyword = {
  text: string;
  search_volume?: string;
  difficulty?: string | number;
  intent?: string;
  opportunity_score?: number;
};

export type TrendOpportunity = {
  topic?: string;
  hook?: string;
  opportunity_type?: string;
  market_analysis?: Record<string, unknown>;
  competition_analysis?: { level?: "baixo" | "medio" | "alto" | string };
  content_angles?: string[];
  target_keywords?: TrendTargetKeyword[];
  content_types?: string[];
  urgency_level?: "baixa" | "media" | "alta" | "critica" | string;
  best_channels?: string[];
  estimated_roi?: string;
  target_personas?: string[] | string;
  audience_size?: string;
};

export type TrendAnalysisResult = {
  keyword: string;
  analysis_date?: string;
  overall_metrics: TrendOverallMetrics;
  geographical_breakdown?: TrendGeoInsight[];
  historical_performance?: Array<{ date: string; [k: string]: number }>;
  seasonal_patterns?: { peak_months?: string[]; pattern_confidence?: number } | null;
  future_predictions?: { next_30_days?: string; confidence?: number } | null;
  related_topics?: unknown[];
  competitor_content?: unknown[];
  content_gaps?: string[];
  opportunities?: TrendOpportunity[];
  provenance?: unknown;
};

/** —— Tipos “legados” (compat p/ UI antiga) —— */
export interface TrendingTopic {
  title: string;
  query: string;
  traffic: string;
  related_queries: string[];
  category: string;
  location: string;
  trend_date: string;
}
export interface RelatedQuery {
  query: string;
  value: number;
  type: "rising" | "top";
}
type RawGeoRow = { region: string } & Record<string, number>;

export interface TrendDataPoint {
  date: string;
  timestamp: number;
  values: Record<string, number>;
}
export interface TrendDataLegacy {
  keyword: string;
  interest_over_time: TrendDataPoint[];
  related_topics: unknown[];
  related_queries: RelatedQuery[];
  geographical_data: Array<{ region: string; values: Record<string, number> }>;
  category?: string | null;
  timeframe: string;
}
export interface TrendsSearchRequest {
  keywords: string[];
  timeframe?: string;
  geo?: string;
  category?: number | null;
}

/* ===== Tipo legado usado por trendsAPI.opportunities (mantido) ===== */
export interface ContentOpportunity {
  topic: string;
  opportunity_type: string;
  interest_level: number;
  competition_level: "baixo" | "medio" | "alto" | string;
  target_audience: string;
  suggested_content_types: string[];
  estimated_traffic_potential?: string;
  description: string;
}

type HistRow = { date: string } & Record<string, number>;

function toLegacyFromAnalyze(
  analyze: TrendAnalysisResult,
  timeframe: string
): TrendDataLegacy {
  const kw = analyze.keyword;
  const hist = Array.isArray(analyze.historical_performance)
    ? (analyze.historical_performance as HistRow[])
    : [];

  const interest_over_time: TrendDataPoint[] = hist.map((row: HistRow) => {
    const { date, ...rest } = row;
    const timestamp = Date.parse(date);
    return {
      date,
      timestamp: Number.isFinite(timestamp) ? timestamp : Date.now(),
      values: rest,
    };
  });

  const geographical_data_raw: RawGeoRow[] = (analyze.geographical_breakdown ?? []).map(
    (g) => ({ region: g.region, [kw]: g.interest_score }) as RawGeoRow
  );

  const related_queries: RelatedQuery[] =
    (analyze.opportunities?.[0]?.target_keywords ?? []).map((t) => ({
      query: t.text,
      value: Number(t.opportunity_score ?? 0),
      type: "top",
    }));

  return {
    keyword: kw,
    timeframe,
    category: null,
    related_topics: [],
    related_queries,
    interest_over_time,
    geographical_data: geographical_data_raw.map((row) => {
      const { region, ...rest } = row;
      return { region, values: rest };
    }),
  };
}

/* ======================= Builder/Sanitizer p/ analyze ======================= */
type AnalyzeParamsMain =
  | { keywords: string[]; timeframe?: string; geo?: string; category?: number | null; include_predictions?: boolean; include_opportunities?: boolean; }
  | { keyword: string; timeframe?: string; geo?: string; category?: number | null; include_predictions?: boolean; include_opportunities?: boolean; };

function buildAnalyzeBody(payload: AnalyzeParamsMain) {
  const {
    timeframe = "today 12-m",
    geo = "BR",
    include_predictions = true,
    include_opportunities = true,
  } = payload as any;

  const keywords =
    "keyword" in payload
      ? [payload.keyword]
      : Array.isArray((payload as any).keywords)
      ? (payload as any).keywords
      : [];

  const body: any = {
    keywords,
    timeframe,
    geo,
  };

  if (include_predictions === true) body.include_predictions = true;
  if (include_opportunities === true) body.include_opportunities = true;

  // só enviar category quando for > 0
  const category = (payload as any).category;
  if (category != null && Number(category) > 0) body.category = Number(category);

  // nunca mandar include_related (causa 422)
  delete (body as any).include_related;

  return body;
}

/* ======================= Trends API ======================= */
export const trendsAPI = {
  daily: (geo = "BR", limit = 20) =>
    get<TrendingTopic[]>("/api/trends/daily", { params: { geo, limit } }),

  /** ✅ ASSINATURA PRINCIPAL */
  analyze: (payload: AnalyzeParamsMain) => {
    const body = buildAnalyzeBody(payload);
    if (process.env.NODE_ENV !== "production") {
      console.log("🛰️ /api/trends/analyze payload >", body);
    }
    return post<TrendAnalysisResult>("/api/trends/analyze", body);
  },

  /** ♻️ COMPAT: usa analyze e adapta para shape legado */
  search: (payload: TrendsSearchRequest) =>
    (async (): Promise<TrendDataLegacy> => {
      const analyze = await trendsAPI.analyze({
        keywords: payload.keywords,
        timeframe: payload.timeframe ?? "today 12-m",
        geo: payload.geo ?? "BR",
        category: payload.category ?? null,
        include_predictions: true,
        include_opportunities: true,
      });
      return toLegacyFromAnalyze(analyze, payload.timeframe ?? "today 12-m");
    })(),

  realtime: (geo = "BR", category = "all") =>
    get<TrendingTopic[]>("/api/trends/realtime", { params: { geo, category } }),

  /** Endpoint dedicado (se existir) — já retorna no shape legado do front */
  opportunities: (keywords: string[]) => {
    const params = new URLSearchParams();
    keywords.forEach((k) => params.append("keywords", k));
    return get<ContentOpportunity[]>(`/api/trends/opportunities?${params.toString()}`);
  },

  categories: () =>
    get<{ categories: Array<{ id: number; name: string }>; total: number }>(
      "/api/trends/categories"
    ),

  suggestions: (seedKeyword: string) =>
    get<{ seed_keyword: string; suggestions: string[]; generated_at: string }>(
      "/api/trends/keywords/suggestions",
      { params: { seed_keyword: seedKeyword } }
    ),
};

/* ======================= YouTube – Tipos (NOVO) ======================= */
export type YoutubeOrder = "relevance" | "date" | "rating" | "viewCount" | "title";

export interface YoutubeTrendingParams {
  theme: string;               // ex.: "Enem 2025" (obrigatório)
  region_code?: string;        // default: "BR"
  max_results?: number;        // 1..50 (default: 20)
  order?: YoutubeOrder;        // default: "relevance"
  published_after?: string;    // "YYYY-MM-DD"
}

export interface YoutubeTrendingItem {
  id: string;
  title: string;
  channel_title: string;
  channel_id: string;
  published_at: string;        // ISO
  view_count: number | null;
  like_count: number | null;
  comment_count: number | null;
  duration: string;            // ISO8601, ex.: "PT26M18S"
  thumbnail_url: string;
  description: string;
  category_id: string;
  category_name: string;
  tags: string[];
  trending_rank: number | null;
  trending_score: number | null;
}

/* ======================= YouTube – SDK (NOVO) ======================= */
export const youtubeAPI = {
  /** Busca vídeos “trending” a partir do tema (via seu backend) */
  searchTrending: (params: YoutubeTrendingParams) =>
    get<YoutubeTrendingItem[]>("/api/youtube/search-trending", { params }),
};

/* ==================== Utilitários de Debug ==================== */
export const debugAPI = {
  checkAuth: () => {
    console.log("=== DEBUG AUTH ===");
    const cookieToken = Cookies.get("access_token");
    const lsToken =
      typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const userData = Cookies.get("user_data");

    console.log("Cookie token existe:", !!cookieToken);
    console.log("LocalStorage token existe:", !!lsToken);
    console.log("User data existe:", !!userData);

    if (userData) {
      try {
        const user = JSON.parse(userData);
        console.log("Usuário:", user.email);
        return { token: !!(cookieToken || lsToken), user };
      } catch (e) {
        console.error("Erro ao parsear user data:", e);
        return { token: !!(cookieToken || lsToken), user: null };
      }
    }
    console.log("================");
    return { token: !!(cookieToken || lsToken), user: null };
  },

  testAuthAPI: async () => {
    try {
      console.log("🧪 Testando /auth/me…");
      const me = await authAPI.getMe();
      console.log("✅ OK:", me);
      return me;
    } catch (err) {
      console.error("❌ Erro no teste da API:", err);
      throw err;
    }
  },
};

/* ======================= News Insights – Tipos (NOVO) ======================= */
export type NewsSortBy = "publishedAt" | "relevancy" | "popularity";

export interface NewsInsightsRequest {
  query: string;
  category?: string;
  sources?: string[];
  language?: string;           // ex.: "pt"
  from_date?: string;          // ISO 8601
  to_date?: string;            // ISO 8601
  sort_by?: NewsSortBy;        // default: "publishedAt"
  max_results?: number;        // default: 20
}

export interface NewsSourceRef {
  id: string | null;
  name: string | null;
  url: string | null;
  reliability_score?: number;
}

export interface NewsArticle {
  id: string;
  title: string;
  description: string | null;
  content: string | null;
  url: string;
  url_to_image: string | null;
  published_at: string;        // ISO
  source: NewsSourceRef | null;
  category?: string | null;
  sentiment?: "positive" | "negative" | "neutral" | "mixed" | string;
  sentiment_score?: number | null;
  engagement_score?: number | null;
  trending_score?: number | null;
  keywords?: string[];
  entities?: string[] | unknown[];
  topics?: string[];
  read_time_minutes?: number | null;
  language?: string | null;
}

export interface NewsInsight {
  id: string;
  title: string;
  description: string;
  insight_type: "sentiment" | "trend" | "pattern" | string;
  confidence?: number | null;
  related_articles?: string[];
  keywords?: string[];
  time_period?: string | null;
  impact_score?: number | null;
  relevance_score?: number | null;
  created_at?: string;
}

export interface NewsTrendingTopic {
  topic: string;
  category?: string | null;
  article_count?: number | null;
  growth_rate?: number | null;
  sentiment?: string | null;
  trending_score?: number | null;
  engagement_level?: string | null;
  key_articles?: NewsArticle[];
  related_keywords?: string[];
  first_seen?: string | null;
  peak_time?: string | null;
}

export interface NewsInsightsResponse {
  query: string;
  total_results: number;
  articles: NewsArticle[];
  insights: NewsInsight[];
  trending_topics: NewsTrendingTopic[];
  overall_sentiment?: string;
  sentiment_distribution?: Record<string, number>;
  analyzed_at?: string;
  time_range?: string;
}

/* ======================= News & Insights – SDK (NOVO) ======================= */
export const newsAPI = {
  search: (q: string, limit = 20) =>
    get<unknown>("/api/news/news/search", { params: { q, limit } }),
  sources: () => get<unknown>("/api/news/news/sources"),
};

export const newsInsightsAPI = {
  analyze: (body: NewsInsightsRequest) =>
    post<NewsInsightsResponse>("/api/news-insights/analyze", body),
};

export default http;
