// web/src/lib/titles.ts
import { get, post } from "@/lib/api";

/* ======================= Tipos base ======================= */
export type Audience = "iniciantes" | "intermediario" | "avancado" | "geral";
export type Tone =
  | "inspirador"
  | "casual"
  | "divertido"
  | "profissional"
  | "provocativo"
  | "motivacional";

export interface TitlesRequest {
  topic: string;
  audience: Audience;
  tone: Tone;
  quantity: number; // 1..10
}

export interface TitleScores {
  engagement: number;
  seo: number;
  trend: number;
  overall: number;
}

export interface TitleItem {
  title: string;
  scores: TitleScores;
  trends_used?: string[];
  power_words?: string[];
}

export interface TitlesResponse {
  success: boolean;
  titles: TitleItem[];
  trends_found: string[];
  generation_time: number;
  prompt_tokens: number;
  completion_tokens: number;
}

/* ============ Tipos para histórico salvo no banco ============ */
export interface GeneratedTitleItem {
  title: string;
  scores: TitleScores;
  trends_used?: string[];
  power_words?: string[];
}

export interface TitleRecord {
  id: number;
  topic: string;
  usuario_ip?: string;
  created_at: string; // ISO
  audience?: Audience;
  content_type?: string;
  tone?: Tone | string;
  quantity?: number;
  max_length?: number;
  use_trends?: boolean;
  include_numbers?: boolean;
  include_power_words?: boolean;

  // quando vier do DETALHE
  titles_generated?: GeneratedTitleItem[];
  titles?: GeneratedTitleItem[];

  // metadados (lista)
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

export type ListTitlesParams = {
  topic?: string;
  limit?: number;
  offset?: number;
  order?: "desc" | "asc";
};

export type Paginated<T> = { items: T[]; total: number };

/* ======================= Helpers ======================= */
function buildQuery(params: Record<string, string | number | undefined>): string {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && String(v).length > 0) {
      qs.set(k, String(v));
    }
  });
  const s = qs.toString();
  return s ? `?${s}` : "";
}

/* ======================= API ======================= */
export const titlesAPI = {
  /** Gera novos títulos (backend salva e retorna a resposta de geração) */
  generate(payload: TitlesRequest): Promise<TitlesResponse> {
    const fullRequest = {
      topic: payload.topic,
      audience: payload.audience,
      tone: payload.tone,
      quantity: payload.quantity,
      // campos esperados no backend
      content_type: "tutorial",
      use_trends: true,
      include_numbers: true,
      include_power_words: true,
      max_length: 60,
    };
    return post<TitlesResponse>("/api/titles/generate", fullRequest);
  },

  /** Lê registros já salvos no banco (paginado) — /history */
  async list(params: ListTitlesParams = {}): Promise<Paginated<TitleRecord>> {
    const query = buildQuery({
      topic: params.topic,
      limit: params.limit,
      offset: params.offset,
      order: params.order,
    });

    // O backend responde: { success, total, limit, offset, history: [...] }
    const data = await get<any>(`/api/titles/history${query}`);
    const items: TitleRecord[] = Array.isArray(data?.history) ? data.history : [];
    const total: number = typeof data?.total === "number" ? data.total : items.length;
    return { items, total };
  },

  /** Lê 1 registro específico (com os títulos) — /history/:id */
  async getById(id: number): Promise<TitleRecord> {
    // Backend pode responder com várias formas:
    // { success, id, titles_generated: [...] }  OU
    // { success, record: { ... , titles_generated: [...] } } OU
    // { success, titles: [...] }
    const data = await get<any>(`/api/titles/history/${id}`);

    const base: TitleRecord =
      data?.record && typeof data.record === "object"
        ? data.record
        : (data as TitleRecord);

    // normaliza para sempre termos titles_generated preenchido
    const titles_generated =
      base?.titles_generated ??
      base?.titles ??
      data?.titles_generated ??
      data?.titles ??
      [];

    return {
      ...base,
      titles_generated,
    };
  },

  /** Endpoints auxiliares (inalterados) */
  analyze(title: string, topic?: string) {
    return post<Record<string, unknown>>("/api/titles/analyze", { title, topic });
  },
  getPowerWords() {
    return get<{ power_words: string[] }>("/api/titles/power-words");
  },
  getTemplates() {
    return get<{ templates: string[] }>("/api/titles/templates");
  },
  getTrendingTopics(category: string = "geral") {
    return get<{ category: string; topics: string[] }>(
      `/api/titles/trending-topics${buildQuery({ category })}`
    );
  },
  getQuickIdeas(topic: string) {
    return get<{ ideas: string[] }>(`/api/titles/title-ideas/${encodeURIComponent(topic)}`);
  },
};
