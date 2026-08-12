// web/src/hooks/useCompliance.ts
"use client";
// ------------------------------------------------------------------
// HOOK para orquestrar a chamada de análise de compliance
// - Encapsula loading, error e resultados.
// - Exposto como useCompliance().
// ------------------------------------------------------------------

import { useCallback, useState } from "react";
import {
  complianceAPI,
  type ComplianceAnalysisRequest,
  type ComplianceAnalysisResponse,
} from "@/lib/compliance";

export function useCompliance() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ComplianceAnalysisResponse | null>(null);

  const analyze = useCallback(async (req: ComplianceAnalysisRequest) => {
    setLoading(true);
    setError(null);

    try {
      const data = await complianceAPI.analyzeReal(req);
      
      if (data.status !== "success") {
        throw new Error("Falha na análise de compliance");
      }
      
      setResult(data);
      return { ok: true as const, data };
      
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erro inesperado na análise de compliance.";
      setError(msg);
      setResult(null);
      return { ok: false as const, error: msg };
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    result,
    analyze,
    clear: () => {
      setResult(null);
      setError(null);
    },
    setError,
  };
}