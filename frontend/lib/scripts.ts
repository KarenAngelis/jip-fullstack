// web/src/lib/scripts.ts
// ------------------------------------------------------------------
// SDK de "geração de roteiros"
// - Usa os helpers get/post de "@/lib/api" (já com auth/interceptors).
// - Alinhado ao endpoint: POST /api/scripts/generate-script
// - Tipos coerentes com o contrato do backend que você mostrou.
// ------------------------------------------------------------------

import { post } from "@/lib/api";

/** ===== Tipos do contrato ===== */
export type ScriptStyle =
  | "educativo"
  | "inspirador"
  | "casual"
  | "profissional"
  | "divertido"
  | "motivacional"
  | "provocativo"

export type TargetAudience =
  | "geral"
  | "iniciantes"
  | "intermediário"
  | "avançado"
  | "todos_os_niveis"

export interface ScriptsRequest {
  topic: string;
  duration_minutes: number;
  objectives?: string;           // pode mandar "" se não tiver objetivos
  target_audience: TargetAudience;
  script_style: ScriptStyle;
  include_interactions: boolean;
}

export interface ScriptMetadata {
  topic: string;
  target_duration_minutes: number;
  estimated_duration_minutes: number;
  target_words: number;
  actual_words: number;
  word_accuracy: number;
  structure_score: number;
  sections_found: number;
  has_timestamps: boolean;
  has_interactions: boolean;
  readability_score: number;
  model_used: string;
  generation_timestamp: number;
}

export interface ScriptItem {
  content: string;
  score: number;
  metadata: ScriptMetadata;
}

export interface ScriptsResponse {
  success: boolean;
  message: string;
  script?: ScriptItem;
}

/** ===== API ===== */
export const scriptsAPI = {
  /**
   * Gera roteiro.
   * Backend: POST /api/scripts/generate-script
   */
  generate: (payload: ScriptsRequest) =>
    post<ScriptsResponse, ScriptsRequest>("/api/scripts/generate-script", payload),
};

export default scriptsAPI;
