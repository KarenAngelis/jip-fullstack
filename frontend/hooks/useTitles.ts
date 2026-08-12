// web/src/hooks/useTitles.ts
"use client";
// ------------------------------------------------------------------
// HOOK para geração de títulos + leitura do histórico.
// - ENVIO/GRAVAÇÃO: titlesAPI.generate  -> grava no banco.
// - LEITURA LISTA:  useTitleRecords     -> usa titlesAPI.list (rota /api/titles/history)
// - LEITURA DETALHE: titlesAPI.getById  -> usa /api/titles/history/:id
// Mantém a API pública do hook (loading, error, items, lastMeta, generate, clear).
// ------------------------------------------------------------------

import { useCallback, useState } from "react";
import {
  titlesAPI,
  type TitlesRequest,
  type TitlesResponse,
  type TitleItem,
  type TitleRecord,
} from "@/lib/titles";
import { useTitleRecords } from "@/hooks/useTitleRecords";

type DetailEntry = { loading: boolean; data?: TitleRecord; error?: string };

export function useTitles() {
  // ===== estados da GERAÇÃO (API original) =====
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<TitleItem[]>([]);
  const [lastMeta, setLastMeta] =
    useState<Pick<TitlesResponse, "trends_found" | "generation_time"> | null>(
      null
    );

  // ===== HISTÓRICO (LEITURA) =====
  // Lista paginada (usa titlesAPI.list -> /api/titles/history)
  const recordsState = useTitleRecords({ limit: 20, order: "desc" });

  // Cache de detalhes por id (usa titlesAPI.getById -> /api/titles/history/:id)
  const [recordDetails, setRecordDetails] = useState<Record<number, DetailEntry>>(
    {}
  );

  // ========= ENVIO/GRAVAÇÃO =========
  // titlesAPI.generate -> backend grava e devolve os títulos gerados
  const generate = useCallback(
    async (req: TitlesRequest) => {
      setLoading(true);
      setError(null);
      try {
        const data = await titlesAPI.generate(req); // ⬅️ envio/DB (NÃO alterado)
        if (!data.success) {
          setItems([]);
          setLastMeta(null);
          setError("Falha ao gerar títulos.");
          return { ok: false as const, data };
        }

        // mostra o resultado da última geração na UI
        setItems(data.titles || []);
        setLastMeta({
          trends_found: data.trends_found,
          generation_time: data.generation_time,
        });

        // depois de gravar, atualiza a lista do histórico (leitura)
        recordsState.setTopic?.(req.topic);
        recordsState.refresh();

        return { ok: true as const, data };
      } catch (e: unknown) {
        const msg =
          e instanceof Error ? e.message : "Erro inesperado ao gerar títulos.";
        setError(msg);
        setItems([]);
        setLastMeta(null);
        return { ok: false as const, error: msg };
      } finally {
        setLoading(false);
      }
    },
    [recordsState]
  );

  // ========= LEITURA (DETALHE) =========
  // Carrega os títulos gerados de UMA pesquisa (por id)
  const viewRecord = useCallback(async (id: number) => {
    setRecordDetails((m) => ({ ...m, [id]: { loading: true } }));
    try {
      const data = await titlesAPI.getById(id); // ⬅️ leitura/DETALHE
      setRecordDetails((m) => ({ ...m, [id]: { loading: false, data } }));
      return { ok: true as const, data };
    } catch (e) {
      const msg =
        e instanceof Error ? e.message : "Falha ao carregar os detalhes.";
      setRecordDetails((m) => ({ ...m, [id]: { loading: false, error: msg } }));
      return { ok: false as const, error: msg };
    }
  }, []);

  // ========= API pública do hook =========
  return {
    // ===== geração (inalterada) =====
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

    // ===== histórico - lista =====
    records: recordsState.records,
    total: recordsState.total,
    listLoading: recordsState.loading,
    listError: recordsState.error,
    listQuery: recordsState.query,
    refreshList: recordsState.refresh,
    setListQuery: recordsState.setQuery,
    setTopic: recordsState.setTopic,
    setLimit: recordsState.setLimit,
    pagination: recordsState.pagination,

    // ===== histórico - detalhe =====
    recordDetails, // { [id]: { loading, data?, error? } }
    viewRecord,
  };
}
