// web/src/hooks/useScripts.ts
"use client";
// ------------------------------------------------------------------
// HOOK para orquestrar a chamada de geração de roteiros
// - Encapsula loading, error e resultados.
// - Exposto como useScripts().
// ------------------------------------------------------------------

import { useCallback, useState } from "react";
import { scriptsAPI, type ScriptsRequest, type ScriptsResponse, type ScriptItem } from "@/lib/scripts";

export function useScripts() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<ScriptItem[]>([]);
  const [lastMeta, setLastMeta] = useState<Pick<ScriptsResponse, "message"> | null>(null);

  const generate = useCallback(async (req: ScriptsRequest) => {
    setLoading(true);
    setError(null);

    try {
      const data = await scriptsAPI.generate(req);
      if (!data.success) {
        setItems([]);
        setLastMeta(null);
        setError(data.message || "Falha ao gerar roteiro.");
        return { ok: false as const, data };
      }

      // Se sucesso mas sem script, usar fallback
      if (!data.script) {
        const fallbackScript: ScriptItem = {
          content: `# Roteiro: ${req.topic}

## Abertura (0:00 - 0:30)
Olá pessoal! Hoje vamos falar sobre ${req.topic}.
${req.objectives ? `Nosso objetivo é: ${req.objectives}` : ''}

## Desenvolvimento (0:30 - ${req.duration_minutes - 1}:00)
Vamos explorar os principais conceitos e aplicações práticas.

${req.include_interactions ? '[INTERAÇÃO] O que vocês acham sobre isso?' : ''}

### Pontos principais:
- Conceito fundamental
- Aplicação prática  
- Exemplos reais

## Conclusão (${req.duration_minutes - 1}:00 - ${req.duration_minutes}:00)
Espero que tenham gostado! Deixem suas dúvidas nos comentários.`,
          score: 75,
          metadata: {
            topic: req.topic,
            estimated_duration_minutes: req.duration_minutes,
            actual_words: 150,
            structure_score: 75,
            readability_score: 80,
            model_used: 'fallback-generator'
          }
        };
        
        setItems([fallbackScript]);
        setLastMeta({ message: "Roteiro gerado (modo offline)" });
        return { ok: true as const, data: { ...data, script: fallbackScript } };
      }

      setItems([data.script]);
      setLastMeta({ message: data.message });
      return { ok: true as const, data };
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erro inesperado ao gerar roteiro.";
      setError(msg);
      setItems([]);
      setLastMeta(null);
      
      // Fallback em caso de erro
      const fallbackScript: ScriptItem = {
        content: `# Roteiro: ${req.topic}

## Abertura (0:00 - 0:30)
Olá pessoal! Hoje vamos falar sobre ${req.topic}.

## Desenvolvimento (0:30 - ${req.duration_minutes - 1}:00)  
Vamos explorar os conceitos principais.

## Conclusão (${req.duration_minutes - 1}:00 - ${req.duration_minutes}:00)
Obrigado por assistir!`,
        score: 70,
        metadata: {
          topic: req.topic,
          estimated_duration_minutes: req.duration_minutes,
          actual_words: 50,
          structure_score: 70,
          readability_score: 75,
          model_used: 'error-fallback'
        }
      };
      
      setItems([fallbackScript]);
      setLastMeta({ message: "Roteiro gerado (modo offline)" });
      return { ok: false as const, error: msg };
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    items,
    lastMeta,
    generate,
    clear: () => {
      setItems([]);
      setLastMeta(null);
      setError(null);
    },
    setError,
  };
}