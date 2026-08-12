// src/lib/roteiros.ts
// Cliente para geração de episódios (roteiro) — endpoint: POST /api/generate

import { post } from "@/lib/api";

export type RiskTolerance = "low" | "medium" | "high";

export interface EpisodeRequest {
  titulo: string;
  tipo_serie: string;
  numero_episodio: number;
  duracao_estimada: number;
  historia_pessoal?: string;
  enable_safety_check?: boolean;
  risk_tolerance?: RiskTolerance;
}

export interface EpisodeOutline {
  introducao: string;
  desenvolvimento: string[];
  conclusao: string;
}

export interface EpisodeBlock {
  titulo: string;
  conteudo: string;
  tempo_estimado?: string;
}

export interface ContentSafetyMeta {
  risk_level: RiskTolerance;
  compliance_score: number;
  has_disclaimers: boolean;
}

export interface EpisodeMetadados {
  tempo_total_estimado?: string;
  principais_ctas?: string[];
  hashtags_sugeridas?: string[];
  pontos_chave?: string[];
  disclaimers?: string[];
  content_safety?: ContentSafetyMeta;
}

export interface SafetyAnalysis {
  risk_level: RiskTolerance;
  compliance_score: number;
  sensitive_topics?: string[];
  disclaimers?: string[];
  improvements?: string[];
  recommendations?: string[];
}

export interface EpisodeRoteiro {
  abertura: string;
  blocos: EpisodeBlock[];
  encerramento: string;
}

export interface EpisodeResponse {
  titulo: string;
  tipo_serie: string;
  numero_episodio: number;
  outline: EpisodeOutline;
  roteiro: EpisodeRoteiro;
  metadados: EpisodeMetadados;
  tempo_geracao?: number;
  safety_analysis?: SafetyAnalysis;
  warnings?: string | null;
}

export const roteirosAPI = {
  generate: (payload: EpisodeRequest) =>
    post<EpisodeResponse, EpisodeRequest>("/api/generate", payload),
};

export default roteirosAPI;
