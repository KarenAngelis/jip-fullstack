"use client";

import { useEffect, useMemo, useState } from "react";
import {
  complianceAPI,
  type ComplianceHistoryItem,
  type ComplianceHistoryDetail,
} from "@/lib/compliance";

type Loading = "idle" | "list" | "detail";

export default function HistoryPanel() {
  const [items, setItems] = useState<ComplianceHistoryItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ComplianceHistoryDetail | null>(null);
  const [loading, setLoading] = useState<Loading>("idle");
  const [error, setError] = useState<string | null>(null);

  // carrega lista ao montar
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setLoading("list");
        setError(null);
        const data = await complianceAPI.listMy();
        if (!alive) return;
        setItems(data);
        // seleciona a mais recente
        if (data.length > 0) setSelectedId(data[0].id);
      } catch (err: any) {
        setError(err?.message ?? "Falha ao carregar histórico.");
      } finally {
        setLoading("idle");
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  // carrega detalhe ao trocar o item selecionado
  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let alive = true;
    (async () => {
      try {
        setLoading("detail");
        setError(null);
        const data = await complianceAPI.getById(selectedId);
        if (!alive) return;
        setDetail(data);
      } catch (err: any) {
        setError(err?.message ?? "Falha ao carregar detalhe.");
      } finally {
        setLoading("idle");
      }
    })();
    return () => {
      alive = false;
    };
  }, [selectedId]);

  const hasItems = items.length > 0;

  return (
    <section className="mt-8 grid gap-6 md:grid-cols-2">
      {/* Lista */}
      <div className="rounded-lg border border-white/10 bg-white/5 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-lg font-semibold">Histórico de Compliance</h3>
          {loading === "list" && (
            <span className="text-xs text-white/60">carregando…</span>
          )}
        </div>

        {error && (
          <div className="mb-3 rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm">
            {error}
          </div>
        )}

        {!hasItems && loading === "idle" && (
          <p className="text-sm text-white/60">
            Nenhuma análise encontrada ainda.
          </p>
        )}

        <ul className="divide-y divide-white/10">
          {items.map((it) => (
            <li
              key={it.id}
              className={`cursor-pointer px-2 py-3 transition hover:bg-white/5 ${
                selectedId === it.id ? "bg-white/5" : ""
              }`}
              onClick={() => setSelectedId(it.id)}
              aria-label={`Abrir análise ${it.id}`}
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-medium">
                    {labelStatus(it.status)} · {it.context_area}
                  </div>
                  <div className="text-xs text-white/60">
                    {new Date(it.created_at).toLocaleString()}
                  </div>
                </div>

                <div className="text-right">
                  {it.risk_level && (
                    <span className={`rounded px-2 py-0.5 text-xs ${badge(it.risk_level)}`}>
                      {it.risk_level}
                    </span>
                  )}
                  {it.confidence_score != null && (
                    <div className="mt-1 text-xs text-white/70">
                      Conf.: {(it.confidence_score * 100).toFixed(0)}%
                    </div>
                  )}
                </div>
              </div>

              {it.summary && (
                <p className="mt-2 line-clamp-2 text-xs text-white/70">
                  {it.summary}
                </p>
              )}
            </li>
          ))}
        </ul>
      </div>

      {/* Detalhe */}
      <div className="rounded-lg border border-white/10 bg-white/5 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-lg font-semibold">Detalhe</h3>
          {loading === "detail" && (
            <span className="text-xs text-white/60">carregando…</span>
          )}
        </div>

        {!selectedId && (
          <p className="text-sm text-white/60">
            Selecione uma análise para ver os detalhes.
          </p>
        )}

        {detail && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded bg-white/10 px-2 py-0.5 text-xs">
                {labelStatus(detail.status)}
              </span>
              {detail.risk_level && (
                <span className={`rounded px-2 py-0.5 text-xs ${badge(detail.risk_level)}`}>
                  {detail.risk_level}
                </span>
              )}
              <span className="rounded bg-white/10 px-2 py-0.5 text-xs">
                {new Date(detail.created_at).toLocaleString()}
              </span>
            </div>

            {detail.summary && (
              <div>
                <h4 className="mb-1 text-sm font-semibold">Resumo</h4>
                <p className="text-sm text-white/80">{detail.summary}</p>
              </div>
            )}

            {Array.isArray(detail.violations) && detail.violations.length > 0 && (
              <div>
                <h4 className="mb-1 text-sm font-semibold">Violações</h4>
                <ul className="list-inside list-disc text-sm text-white/80">
                  {detail.violations.map((v, i) => (
                    <li key={i}>{String(v)}</li>
                  ))}
                </ul>
              </div>
            )}

            {Array.isArray(detail.recommendations) &&
              detail.recommendations.length > 0 && (
                <div>
                  <h4 className="mb-1 text-sm font-semibold">Recomendações</h4>
                  <ul className="list-inside list-disc text-sm text-white/80">
                    {detail.recommendations.map((r, i) => (
                      <li key={i}>{String(r)}</li>
                    ))}
                  </ul>
                </div>
              )}
          </div>
        )}
      </div>
    </section>
  );
}

function labelStatus(s: string) {
  if (s === "compliant") return "Compliant";
  if (s === "non_compliant") return "Non Compliant";
  if (s === "needs_review") return "Needs Review";
  return s;
}

function badge(level: string) {
  switch (level) {
    case "low":
      return "bg-emerald-500/15 text-emerald-300";
    case "medium":
      return "bg-amber-500/15 text-amber-300";
    case "high":
      return "bg-rose-500/15 text-rose-300";
    case "critical":
      return "bg-red-600/20 text-red-300";
    default:
      return "bg-white/10 text-white/70";
  }
}
