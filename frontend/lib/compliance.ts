// web/src/lib/compliance.ts
import { post, get } from "@/lib/api"; // 👈 precisa do get também

/** ===== Tipos do contrato ===== */
export interface ComplianceAnalysisRequest {
  content: string;
  context: string;
}

export interface AIAnalysis {
  conformidade_status: "compliant" | "non_compliant" | "partial_compliant" | "unclear";
  confidence_score: number;
  violations: string[];
  legal_articles_cited: string[];
  recommendations: string[];
  risk_level: "low" | "medium" | "high" | "critical";
  summary: string;
  detailed_analysis: string;
}

export interface Performance {
  search_time_seconds: number;
  total_time_seconds: number;
}

export interface ComplianceAnalysisResponse {
  status: "success" | "error";
  analysis_type: string;
  content_analyzed: string;
  context_area: string;
  legal_sources_found: number;
  legal_sources: unknown[];
  ai_analysis: AIAnalysis;
  performance: Performance;
  timestamp: string;
  confidence_score: number;
}

/** ===== Tipos do HISTÓRICO (espelham o backend) ===== */
export interface ComplianceHistoryItem {
  id: string;              // uuid da linha
  request_id: string;      // uuid da requisição
  context_area: string;
  status: string;          // compliant | non_compliant | needs_review...
  risk_level?: string | null;
  confidence_score?: number | null;
  summary?: string | null;
  created_at: string;      // ISO
}

export interface ComplianceHistoryDetail extends ComplianceHistoryItem {
  violations?: unknown[] | null;
  recommendations?: unknown[] | null;
}

/** ===== API ===== */
export const complianceAPI = {
  // Análise REAL (já existia)
  analyzeReal: (payload: ComplianceAnalysisRequest): Promise<ComplianceAnalysisResponse> =>
    post<ComplianceAnalysisResponse>("/api/compliance/analyze-real", payload),

  // LISTAR histórico do usuário
  listMy: (): Promise<ComplianceHistoryItem[]> =>
    get<ComplianceHistoryItem[]>("/api/compliance/history"),

  // DETALHE por id
  getById: (id: string): Promise<ComplianceHistoryDetail> =>
    get<ComplianceHistoryDetail>(`/api/compliance/history/${id}`),
};
