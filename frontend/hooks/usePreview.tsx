// src/hooks/usePreview.ts
import { useState } from 'react';

export function usePreview() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function getPreview(payload: {
    tema: string;
    incluir_dados_tendencia?: boolean;
    duracao_minutos?: number;
    use_gpt_insights?: boolean;
  }) {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/pautas/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || 'Erro no preview');
      return data;
    } catch (e: any) {
      setError(e.message);
      return null;
    } finally {
      setLoading(false);
    }
  }

  return { getPreview, loading, error };
}
