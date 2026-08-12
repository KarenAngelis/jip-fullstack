"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  FileText,
  Clock,
  CheckCircle,
  MessageCircle,
  Wand2,
  Copy,
  Star,
  RefreshCw,
  History,
} from "lucide-react";

import { useTitles } from "@/hooks/useTitles";
import { useEpisodes } from "@/hooks/useEpisodes";
import { useTitleRecords } from "@/hooks/useTitleRecords";
import { useEpisodeHistory } from "@/hooks/useEpisodeHistory";

type Tab = "titulos" | "episodios";

const ContentDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>("titulos");

  // ====== form comum ======
  const [mainTopic, setMainTopic] = useState("");

  // ====== form títulos ======
  const [audience, setAudience] = useState("iniciantes");
  const [contentTone, setContentTone] = useState("inspirador");

  // ====== form episódios ======
  const [context, setContext] = useState("");
  const [personalInput, setPersonalInput] = useState("");
  const [targetAudience, setTargetAudience] = useState(
    "profissionais de marketing digital"
  );
  const [episodeFormat, setEpisodeFormat] = useState("painel de debate");

  // ====== hooks ======
  const titlesHook = useTitles();
  const episodesHook = useEpisodes();
  const recordsHook = useTitleRecords({ limit: 20, order: "desc" }); // histórico (lista)

  // Histórico de Episódios (batches)
  const epHistory = useEpisodeHistory({ limit: 10, include_episodes: false, auto: true });

  // ====== notificação ======
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  useEffect(() => {
    if (!notification) return;
    const t = setTimeout(() => setNotification(null), 4000);
    return () => clearTimeout(t);
  }, [notification]);

  // ====== copiar ======
  const copyToClipboard = (text: string) => {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard
        .writeText(text)
        .then(() =>
          setNotification({
            type: "success",
            message: "Copiado para a área de transferência!",
          })
        )
        .catch(() =>
          setNotification({
            type: "error",
            message: "Não foi possível copiar",
          })
        );
    }
  };

  // ====== gerar títulos ======
  const generateTitles = async () => {
    if (!mainTopic.trim()) {
      setNotification({ type: "error", message: "Digite um tópico para continuar" });
      return;
    }
    const result = await titlesHook.generate({
      topic: mainTopic.trim(),
      audience: (audience as any) || "iniciantes",
      tone: contentTone as any,
      quantity: 5,
    });

    if (result.ok) {
      setNotification({
        type: "success",
        message: `${titlesHook.items.length} títulos gerados com sucesso!`,
      });
      recordsHook.refresh(); // atualiza histórico após gravar
    } else {
      setNotification({
        type: "error",
        message: (result as any).error || "Erro ao gerar títulos",
      });
    }
  };

  // ====== gerar episódios ======
  const generateEpisodes = async () => {
    if (!mainTopic.trim()) {
      setNotification({ type: "error", message: "Digite um tópico para continuar" });
      return;
    }

    const result = await episodesHook.generate({
      title: mainTopic.trim(),
      context: context.trim() || "Explorando o tema em profundidade",
      personal_input: personalInput.trim(),
      target_audience: targetAudience,
      episode_format: episodeFormat,
    });

    if (result.ok) {
      const total =
        (result as any)?.data?.total_suggestions ??
        episodesHook.suggestions.length ??
        0;

      setNotification({
        type: "success",
        message: `${total} sugestões de episódios geradas!`,
      });

      // Atualiza a lista de batches do histórico
      epHistory.refresh();
    } else {
      setNotification({
        type: "error",
        message: (result as any).error || "Erro ao gerar episódios",
      });
    }
  };

  // ====== dispatcher ======
  const handleGenerate = async () => {
    if (activeTab === "titulos") {
      titlesHook.clear();
      await generateTitles();
    } else {
      episodesHook.clear();
      await generateEpisodes();
    }
  };

  // ====== helpers de exibição ======
  const currentResults =
    activeTab === "titulos"
      ? titlesHook.items
      : (episodesHook.suggestions as any[]);
  const isLoading =
    activeTab === "titulos" ? titlesHook.loading : episodesHook.loading;
  const error = activeTab === "titulos" ? titlesHook.error : episodesHook.error;

  // ====== FALLBACKS SEGUROS PARA O HISTÓRICO (títulos) ======
  const dbItems = useMemo(
    () => (Array.isArray(recordsHook.records) ? recordsHook.records : []),
    [recordsHook.records]
  );
  const totalRecords =
    typeof recordsHook.total === "number" ? recordsHook.total : dbItems.length;

  // ====== estado local para expandir batches de episódios ======
  const [openBatchId, setOpenBatchId] = useState<number | null>(null);
  const toggleBatch = async (id: number) => {
    if (openBatchId === id) {
      setOpenBatchId(null);
      return;
    }
    setOpenBatchId(id);
    // garante que o batch tenha episodes carregados
    const batch = epHistory.batches.find((b) => b.batch_id === id);
    const hasEpisodes = Array.isArray(batch?.episodes) && batch!.episodes!.length > 0;
    if (!hasEpisodes) {
      await epHistory.loadBatch(id);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      {/* ====== toast ====== */}
      {notification && (
        <div
          className={`fixed top-4 right-4 z-50 p-4 rounded-lg border backdrop-blur-sm transition-all duration-300 ${
            notification.type === "success"
              ? "bg-emerald-900/80 border-emerald-500/40 text-emerald-100"
              : "bg-rose-900/80 border-rose-500/40 text-rose-100"
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === "success" ? (
              <CheckCircle className="h-5 w-5" />
            ) : (
              <MessageCircle className="h-5 w-5" />
            )}
            <span className="text-sm">{notification.message}</span>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto">
        {/* ====== título página ====== */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2 flex items-center justify-center gap-3">
            <Wand2 className="text-cyan-400" />
            Geração de Conteúdo IA
          </h1>
          <p className="text-gray-400">
            Crie títulos e sugestões de episódios inteligentes
          </p>
        </div>

        {/* ====== tabs ====== */}
        <div className="flex justify-center mb-8">
          <div className="bg-gray-900 rounded-xl p-1 flex shadow-lg shadow-black/20">
            <button
              onClick={() => setActiveTab("titulos")}
              className={`px-6 py-2 rounded-lg transition-colors ${
                activeTab === "titulos"
                  ? "bg-cyan-600 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <FileText className="w-4 h-4 inline mr-2" /> Títulos
            </button>
            <button
              onClick={() => setActiveTab("episodios")}
              className={`px-6 py-2 rounded-lg transition-colors ${
                activeTab === "episodios"
                  ? "bg-cyan-600 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <Clock className="w-4 h-4 inline mr-2" /> Episódios
            </button>
          </div>
        </div>

        {/* ====== form ====== */}
        <div className="bg-gray-900/70 border border-gray-800 rounded-2xl p-6 shadow-xl mb-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            {/* tópico/título */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-2 text-gray-300">
                {activeTab === "titulos" ? "Tópico Principal" : "Título do Episódio"}
              </label>
              <input
                type="text"
                value={mainTopic}
                onChange={(e) => setMainTopic(e.target.value)}
                placeholder={
                  activeTab === "titulos" ? "Ex: ENEM 2025" : "Ex: A revolução do conteúdo digital"
                }
                className="w-full p-3 rounded-xl bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
              />
            </div>

            {/* audiência ou formato */}
            <div>
              <label className="block text-sm font-medium mb-2 text-gray-300">
                {activeTab === "titulos" ? "Audiência" : "Formato do Episódio"}
              </label>
              {activeTab === "titulos" ? (
                <select
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                  className="w-full p-3 bg-gray-800 border border-gray-700 rounded-xl focus:ring-2 focus:ring-cyan-500 text-white"
                >
                  <option value="iniciantes">Iniciantes</option>
                  <option value="intermediario">Intermediário</option>
                  <option value="avancado">Avançado</option>
                  <option value="geral">Geral</option>
                </select>
              ) : (
                <select
                  value={episodeFormat}
                  onChange={(e) => setEpisodeFormat(e.target.value)}
                  className="w-full p-3 bg-gray-800 border border-gray-700 rounded-xl focus:ring-2 focus:ring-cyan-500 text-white"
                >
                  <option value="painel de debate">Painel de Debate</option>
                  <option value="entrevista">Entrevista</option>
                  <option value="tutorial">Tutorial</option>
                  <option value="storytelling">Storytelling</option>
                  <option value="mesa redonda">Mesa Redonda</option>
                  <option value="monólogo">Monólogo</option>
                </select>
              )}
            </div>

            {/* botão */}
            <div className="flex items-end">
              <button
                onClick={handleGenerate}
                disabled={isLoading || !mainTopic.trim()}
                className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold py-3 px-6 rounded-xl transition-all duration-300 hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg shadow-cyan-900/30"
              >
                {isLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Gerando...
                  </>
                ) : (
                  <>
                    <Wand2 className="w-4 h-4" />
                    Gerar {activeTab === "titulos" ? "Títulos" : "Episódios"}
                  </>
                )}
              </button>
            </div>
          </div>

          {/* extras de episódios */}
          {activeTab === "episodios" && (
            <div className="grid grid-cols-1 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-300">
                  Contexto do Episódio
                </label>
                <textarea
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  rows={3}
                  placeholder="Ex: Explorando como a IA está transformando a criação de conteúdo."
                  className="w-full p-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 resize-none"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2 text-gray-300">
                    Audiência Alvo
                  </label>
                  <select
                    value={targetAudience}
                    onChange={(e) => setTargetAudience(e.target.value)}
                    className="w-full p-3 bg-gray-800 border border-gray-700 rounded-xl focus:ring-2 focus:ring-cyan-500 text-white"
                  >
                    <option value="profissionais de marketing digital">
                      Marketing Digital
                    </option>
                    <option value="empreendedores">Empreendedores</option>
                    <option value="estudantes">Estudantes</option>
                    <option value="desenvolvedores">Desenvolvedores</option>
                    <option value="criadores de conteúdo">Criadores de Conteúdo</option>
                    <option value="público geral">Público Geral</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 text-gray-300">
                    Input Pessoal (opcional)
                  </label>
                  <input
                    type="text"
                    value={personalInput}
                    onChange={(e) => setPersonalInput(e.target.value)}
                    placeholder="Ex: Quero destacar como pequenos criadores podem competir com grandes empresas"
                    className="w-full p-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ====== erro / loading da geração ====== */}
        {error && (
          <div className="bg-rose-900/40 border border-rose-600/40 rounded-xl p-4 mb-8 text-center">
            <p className="text-rose-100">{error}</p>
          </div>
        )}

        {isLoading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500 mx-auto mb-4"></div>
            <p className="text-gray-400">IA gerando conteúdo...</p>
          </div>
        )}

        {/* ====== resultados da geração atual ====== */}
        {currentResults.length > 0 && !isLoading && (
          <div className="bg-gray-900/70 border border-gray-800 rounded-2xl p-6 shadow-xl mb-8">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Star className="text-yellow-400" />
              {activeTab === "titulos" ? "Títulos Gerados" : "Sugestões de Episódios"}
              <span className="text-sm text-gray-400">({currentResults.length})</span>
            </h3>

            {/* LISTA DE TÍTULOS */}
            {activeTab === "titulos" && (
              <div className="space-y-3">
                {currentResults.map((item: any, index: number) => (
                  <div
                    key={index}
                    className="bg-gray-800/80 border border-gray-700 rounded-xl p-4 flex items-start justify-between"
                  >
                    <h4 className="text-base font-medium pr-4">{item.title}</h4>
                    <button
                      onClick={() => copyToClipboard(item.title)}
                      className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
                      title="Copiar"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* LISTA DE EPISÓDIOS (detalhada) */}
            {activeTab === "episodios" && (
              <div className="space-y-4">
                {currentResults.map((item: any, index: number) => {
                  const rawKW = Array.isArray(item.keywords) ? item.keywords : (item.keywords ?? []);
                  const kwJoined = Array.isArray(rawKW) ? rawKW.join("\n") : String(rawKW ?? "");
                  const keywords = kwJoined
                    .split("\n")
                    .map((s) =>
                      s.replace(/^\s*\d+\.\s*/g, "").replace(/^keyword\d*:\s*/i, "").trim()
                    )
                    .filter(Boolean)
                    .slice(0, 8);

                  return (
                    <div
                      key={item.id ?? index}
                      className="bg-gray-800/80 border border-gray-700 rounded-xl p-4"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <h4 className="text-base font-semibold text-white mb-1">
                            {item.title}
                          </h4>
                          {item.short_description && (
                            <p className="text-sm text-gray-300 leading-relaxed">
                              {item.short_description}
                            </p>
                          )}
                        </div>
                        <button
                          onClick={() => copyToClipboard(item.title)}
                          className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
                          title="Copiar título"
                        >
                          <Copy className="h-4 w-4" />
                        </button>
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        {typeof item.success_probability === "number" && (
                          <span className="text-[11px] px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-700/40">
                            Sucesso {item.success_probability}%
                          </span>
                        )}
                        {item.jip_trend_analysis?.trend_score != null && (
                          <span className="text-[11px] px-2 py-1 rounded-full bg-blue-500/10 text-blue-300 border border-blue-700/40">
                            Trend {item.jip_trend_analysis.trend_score}
                          </span>
                        )}
                        {item.jip_market_analysis?.estimated_reach != null && (
                          <span className="text-[11px] px-2 py-1 rounded-full bg-purple-500/10 text-purple-300 border border-purple-700/40">
                            Alcance {item.jip_market_analysis.estimated_reach}
                          </span>
                        )}
                        {item.estimated_duration != null && (
                          <span className="text-[11px] px-2 py-1 rounded-full bg-orange-500/10 text-orange-300 border border-orange-700/40">
                            {item.estimated_duration} min
                          </span>
                        )}
                      </div>

                      {/* keywords */}
                      {keywords.length > 0 && (
                        <div className="mt-4">
                          <h6 className="text-xs font-semibold text-yellow-400 mb-2">
                            Keywords principais
                          </h6>
                          <div className="flex flex-wrap gap-2">
                            {keywords.map((kw: string, i: number) => (
                              <span
                                key={i}
                                className="text-[11px] px-2 py-1 bg-yellow-600/20 text-yellow-300 rounded"
                                title={kw}
                              >
                                {kw.length > 30 ? kw.slice(0, 30) + "…" : kw}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="mt-4 flex gap-2 flex-wrap text-[11px] text-gray-400">
                        <span>
                          🎯 Público:{" "}
                          <span className="text-gray-200">
                            {item.target_audience ?? "—"}
                          </span>
                        </span>
                        <span>
                          ⏱️ Criado em:{" "}
                          <span className="text-gray-200">
                            {item.created_at ? new Date(item.created_at).toLocaleString() : "—"}
                          </span>
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ====== HISTÓRICO DE TÍTULOS — só na aba Títulos ====== */}
        {activeTab === "titulos" && (
          <div className="bg-gray-900/70 border border-gray-800 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <History className="text-cyan-400" />
                Histórico de Títulos (Banco de Dados)
                <span className="text-sm text-gray-400">({totalRecords})</span>
              </h3>

              <button
                onClick={() => recordsHook.refresh()}
                className="px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm flex items-center gap-2 border border-gray-700"
                title="Atualizar"
              >
                <RefreshCw className="w-4 h-4" /> Atualizar
              </button>
            </div>

            {recordsHook.loading ? (
              <div className="text-center py-10 text-gray-400">Carregando histórico…</div>
            ) : dbItems.length === 0 ? (
              <div className="text-center py-10 text-gray-400">Sem registros para exibir.</div>
            ) : (
              <ul className="space-y-3">
                {dbItems.map((rec) => {
                  const created = new Date(rec.created_at).toLocaleString();
                  const bestTitle = rec.best_title || rec.topic;
                  const total = rec.total_titles ?? rec.quantity ?? 0;
                  const bestScore = rec.best_score ?? 0;
                  const seconds =
                    typeof rec.generation_time === "number"
                      ? `${rec.generation_time.toFixed(2)}s`
                      : "-";
                  const status = rec.status ?? "success";

                  return (
                    <li
                      key={rec.id}
                      className="bg-gray-800/80 border border-gray-700 rounded-xl px-4 py-3"
                    >
                      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                        <div className="min-w-0">
                          <div className="text-[11px] text-gray-400 mb-1 truncate">
                            #{rec.id} • {created} •{" "}
                            <span className="text-gray-200">{rec.topic}</span>
                          </div>
                          <div className="flex items-start gap-2">
                            <h4 className="text-white font-medium text-[15px] leading-snug break-words">
                              {bestTitle}
                            </h4>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[11px] px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-700/40">
                            Score {bestScore}
                          </span>
                          <span className="text-[11px] px-2 py-1 rounded-full bg-blue-500/10 text-blue-300 border border-blue-700/40">
                            {total} títulos
                          </span>
                          <span
                            className={`text-[11px] px-2 py-1 rounded-full border ${
                              status === "success"
                                ? "bg-cyan-500/10 text-cyan-300 border-cyan-700/40"
                                : "bg-rose-500/10 text-rose-300 border-rose-700/40"
                            }`}
                          >
                            {status}
                          </span>
                          <span className="text-[11px] px-2 py-1 rounded-full bg-purple-500/10 text-purple-300 border border-purple-700/40">
                            {seconds}
                          </span>

                          <button
                            onClick={() => copyToClipboard(bestTitle)}
                            className="ml-1 p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
                            title="Copiar melhor título"
                          >
                            <Copy className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}

        {/* ====== HISTÓRICO DE EPISÓDIOS — só na aba Episódios ====== */}
        {activeTab === "episodios" && (
          <div className="bg-gray-900/70 border border-gray-800 rounded-2xl p-6 shadow-xl mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <History className="text-cyan-400" />
                Histórico de Episódios (Banco de Dados)
                <span className="text-sm text-gray-400">({epHistory.total})</span>
              </h3>

              <button
                onClick={() => epHistory.refresh()}
                className="px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm flex items-center gap-2 border border-gray-700"
                title="Atualizar"
              >
                <RefreshCw className="w-4 h-4" /> Atualizar
              </button>
            </div>

            {epHistory.loading ? (
              <div className="text-center py-10 text-gray-400">Carregando histórico…</div>
            ) : !epHistory.hasData ? (
              <div className="text-center py-10 text-gray-400">Sem batches de episódios ainda.</div>
            ) : (
              <ul className="space-y-3">
                {epHistory.batches.map((b) => {
                  const created = new Date(b.created_at).toLocaleString();
                  const isOpen = openBatchId === b.batch_id;
                  return (
                    <li
                      key={b.batch_id}
                      className="bg-gray-800/80 border border-gray-700 rounded-xl"
                    >
                      <button
                        onClick={() => toggleBatch(b.batch_id)}
                        className="w-full px-4 py-3 flex items-center justify-between text-left"
                        title="Expandir"
                      >
                        <div className="min-w-0">
                          <div className="text-[11px] text-gray-400 mb-1 truncate">
                            #{b.batch_id} • {created} •{" "}
                            <span className="text-gray-200">{b.request_title}</span>
                          </div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[11px] px-2 py-1 rounded-full bg-blue-500/10 text-blue-300 border border-blue-700/40">
                              {b.total_suggestions} episódios
                            </span>
                            <span className="text-[11px] px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-700/40">
                              Trend {b.overall_trend_score}
                            </span>
                            <span className="text-[11px] px-2 py-1 rounded-full bg-purple-500/10 text-purple-300 border border-purple-700/40">
                              {b.market_opportunity}
                            </span>
                          </div>
                        </div>
                        <span className="text-xs text-gray-400">
                          {isOpen ? "▲" : "▼"}
                        </span>
                      </button>

                      {isOpen && (
                        <div className="px-4 pb-4">
                          {Array.isArray(b.episodes) && b.episodes.length > 0 ? (
                            <div className="space-y-2">
                              {b.episodes.map((ep) => (
                                <div
                                  key={ep.id}
                                  className="bg-gray-900/60 border border-gray-700 rounded-lg p-3 flex items-start justify-between"
                                >
                                  <div className="pr-3">
                                    <p className="text-sm text-white font-medium">
                                      {ep.title}
                                    </p>
                                    {ep.short_description && (
                                      <p className="text-xs text-gray-300 mt-1">
                                        {ep.short_description}
                                      </p>
                                    )}
                                  </div>
                                  <button
                                    onClick={() => copyToClipboard(ep.title)}
                                    className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
                                    title="Copiar título"
                                  >
                                    <Copy className="h-4 w-4" />
                                  </button>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-sm text-gray-400">
                              Carregando episódios do batch…
                            </div>
                          )}
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}

        {/* vazio inicial */}
        {currentResults.length === 0 && !isLoading && !error && (
          <div className="text-center py-12">
            <Wand2 className="w-16 h-16 text-gray-700 mx-auto mb-4" />
            <p className="text-gray-500">Digite um tópico para gerar conteúdo</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContentDashboard;
