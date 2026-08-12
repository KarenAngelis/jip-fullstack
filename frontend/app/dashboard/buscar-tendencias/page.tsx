"use client";

import React, { useMemo, useState } from "react";
import { BarChart2, Search, TrendingUp, Globe, Activity } from "lucide-react";

/* =========================================================
   Tipos do payload e da resposta da sua API de Tendências
   (compatíveis com os exemplos do seu Swagger)
   ========================================================= */
type TrendsSearchPayload = {
  keywords: string[];   // ["inteligência artificial", "enem 2025"]
  timeframe?: string;   // "today 12-m"
  geo?: string;         // "BR"
  category?: number;    // 0
};

type InterestPoint = {
  date: string;
  timestamp: number;
  // valores por palavra-chave, p.ex. "inteligência artificial": 49
  // como as chaves são dinâmicas, representamos com índice:
  [keyword: string]: string | number;
};

type RelatedQuery = {
  query: string;
  value: number;
  type: "top" | "rising";
};

type GeoRow = {
  region: string;
  // idem: valores por palavra-chave
  [keyword: string]: number | string;
};

type TrendsResponse = {
  keyword: string;
  interest_over_time: InterestPoint[];
  related_topics: unknown[];   // (se precisar depois)
  related_queries: RelatedQuery[];
  geographical_data: GeoRow[];
  category: number | null;
  timeframe: string;
};

/* ===================================
   Config básica (env + utilitário)
   =================================== */
const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

/** Utilitário: retorna as chaves de keywords presentes no primeiro item.
 *  Ex.: ["inteligência artificial", "enem 2025"]
 */
function extractKeywordKeys(arr: InterestPoint[] | GeoRow[]): string[] {
  if (!arr?.length) return [];
  const set = new Set<string>();
  const first = arr[0];
  Object.keys(first).forEach((k) => {
    if (!["date", "timestamp", "region"].includes(k)) {
      set.add(k);
    }
  });
  return [...set];
}

/* ===================================
   Painel de Tendências (com a sua API)
   =================================== */
function TrendsPanel({
  result,
}: {
  result: TrendsResponse | null;
}) {
  if (!result) {
    return (
      <p className="text-gray-400">
        Faça uma busca para ver tendências (Google Trends) do(s) termo(s) informado(s).
      </p>
    );
  }

  // Quais keywords existem nas séries e nos dados geográficos?
  const seriesKeywordKeys = useMemo(
    () => extractKeywordKeys(result.interest_over_time),
    [result]
  );
  const geoKeywordKeys = useMemo(
    () => extractKeywordKeys(result.geographical_data),
    [result]
  );

  return (
    <div className="space-y-8">
      {/* Série temporal (lista simples) */}
      <section>
        <h3 className="flex items-center gap-2 text-lg font-semibold mb-3">
          <Activity className="w-5 h-5 text-cyan-400" />
          Interesse ao longo do tempo
        </h3>

        {result.interest_over_time.length === 0 ? (
          <p className="text-gray-500">Sem dados no período selecionado.</p>
        ) : (
          <div className="grid md:grid-cols-2 gap-3">
            {result.interest_over_time.map((p) => (
              <div
                key={p.timestamp}
                className="rounded-lg border border-gray-700 bg-gray-800 p-4"
              >
                <p className="text-sm text-gray-400">{p.date}</p>
                <ul className="text-sm mt-2 space-y-1">
                  {seriesKeywordKeys.map((k) => (
                    <li key={`${p.timestamp}-${k}`}>
                      <span className="text-gray-300">{k}:</span>{" "}
                      <span className="text-gray-100 font-medium">{String(p[k] ?? 0)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Related Queries */}
      <section>
        <h3 className="flex items-center gap-2 text-lg font-semibold mb-3">
          <TrendingUp className="w-5 h-5 text-cyan-400" />
          Buscas relacionadas
        </h3>

        {result.related_queries.length === 0 ? (
          <p className="text-gray-500">Nenhuma consulta relacionada retornada.</p>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {/* TOP */}
            <div className="rounded-lg border border-gray-700 bg-gray-800 p-4">
              <h4 className="font-semibold mb-2">Top</h4>
              <ul className="space-y-2">
                {result.related_queries
                  .filter((q) => q.type === "top")
                  .map((q) => (
                    <li key={`top-${q.query}`} className="flex justify-between text-sm">
                      <span className="text-gray-200">{q.query}</span>
                      <span className="text-gray-400">{q.value}</span>
                    </li>
                  ))}
              </ul>
            </div>

            {/* RISING */}
            <div className="rounded-lg border border-gray-700 bg-gray-800 p-4">
              <h4 className="font-semibold mb-2">Rising</h4>
              <ul className="space-y-2">
                {result.related_queries
                  .filter((q) => q.type === "rising")
                  .map((q) => (
                    <li key={`rising-${q.query}`} className="flex justify-between text-sm">
                      <span className="text-gray-200">{q.query}</span>
                      <span className="text-gray-400">{q.value}</span>
                    </li>
                  ))}
              </ul>
            </div>
          </div>
        )}
      </section>

      {/* Dados geográficos */}
      <section>
        <h3 className="flex items-center gap-2 text-lg font-semibold mb-3">
          <Globe className="w-5 h-5 text-cyan-400" />
          Distribuição geográfica
        </h3>

        {result.geographical_data.length === 0 ? (
          <p className="text-gray-500">Sem dados geográficos retornados.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-700">
            <table className="min-w-[560px] w-full bg-gray-800 text-sm">
              <thead className="bg-gray-700/60">
                <tr>
                  <th className="text-left p-3">Região</th>
                  {geoKeywordKeys.map((k) => (
                    <th key={`head-${k}`} className="text-right p-3">{k}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.geographical_data.map((row) => (
                  <tr key={row.region} className="border-t border-gray-700/50">
                    <td className="p-3">{row.region}</td>
                    {geoKeywordKeys.map((k) => (
                      <td key={`${row.region}-${k}`} className="p-3 text-right">
                        {String(row[k] ?? 0)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

/* ===================================
   Página do Dashboard com Abas
   (apenas a aba "Tendências" chama a API)
   =================================== */
type Tab = "trends" | "search" | "youtube" | "news" | "competitors";

export default function DashboardBuscarTendenciasPage() {
  const [tab, setTab] = useState<Tab>("trends");

  // Formulário comum para as buscas
  const [keywordsInput, setKeywordsInput] = useState("inteligência artificial, enem 2025");
  const [timeframe, setTimeframe] = useState("today 12-m");
  const [geo, setGeo] = useState("BR");

  // Estados de execução
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Resultado somente da aba Tendências
  const [trendsResult, setTrendsResult] = useState<TrendsResponse | null>(null);

  // Chama SOMENTE a API de tendências quando a aba selecionada for "trends"
  async function handleSearch() {
    setError(null);

    if (!API_BASE) {
      setError("API não configurada. Defina NEXT_PUBLIC_API_URL no .env.local");
      return;
    }
    const keywords = keywordsInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    if (keywords.length === 0) {
      setError("Informe pelo menos um termo (separe por vírgula).");
      return;
    }

    setLoading(true);

    try {
      if (tab === "trends") {
        const payload: TrendsSearchPayload = {
          keywords,
          timeframe,
          geo,
          category: 0,
        };

        const resp = await fetch(`${API_BASE}/api/trends/search`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify(payload),
        });

        if (!resp.ok) {
          const txt = await resp.text();
          throw new Error(`Falha ao carregar tendências (${resp.status}): ${txt}`);
        }

        const data: TrendsResponse = await resp.json();
        setTrendsResult(data);
      } else {
        // Stubs para as outras abas — aqui você pluga seus outros endpoints:
        // - search:     `${API_BASE}/api/search/analyze`
        // - youtube:    `${API_BASE}/api/youtube/trends`
        // - news:       `${API_BASE}/api/news/search`
        // - competitors:`${API_BASE}/api/competitors/overview`
        // Por enquanto, só informamos que a integração ainda não foi feita:
        throw new Error("A integração desta aba ainda não foi conectada à API. (Somente Tendências está ativa)");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado ao consultar a API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Título e descrição */}
      <header className="max-w-6xl mx-auto mb-6">
        <h1 className="text-2xl font-bold">Pesquisa & Insights</h1>
        <p className="text-gray-400">
          Descubra tendências, analise tópicos e encontre oportunidades de conteúdo.
        </p>
      </header>

      {/* Form de busca (comum para todas as abas) */}
      <section className="max-w-6xl mx-auto bg-gray-800/60 border border-gray-700 rounded-xl p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="flex-1">
            <label className="block text-sm text-gray-300 mb-1">Termos (separe por vírgula)</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                value={keywordsInput}
                onChange={(e) => setKeywordsInput(e.target.value)}
                placeholder="Ex.: Enem 2025, IA Generativa"
                className="w-full pl-10 pr-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-gray-100 placeholder-gray-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1">Período</label>
            <input
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="w-40 py-2 px-3 rounded-lg bg-gray-900 border border-gray-700"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1">Geo</label>
            <input
              value={geo}
              onChange={(e) => setGeo(e.target.value)}
              className="w-24 py-2 px-3 rounded-lg bg-gray-900 border border-gray-700"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={handleSearch}
              disabled={loading}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 transition-colors font-semibold px-5 py-2 rounded-lg"
            >
              <BarChart2 className="w-4 h-4" />
              {loading ? "Buscando..." : "Pesquisar"}
            </button>
          </div>
        </div>
        {error && <p className="text-red-400 text-sm mt-3">{error}</p>}
      </section>

      {/* Abas */}
      <nav className="max-w-6xl mx-auto mb-4">
        <ul className="flex flex-wrap gap-2">
          {([
            { key: "trends", label: "Tendências", icon: BarChart2 },
            { key: "search", label: "Análise de Busca", icon: Search },
            { key: "youtube", label: "YouTube Trends", icon: TrendingUp },
            { key: "news", label: "Notícias & Insights", icon: Activity },
            { key: "competitors", label: "Concorrentes", icon: Globe },
          ] as { key: Tab; label: string; icon: React.ComponentType<any> }[]).map(
            ({ key, label, icon: Icon }) => (
              <li key={label}>
                <button
                  onClick={() => setTab(key)}
                  className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border ${
                    tab === key
                      ? "bg-cyan-500/20 border-cyan-400 text-cyan-300"
                      : "bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              </li>
            )
          )}
        </ul>
      </nav>

      {/* Conteúdo da aba */}
      <main className="max-w-6xl mx-auto">
        {tab === "trends" && <TrendsPanel result={trendsResult} />}

        {tab !== "trends" && (
          <div className="rounded-xl border border-gray-700 bg-gray-800/60 p-6">
            <h3 className="text-lg font-semibold mb-2">
              {tab === "search" && "Análise de Busca"}
              {tab === "youtube" && "YouTube Trends"}
              {tab === "news" && "Notícias & Insights"}
              {tab === "competitors" && "Concorrentes"}
            </h3>
            <p className="text-gray-400">
              Esta aba ainda não está conectada à API. Assim que seus endpoints estiverem prontos,
              plugamos aqui (o botão “Pesquisar” já envia o mesmo formulário).
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
