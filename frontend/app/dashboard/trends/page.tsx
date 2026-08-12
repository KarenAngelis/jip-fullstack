// src/app/dashboard/trends/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useTrends } from "@/hooks/useTrends";
import { Input } from "@/app/components/ui/input";
import { Button } from "@/app/components/ui/button";
import { Card } from "@/app/components/ui/card";

// Se você usa recharts, mantenha. Se não, comento a área do gráfico.
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

export default function TrendsPage() {
  const { search, trend, chart, score, loading, error, topRegions, topRelated } = useTrends();
  const [q, setQ] = useState(""); // termo inicial p/ teste rápido

  // 1º carregamento (opcional)
  useEffect(() => {
    search(q, { timeframe: "today 12-m", geo: "BR", include_opportunities: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await search(q, { timeframe: "today 12-m", geo: "BR", include_opportunities: true });
  };

  const overall: any = trend?.raw?.overall_metrics ?? {};
  const regions = topRegions(8);
  const related = topRelated(10);

  return (
    <div className="p-6 space-y-6 text-white">
      <h1 className="text-2xl font-bold">Tendências</h1>

      {/* Busca */}
      <form onSubmit={onSubmit} className="flex gap-3 max-w-xl">
        <Input
          placeholder="Digite um termo (ex.: coragem)"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="bg-gray-800 border-gray-700"
        />
        <Button disabled={loading.search} className="bg-cyan-600 hover:bg-cyan-500">
          {loading.search ? "Buscando..." : "Buscar"}
        </Button>
      </form>

      {/* Erro (se houver) */}
      {error && <p className="text-red-400">{error}</p>}

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-gray-900/70 border-gray-800">
          <p className="text-gray-400 text-sm">Interesse atual</p>
          <p className="text-2xl font-bold">{overall.current_interest ?? "-"}</p>
        </Card>
        <Card className="p-4 bg-gray-900/70 border-gray-800">
          <p className="text-gray-400 text-sm">Crescimento 12m</p>
          <p className="text-2xl font-bold">
            {overall.growth_rate != null ? `${Math.round(overall.growth_rate)}%` : "-"}
          </p>
        </Card>
        <Card className="p-4 bg-gray-900/70 border-gray-800">
          <p className="text-gray-400 text-sm">Média 12m</p>
          <p className="text-2xl font-bold">
            {overall.average_interest != null ? Math.round(overall.average_interest) : "-"}
          </p>
        </Card>
        <Card className="p-4 bg-gray-900/70 border-gray-800">
          <p className="text-gray-400 text-sm">Score simples</p>
          <p className="text-2xl font-bold">{score ?? "-"}</p>
        </Card>
      </div>

      {/* Gráfico de série */}
      <Card className="p-4 bg-gray-900/70 border-gray-800">
        <p className="text-gray-300 mb-3">Interesse ao longo do tempo</p>
        {chart && chart.labels.length ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={chart.labels.map((label, i) => ({ label, value: chart.values[i] }))}
                margin={{ left: 0, right: 0, top: 10, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="c" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.6}/>
                    <stop offset="95%" stopColor="#22d3ee" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="label" tick={{ fill: "#9CA3AF" }} />
                <YAxis tick={{ fill: "#9CA3AF" }} />
                <Tooltip
                  contentStyle={{ background: "#0f172a", border: "1px solid #1f2937", color: "#fff" }}
                  labelStyle={{ color: "#9CA3AF" }}
                />
                <Area type="monotone" dataKey="value" stroke="#22d3ee" fill="url(#c)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-gray-500">Sem dados para o gráfico.</p>
        )}
      </Card>

      {/* Regiões topo */}
      <Card className="p-4 bg-gray-900/70 border-gray-800">
        <p className="text-gray-300 mb-3">Regiões com maior interesse</p>
        {regions.length ? (
          <ul className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            {regions.map((r) => (
              <li key={r.region} className="flex justify-between bg-gray-800/60 rounded px-3 py-2">
                <span className="text-gray-300">{r.region}</span>
                <span className="text-cyan-400 font-semibold">{r.value}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-500">Sem dados regionais.</p>
        )}
      </Card>

      {/* Relacionados (se backend preencher target_keywords) */}
      <Card className="p-4 bg-gray-900/70 border-gray-800">
        <p className="text-gray-300 mb-3">Palavras-chave relacionadas</p>
        {related.length ? (
          <div className="flex flex-wrap gap-2">
            {related.map((r) => (
              <span key={r.text} className="px-2 py-1 rounded bg-cyan-600/20 border border-cyan-600/30 text-cyan-300 text-sm">
                {r.text} {r.opportunity_score != null && <em className="text-xs opacity-70">({r.opportunity_score})</em>}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">Sem relacionados do backend.</p>
        )}
      </Card>

      {/* Oportunidades (se vierem) */}
      <Card className="p-4 bg-gray-900/70 border-gray-800">
        <p className="text-gray-300 mb-3">Oportunidades</p>
        {trend?.raw?.opportunities?.length ? (
          <ul className="space-y-2">
            {trend.raw.opportunities.map((o: any, i: number) => (
              <li key={i} className="bg-gray-800/60 rounded p-3">
                <p className="font-semibold text-cyan-300">{o.hook || o.topic}</p>
                {o.content_angles?.length ? (
                  <p className="text-gray-400 text-sm mt-1">{o.content_angles[0]}</p>
                ) : null}
                {o.best_channels?.length ? (
                  <p className="text-gray-500 text-xs mt-1">Canais: {o.best_channels.join(", ")}</p>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-500">Sem oportunidades para este termo.</p>
        )}
      </Card>
    </div>
  );
}
