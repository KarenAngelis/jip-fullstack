"use client";

import React, { useState, useEffect } from "react";
import {
  FileText,
  Clock,
  TrendingUp,
  Search,
  ExternalLink,
  CheckCircle,
  BarChart3,
  Target,
  Lightbulb,
  MessageCircle,
  Trash2,
  Edit,
  Plus,
  Calendar,
  Archive,
  Filter,
} from "lucide-react";
import Cookies from "js-cookie";

// Tipos (mesmo do componente anterior)
interface ArtigoRef {
  titulo: string;
  fonte: string;
  data: string;
  url: string;
  resumo: string;
  confiabilidade: string;
}

interface TrendsDetalhadas {
  keywords: string[];
  volume_busca_mensal: number;
  crescimento_30_dias: string;
  tendencia: string;
  popularidade_score: number;
  pico_interesse: string;
  previsao_proximo_mes: string;
  interesse_regional: Record<string, number>;
}

interface DeepResearch {
  validacao: string[];
}

interface RoteiroEstruturado {
  abertura: string;
  bloco_1: string;
  bloco_2: string;
  bloco_3: string;
  bloco_4: string;
  conclusao: string;
}

interface PautaResponse {
  id?: number;
  tema: string;
  duracao_min: number;
  resumo_executivo: string[];
  titulos_sugeridos: string[];
  perguntas_sugeridas: string[];
  artigos_referencia: ArtigoRef[];
  trends_detalhadas: TrendsDetalhadas;
  deep_research: DeepResearch;
  roteiro_estruturado: RoteiroEstruturado;
  status: string;
}

interface PautaListItem {
  id: number;
  tema: string;
  duracao_min: number;
  status: string;
  popularidade_score: number;
  tendencia: string;
  created_at: string;
}

// ===== Helpers de Auth para fetch =====
function getToken(): string | undefined {
  const cookie = Cookies.get("access_token");
  if (cookie) return cookie;
  if (typeof window !== "undefined") {
    return localStorage.getItem("access_token") ?? undefined;
  }
  return undefined;
}

function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = getToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(extra || {}),
  };
}

const PautasDashboard = () => {
  const [modo, setModo] = useState<"create" | "list">("list");
  const [tema, setTema] = useState("");
  const [duracao, setDuracao] = useState(15);
  const [isLoading, setIsLoading] = useState(false);
  const [resultado, setResultado] = useState<PautaResponse | null>(null);
  const [pautas, setPautas] = useState<PautaListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "content" | "research">(
    "overview"
  );
  const [filtroTema, setFiltroTema] = useState("");
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [totalPautas, setTotalPautas] = useState(0);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Carregar lista de pautas
  useEffect(() => {
    if (modo === "list") {
      loadPautas();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modo, paginaAtual, filtroTema]);

  const loadPautas = async () => {
    try {
      setError(null);

      const params = new URLSearchParams({
        page: paginaAtual.toString(),
        limit: "10",
        status: "ativo",
      });
      if (filtroTema) params.append("tema", filtroTema);

      const response = await fetch(`${API_BASE}/api/pautas?${params.toString()}`, {
        headers: authHeaders(),
        cache: "no-store",
      });

      if (response.ok) {
        const data = await response.json();
        setPautas(Array.isArray(data.pautas) ? data.pautas : []);
        setTotalPautas(Number(data.total ?? 0));
      } else if (response.status === 401) {
        setPautas([]);
        setTotalPautas(0);
        setError("Não autenticado. Faça login novamente.");
      } else {
        setError(`Erro ao carregar pautas. [${response.status}]`);
      }
    } catch (err) {
      console.error("Erro ao carregar pautas:", err);
      setError("Erro ao carregar pautas.");
    }
  };

  const handleGenerate = async () => {
    if (!tema.trim()) {
      setError("Digite um tema para continuar");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/pautas/generate`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          tema: tema.trim(),
          duracao_desejada: duracao,
        }),
      });

      if (!response.ok) {
        if (response.status === 401) throw new Error("401");
        throw new Error(`Erro ${response.status}`);
      }

      const data: PautaResponse = await response.json();
      setResultado(data);
      setActiveTab("overview");

      if (modo === "list") {
        await loadPautas();
      }
    } catch (err) {
      setError(
        (err as Error)?.message === "401"
          ? "Sessão expirada. Faça login novamente."
          : "Erro ao gerar pauta. Verifique a conexão."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Tem certeza que deseja excluir esta pauta?")) return;

    try {
      const response = await fetch(`${API_BASE}/api/pautas/${id}`, {
        method: "DELETE",
        headers: authHeaders(),
      });

      if (response.ok) {
        await loadPautas();
      } else if (response.status === 401) {
        setError("Sessão expirada. Faça login novamente.");
      } else if (response.status === 404) {
        setError("Endpoint de exclusão não encontrado no backend.");
      } else {
        setError("Erro ao excluir pauta.");
      }
    } catch (err) {
      setError("Erro ao excluir pauta.");
    }
  };

  const handleView = async (id: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/pautas/${id}`, {
        headers: authHeaders(),
        cache: "no-store",
      });
      if (response.ok) {
        const data = await response.json();
        setResultado(data);
        setModo("create");
        setActiveTab("overview");
      } else if (response.status === 401) {
        setError("Sessão expirada. Faça login novamente.");
      } else {
        setError("Erro ao carregar pauta.");
      }
    } catch (err) {
      setError("Erro ao carregar pauta.");
    }
  };

  const getTendenciaColor = (tend: string) => {
    switch (tend?.toLowerCase()) {
      case "crescendo":
        return "text-green-400";
      case "estável":
        return "text-blue-400";
      case "declinando":
        return "text-red-400";
      default:
        return "text-gray-400";
    }
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return Number.isNaN(d.getTime()) ? "-" : d.toLocaleDateString("pt-BR");
    };

  // Componente para lista de pautas
  const PautasList = () => (
    <div className="space-y-6">
      {/* Header da Lista */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">Minhas Pautas</h2>
          <p className="text-gray-400">Gerencie suas pautas salvas</p>
        </div>
        <button
          onClick={() => setModo("create")}
          className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Nova Pauta
        </button>
      </div>

      {/* Filtros */}
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex gap-4">
          <input
            type="text"
            placeholder="Filtrar por tema..."
            value={filtroTema}
            onChange={(e) => setFiltroTema(e.target.value)}
            className="flex-1 p-3 bg-gray-700 border border-gray-600 rounded-lg text-white"
          />
          <button
            onClick={loadPautas}
            className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <Filter className="w-4 h-4" />
            Filtrar
          </button>
        </div>
      </div>

      {/* Lista */}
      <div className="grid gap-4">
        {pautas.map((pauta) => (
          <div
            key={pauta.id}
            className="bg-gray-800 rounded-lg p-6 hover:bg-gray-750 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-white mb-2">
                  {pauta.tema}
                </h3>
                <div className="flex items-center gap-4 text-sm text-gray-400 mb-3">
                  <span className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    {pauta.duracao_min} min
                  </span>
                  <span className="flex items-center gap-1">
                    <BarChart3 className="w-4 h-4" />
                    {pauta.popularidade_score}/100
                  </span>
                  <span
                    className={`flex items-center gap-1 ${getTendenciaColor(
                      pauta.tendencia
                    )}`}
                  >
                    <TrendingUp className="w-4 h-4" />
                    {pauta.tendencia}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    {formatDate(pauta.created_at)}
                  </span>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleView(pauta.id)}
                  className="p-2 text-blue-400 hover:bg-blue-400/10 rounded"
                  title="Visualizar"
                >
                  <ExternalLink className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDelete(pauta.id)}
                  className="p-2 text-red-400 hover:bg-red-400/10 rounded"
                  title="Excluir"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Paginação */}
      {totalPautas > 10 && (
        <div className="flex justify-center items-center gap-4">
          <button
            onClick={() => setPaginaAtual(Math.max(1, paginaAtual - 1))}
            disabled={paginaAtual === 1}
            className="px-4 py-2 bg-gray-700 text-white rounded disabled:opacity-50"
          >
            Anterior
          </button>
          <span className="text-gray-400">
            Página {paginaAtual} de {Math.ceil(totalPautas / 10)}
          </span>
          <button
            onClick={() => setPaginaAtual(paginaAtual + 1)}
            disabled={paginaAtual >= Math.ceil(totalPautas / 10)}
            className="px-4 py-2 bg-gray-700 text-white rounded disabled:opacity-50"
          >
            Próxima
          </button>
        </div>
      )}
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Toggle entre modos */}
        <div className="mb-8 flex justify-center">
          <div className="bg-gray-800 rounded-lg p-1 flex">
            <button
              onClick={() => setModo("list")}
              className={`px-4 py-2 rounded-md transition-colors ${
                modo === "list"
                  ? "bg-cyan-600 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <Archive className="w-4 h-4 inline mr-2" />
              Minhas Pautas
            </button>
            <button
              onClick={() => setModo("create")}
              className={`px-4 py-2 rounded-md transition-colors ${
                modo === "create"
                  ? "bg-cyan-600 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <Plus className="w-4 h-4 inline mr-2" />
              Criar Nova
            </button>
          </div>
        </div>

        {/* Conteúdo baseado no modo */}
        {modo === "list" ? (
          <PautasList />
        ) : (
          <div>
            {/* Header da criação */}
            <div className="text-center mb-8">
              <h1 className="text-3xl font-bold mb-2 flex items-center justify-center gap-3">
                <FileText className="text-cyan-500" />
                {resultado ? "Visualizar Pauta" : "Gerador de Pautas IA"}
              </h1>
              <p className="text-gray-400">
                {resultado
                  ? "Pauta gerada e salva no banco de dados"
                  : "Crie episódios de podcast inteligentes"}
              </p>
            </div>

            {/* Form */}
            {!resultado && (
              <div className="bg-gray-800 p-6 rounded-lg shadow-xl mb-8">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium mb-2 text-gray-300">
                      Tema
                    </label>
                    <input
                      type="text"
                      value={tema}
                      onChange={(e) => setTema(e.target.value)}
                      placeholder="Ex: ENEM 2025, inteligência artificial..."
                      className="w-full p-3 rounded-lg bg-gray-700 border border-gray-600 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                      onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2 text-gray-300">
                      Duração
                    </label>
                    <select
                      value={duracao}
                      onChange={(e) => setDuracao(Number(e.target.value))}
                      className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-cyan-500 text-white"
                    >
                      <option value={5}>5 min</option>
                      <option value={10}>10 min</option>
                      <option value={15}>15 min</option>
                      <option value={20}>20 min</option>
                      <option value={30}>30 min</option>
                      <option value={45}>45 min</option>
                      <option value={60}>60 min</option>
                    </select>
                  </div>
                  <div className="flex items-end">
                    <button
                      onClick={handleGenerate}
                      disabled={isLoading}
                      className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {isLoading ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          Gerando...
                        </>
                      ) : (
                        <>
                          <Plus className="w-4 h-4" />
                          Gerar e Salvar
                        </>
                      )}
                    </button>
                  </div>
                </div>
                <p className="text-sm text-gray-500 text-center">
                  A pauta será gerada e automaticamente salva no banco de dados
                </p>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 mb-8 text-center">
                <p className="text-red-200">{error}</p>
              </div>
            )}

            {/* Loading */}
            {isLoading && (
              <div className="text-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500 mx-auto mb-4"></div>
                <p className="text-gray-400">JIP analisando e salvando...</p>
              </div>
            )}

            {/* Results */}
            {resultado && !isLoading && (
              <div className="space-y-6">
                {/* Quick Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gray-800 rounded-lg p-4 text-center">
                    <Clock className="w-6 h-6 text-blue-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold">{resultado.duracao_min}</p>
                    <p className="text-sm text-gray-400">minutos</p>
                  </div>

                  <div className="bg-gray-800 rounded-lg p-4 text-center">
                    <BarChart3 className="w-6 h-6 text-green-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold">
                      {resultado.trends_detalhadas.volume_busca_mensal.toLocaleString()}
                    </p>
                    <p className="text-sm text-gray-400">buscas/mês</p>
                  </div>

                  <div className="bg-gray-800 rounded-lg p-4 text-center">
                    <TrendingUp className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold">
                      {resultado.trends_detalhadas.crescimento_30_dias}
                    </p>
                    <p className="text-sm text-gray-400">crescimento</p>
                  </div>

                  <div className="bg-gray-800 rounded-lg p-4 text-center">
                    <FileText className="w-6 h-6 text-cyan-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold">
                      {resultado.artigos_referencia.length}
                    </p>
                    <p className="text-sm text-gray-400">fontes</p>
                  </div>
                </div>

                {/* Tabs */}
                <div className="bg-gray-800 rounded-lg">
                  <div className="flex border-b border-gray-700">
                    <button
                      onClick={() => setActiveTab("overview")}
                      className={`px-6 py-3 font-medium rounded-tl-lg transition-colors ${
                        activeTab === "overview"
                          ? "bg-cyan-600 text-white"
                          : "text-gray-400 hover:text-white hover:bg-gray-700"
                      }`}
                    >
                      <Target className="w-4 h-4 inline mr-2" />
                      Visão Geral
                    </button>
                    <button
                      onClick={() => setActiveTab("content")}
                      className={`px-6 py-3 font-medium transition-colors ${
                        activeTab === "content"
                          ? "bg-cyan-600 text-white"
                          : "text-gray-400 hover:text-white hover:bg-gray-700"
                      }`}
                    >
                      <MessageCircle className="w-4 h-4 inline mr-2" />
                      Conteúdo
                    </button>
                    <button
                      onClick={() => setActiveTab("research")}
                      className={`px-6 py-3 font-medium rounded-tr-lg transition-colors ${
                        activeTab === "research"
                          ? "bg-cyan-600 text-white"
                          : "text-gray-400 hover:text-white hover:bg-gray-700"
                      }`}
                    >
                      <Search className="w-4 h-4 inline mr-2" />
                      Pesquisa
                    </button>
                  </div>

                  <div className="p-6">
                    {/* Overview Tab */}
                    {activeTab === "overview" && (
                      <div className="space-y-6">
                        {/* Resumo Executivo */}
                        <div className="bg-gray-700 rounded-lg p-6">
                          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                            <Target className="text-blue-400" />
                            Resumo Executivo
                          </h3>
                          <div className="space-y-3">
                            {resultado.resumo_executivo.map((item, index) => (
                              <p key={index} className="text-gray-300 leading-relaxed">
                                {item}
                              </p>
                            ))}
                          </div>
                        </div>

                        {/* Keywords */}
                        <div className="bg-gray-700 rounded-lg p-6">
                          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                            <TrendingUp className="text-green-400" />
                            Palavras-chave em Alta
                          </h3>
                          <div className="flex flex-wrap gap-2">
                            {resultado.trends_detalhadas.keywords
                              .slice(0, 8)
                              .map((keyword, index) => (
                                <span
                                  key={index}
                                  className="bg-cyan-600/20 text-cyan-300 px-3 py-1 rounded-full text-sm border border-cyan-600/30"
                                >
                                  {keyword}
                                </span>
                              ))}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Content Tab */}
                    {activeTab === "content" && (
                      <div className="space-y-6">
                        {/* Títulos e Perguntas */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                          <div className="bg-gray-700 rounded-lg p-6">
                            <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                              <Lightbulb className="text-yellow-400" />
                              Títulos Sugeridos
                            </h3>
                            <div className="space-y-3">
                              {resultado.titulos_sugeridos
                                .slice(0, 4)
                                .map((titulo, index) => (
                                  <div
                                    key={index}
                                    className="bg-gray-600 rounded p-3 hover:bg-gray-500 transition-colors"
                                  >
                                    <p className="text-gray-200">
                                      {titulo.replace(/^[-\d\.\s]+/, "").trim()}
                                    </p>
                                  </div>
                                ))}
                            </div>
                          </div>

                          <div className="bg-gray-700 rounded-lg p-6">
                            <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                              <MessageCircle className="text-blue-400" />
                              Perguntas-Chave
                            </h3>
                            <div className="space-y-3">
                              {resultado.perguntas_sugeridas
                                .slice(0, 4)
                                .map((pergunta, index) => (
                                  <div key={index} className="bg-gray-600 rounded p-3">
                                    <p className="text-gray-200">
                                      {pergunta.replace(/^[-\d\.\s]+/, "").trim()}
                                    </p>
                                  </div>
                                ))}
                            </div>
                          </div>
                        </div>

                        {/* Roteiro */}
                        <div className="bg-gray-700 rounded-lg p-6">
                          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                            <FileText className="text-purple-400" />
                            Estrutura do Roteiro
                          </h3>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {Object.entries(resultado.roteiro_estruturado).map(
                              ([bloco, conteudo]) => (
                                <div key={bloco} className="bg-gray-600 rounded-lg p-4">
                                  <h4 className="font-medium text-cyan-300 mb-2 capitalize">
                                    {bloco.replace("_", " ")}
                                  </h4>
                                  <p className="text-gray-300 text-sm">
                                    {conteudo.replace(/^"|"$/g, "").trim()}
                                  </p>
                                </div>
                              )
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Research Tab */}
                    {activeTab === "research" && (
                      <div className="space-y-6">
                        {/* Artigos */}
                        <div className="bg-gray-700 rounded-lg p-6">
                          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                            <ExternalLink className="text-green-400" />
                            Fontes de Referência
                          </h3>
                          <div className="space-y-4">
                            {resultado.artigos_referencia.map((artigo, index) => (
                              <div key={index} className="bg-gray-600 rounded-lg p-4">
                                <div className="flex items-start justify-between mb-2">
                                  <h4 className="font-medium text-white pr-4">
                                    {artigo.titulo}
                                  </h4>
                                  <span className="text-xs px-2 py-1 rounded bg-gray-800 text-yellow-400">
                                    {artigo.confiabilidade}
                                  </span>
                                </div>
                                <p className="text-gray-300 text-sm mb-3">{artigo.resumo}</p>
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-4 text-xs text-gray-400">
                                    <span>{artigo.fonte}</span>
                                    <span>{artigo.data}</span>
                                  </div>
                                  <a
                                    href={artigo.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-cyan-400 hover:text-cyan-300 text-sm flex items-center gap-1"
                                  >
                                    Abrir <ExternalLink className="w-3 h-3" />
                                  </a>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Validação */}
                        <div className="bg-gray-700 rounded-lg p-6">
                          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                            <CheckCircle className="text-green-400" />
                            Checklist de Validação
                          </h3>
                          <div className="space-y-3">
                            {resultado.deep_research.validacao.slice(0, 4).map((item, index) => (
                              <div key={index} className="flex items-start gap-3">
                                <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                                <p className="text-gray-300">
                                  {item.replace(/^[-\d\.\s]+/, "").trim()}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-4 justify-center">
                  <button
                    onClick={() => setModo("list")}
                    className="bg-gray-700 hover:bg-gray-600 text-white px-6 py-3 rounded-lg flex items-center gap-2"
                  >
                    <Archive className="w-4 h-4" />
                    Ver Todas as Pautas
                  </button>
                  <button
                    onClick={() => {
                      setResultado(null);
                      setTema("");
                    }}
                    className="bg-cyan-600 hover:bg-cyan-700 text-white px-6 py-3 rounded-lg flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Criar Nova Pauta
                  </button>
                </div>
              </div>
            )}

            {/* Empty State */}
            {!resultado && !isLoading && !error && (
              <div className="text-center py-12">
                <FileText className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400">Digite um tema para gerar uma nova pauta</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PautasDashboard;
