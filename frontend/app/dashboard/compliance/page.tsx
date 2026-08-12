"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Search,
  FileText,
  Scale,
  AlertCircle,
  BookOpen,
  Target,
  Zap,
  History as HistoryIcon,
  ExternalLink,
} from "lucide-react";

import { useCompliance } from "../../../hooks/useCompliance";
import {
  complianceAPI,
  type ComplianceHistoryItem,
  type ComplianceHistoryDetail,
} from "@/lib/compliance"; // ajuste para caminho relativo se não usar alias "@/"

/** ================= helpers de UI ================== */
const getStatusColor = (status: string) => {
  switch ((status || "").toLowerCase()) {
    case "compliant":
      return "text-green-400 bg-green-500/20 border-green-500/30";
    case "non_compliant":
    case "non compliant":
      return "text-red-400 bg-red-500/20 border-red-500/30";
    case "partial_compliant":
    case "partial compliant":
      return "text-yellow-400 bg-yellow-500/20 border-yellow-500/30";
    default:
      return "text-gray-400 bg-gray-500/20 border-gray-500/30";
  }
};

const getStatusIcon = (status: string) => {
  switch ((status || "").toLowerCase()) {
    case "compliant":
      return <CheckCircle className="w-5 h-5" />;
    case "non_compliant":
    case "non compliant":
      return <XCircle className="w-5 h-5" />;
    case "partial_compliant":
    case "partial compliant":
      return <AlertTriangle className="w-5 h-5" />;
    default:
      return <AlertCircle className="w-5 h-5" />;
  }
};

const getRiskColor = (risk?: string | null) => {
  switch ((risk || "").toLowerCase()) {
    case "low":
      return "text-green-400";
    case "medium":
      return "text-yellow-400";
    case "high":
      return "text-orange-400";
    case "critical":
      return "text-red-400";
    default:
      return "text-gray-400";
  }
};

const getRiskIcon = (risk?: string | null) => {
  switch ((risk || "").toLowerCase()) {
    case "low":
      return <Shield className="w-4 h-4" />;
    case "medium":
      return <AlertCircle className="w-4 h-4" />;
    case "high":
      return <AlertTriangle className="w-4 h-4" />;
    case "critical":
      return <Zap className="w-4 h-4" />;
    default:
      return <Shield className="w-4 h-4" />;
  }
};

/** ===== Confiança de CONFORMIDADE (0–1) calculada na UI ===== */
const normalize = (s?: string | null) =>
  (s || "").toString().trim().toLowerCase().replace(/\s+/g, "_");

const computeConformityConfidence = (p: {
  status?: string | null; // "compliant" | "non_compliant" | ...
  riskLevel?: string | null; // "low" | "medium" | "high" | "critical"
  legalRefs?: number; // total de citações/menções
  evidenceSources?: number; // nº de fontes distintas
}): number => {
  const status = normalize(p.status);
  const risk = normalize(p.riskLevel);
  const legalRefs = Math.max(0, p.legalRefs ?? 0);
  const evidenceSources = Math.max(0, p.evidenceSources ?? p.legalRefs ?? 0);

  // risco normalizado (proxy simples)
  const riskMap: Record<string, number> = {
    low: 0.2,
    medium: 0.5,
    high: 0.8,
    critical: 0.95,
  };
  const riskNorm = riskMap[risk] ?? 0.5;

  // evidência normalizada (>=3 satura)
  const evidenceNorm = Math.min(1, legalRefs / 3);
  const diversityBonus = Math.min(0.1, Math.max(0, evidenceSources - 1) * 0.03);

  // fórmula (mesma do backend revisado)
  let conf = 0.6 * (1 - riskNorm) + 0.4 * evidenceNorm + diversityBonus;

  // penalidades para não conforme
  if (status === "non_compliant" || status === "warning" || status === "non_compliant_warning") {
    if (legalRefs === 0) conf -= 0.25;
    else if (legalRefs < 2) conf -= 0.1;
  }

  // clamp estável
  conf = Math.max(0.05, Math.min(0.98, conf));
  return conf;
};

/** ===================== Página ===================== */
const ComplianceDashboard = () => {
  const [content, setContent] = useState("");
  const [context, setContext] = useState("e-commerce");

  const complianceHook = useCompliance();

  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // ====== Histórico ======
  const [history, setHistory] = useState<ComplianceHistoryItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const [selected, setSelected] = useState<ComplianceHistoryDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const loadHistory = useCallback(async () => {
    try {
      setLoadingHistory(true);
      const rows = await complianceAPI.listMy();
      setHistory(
        [...rows].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
      );
    } catch (err) {
      console.error("Erro ao carregar histórico:", err);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  const openDetail = useCallback(async (id: string) => {
    try {
      setLoadingDetail(true);
      const detail = await complianceAPI.getById(id);
      setSelected(detail);
      setTimeout(() => {
        document.getElementById("history-detail-card")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 50);
    } catch (err) {
      console.error("Erro ao obter detalhe:", err);
      setNotification({ type: "error", message: "Não foi possível carregar o detalhe" });
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    if (!notification) return;
    const t = setTimeout(() => setNotification(null), 5000);
    return () => clearTimeout(t);
  }, [notification]);

  const handleAnalyze = async () => {
    if (!content.trim()) {
      setNotification({ type: "error", message: "Digite um conteúdo para analisar" });
      return;
    }

    const result = await complianceHook.analyze({
      content: content.trim(),
      context: context,
    });

    if (result.ok) {
      setNotification({ type: "success", message: "Análise de compliance concluída!" });
      loadHistory();
    } else {
      setNotification({ type: "error", message: result.error || "Erro na análise de compliance" });
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Notificação */}
      {notification && (
        <div
          className={`fixed top-4 right-4 z-50 p-4 rounded-lg border backdrop-blur-sm transition-all duration-300 ${
            notification.type === "success"
              ? "bg-green-900/80 border-green-500/50 text-green-200"
              : "bg-red-900/80 border-red-500/50 text-red-200"
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === "success" ? (
              <CheckCircle className="h-5 w-5" />
            ) : (
              <AlertTriangle className="h-5 w-5" />
            )}
            <span>{notification.message}</span>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2 flex items-center justify-center gap-3">
            <Scale className="text-cyan-500" />
            Análise de Compliance
          </h1>
          <p className="text-gray-400">Verifique a conformidade legal do seu conteúdo</p>
        </div>

        {/* ================= FORM ================= */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-xl mb-8">
          <div className="grid grid-cols-1 gap-6">
            {/* Contexto */}
            <div>
              <label className="block text-sm font-medium mb-2 text-gray-300">Área de Contexto</label>
              <select
                value={context}
                onChange={(e) => setContext(e.target.value)}
                className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-cyan-500 text-white"
              >
                <option value="e-commerce">E-commerce</option>
                <option value="saude">Saúde</option>
                <option value="financeiro">Financeiro</option>
                <option value="educacao">Educação</option>
                <option value="marketing">Marketing</option>
                <option value="tecnologia">Tecnologia</option>
                <option value="alimentacao">Alimentação</option>
                <option value="farmaceutico">Farmacêutico</option>
                <option value="seguros">Seguros</option>
                <option value="telecomunicacoes">Telecomunicações</option>
              </select>
            </div>

            {/* Conteúdo */}
            <div>
              <label className="block text-sm font-medium mb-2 text-gray-300">Conteúdo para Análise</label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Ex: Vendemos produtos sem garantia e não nos responsabilizamos por defeitos."
                rows={6}
                className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 resize-none"
              />
              <p className="text-xs text-gray-400 mt-2">
                Digite o texto, política ou conteúdo que deseja verificar quanto à conformidade legal
              </p>
            </div>

            {/* Botão */}
            <div>
              <button
                onClick={handleAnalyze}
                disabled={complianceHook.loading || !content.trim()}
                className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {complianceHook.loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Analisando...
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4" />
                    Analisar Compliance
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* ================= HISTÓRICO ================= */}
        <div className="bg-gray-800 rounded-lg p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-white flex items-center gap-2">
              <HistoryIcon className="text-cyan-400" />
              Meu Histórico
            </h3>
            <button onClick={loadHistory} className="text-sm px-3 py-1.5 rounded border border-gray-600 hover:bg-gray-700">
              Atualizar
            </button>
          </div>

          {loadingHistory ? (
            <div className="text-gray-400">Carregando histórico…</div>
          ) : history.length === 0 ? (
            <div className="text-gray-400">Nenhuma análise encontrada.</div>
          ) : (
            <div className="space-y-2">
              {history.map((h) => (
                <div key={h.id} className="flex items-center justify-between bg-gray-700/60 border border-gray-600 rounded p-3">
                  <div className="flex items-center gap-3">
                    <div className={`px-2 py-1 rounded border ${getStatusColor(h.status)}`}>
                      <div className="flex items-center gap-1 text-sm">
                        {getStatusIcon(h.status)}
                        <span className="capitalize">{h.status.replace("_", " ")}</span>
                      </div>
                    </div>
                    <div className="text-sm text-gray-300">
                      <div className="flex gap-3 items-center">
                        <span className="text-gray-400">Contexto:</span>
                        <span className="font-medium">{h.context_area}</span>
                        <span className={`ml-2 ${getRiskColor(h.risk_level)}`}>{getRiskIcon(h.risk_level)} </span>
                        <span className={`${getRiskColor(h.risk_level)} font-medium capitalize`}>
                          {h.risk_level ?? "—"}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400">{new Date(h.created_at).toLocaleString("pt-BR")}</div>
                    </div>
                  </div>
                  <button onClick={() => openDetail(h.id)} className="flex items-center gap-2 text-cyan-400 hover:text-cyan-300 text-sm">
                    <ExternalLink className="w-4 h-4" />
                    Ver detalhes
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Detalhe */}
          {selected && (
            <div id="history-detail-card" className="mt-6 bg-gray-700 rounded-lg border border-gray-600 p-5">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold text-white flex items-center gap-2">
                  <FileText className="text-blue-400" />
                  Detalhe da Análise
                </h4>
                {loadingDetail && <span className="text-xs text-gray-400">Carregando…</span>}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div className={`p-3 rounded-lg border ${getStatusColor(selected.status)}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium">Status</span>
                    {getStatusIcon(selected.status)}
                  </div>
                  <p className="font-bold capitalize">{selected.status.replace("_", " ")}</p>
                </div>

                <div className="bg-gray-800 p-3 rounded-lg border border-gray-600">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-300">Confiança</span>
                    <Target className="w-4 h-4 text-blue-400" />
                  </div>
                  {(() => {
                    const conf = computeConformityConfidence({
                      status: selected.status,
                      riskLevel: selected.risk_level,
                      legalRefs: (selected as any).legal_sources_found ?? 0,
                      evidenceSources:
                        (selected as any).legal_sources_distinct ?? (selected as any).legal_sources_found ?? 0,
                    });
                    return <p className="text-lg font-bold text-blue-400">{Math.round(conf * 100)}%</p>;
                  })()}
                </div>

                <div className="bg-gray-800 p-3 rounded-lg border border-gray-600">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-300">Risco</span>
                    <span className={getRiskColor(selected.risk_level)}>{getRiskIcon(selected.risk_level)}</span>
                  </div>
                  <p className={`text-lg font-bold capitalize ${getRiskColor(selected.risk_level)}`}>
                    {selected.risk_level ?? "—"}
                  </p>
                </div>
              </div>

              {selected.summary && (
                <div className="bg-gray-800 p-3 rounded mb-3">
                  <h5 className="font-semibold text-white mb-1 flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-green-400" />
                    Resumo
                  </h5>
                  <p className="text-gray-300 text-sm">{selected.summary}</p>
                </div>
              )}

              {!!(selected.violations && selected.violations.length) && (
                <div className="bg-gray-800 rounded-lg p-4 mb-3">
                  <h5 className="font-semibold text-red-400 mb-2 flex items-center gap-2">
                    <XCircle className="w-4 h-4" />
                    Violações ({selected.violations?.length})
                  </h5>
                  <ul className="list-disc pl-5 space-y-1 text-red-300 text-sm">
                    {selected.violations?.map((v: any, i: number) => (
                      <li key={i}>{String(v)}</li>
                    ))}
                  </ul>
                </div>
              )}

              {!!(selected.recommendations && selected.recommendations.length) && (
                <div className="bg-gray-800 rounded-lg p-4">
                  <h5 className="font-semibold text-green-400 mb-2 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    Recomendações ({selected.recommendations?.length})
                  </h5>
                  <ul className="list-disc pl-5 space-y-1 text-green-300 text-sm">
                    {selected.recommendations?.map((r: any, i: number) => (
                      <li key={i}>{String(r)}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
        {/* ============== FIM HISTÓRICO ============== */}

        {/* ================= ERRO ================== */}
        {complianceHook.error && (
          <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 mb-8 text-center">
            <p className="text-red-200">{complianceHook.error}</p>
          </div>
        )}

        {/* ================= LOADING ================= */}
        {complianceHook.loading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500 mx-auto mb-4"></div>
            <p className="text-gray-400">Analisando conformidade legal...</p>
          </div>
        )}

        {/* ================= RESULTADO ATUAL ================= */}
        {complianceHook.result && !complianceHook.loading && (
          <div className="space-y-6">
            <div className="bg-gray-800 rounded-lg p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                  <FileText className="text-cyan-400" />
                  Resultado da Análise
                </h3>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-400">
                    {complianceHook.result.performance.total_time_seconds.toFixed(2)}s
                  </span>
                </div>
              </div>

              <div className={`p-4 rounded-lg border ${getStatusColor(complianceHook.result.ai_analysis.conformidade_status)}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">Status de Conformidade</span>
                  {getStatusIcon(complianceHook.result.ai_analysis.conformidade_status)}
                </div>
                <p className="font-bold capitalize">
                  {complianceHook.result.ai_analysis.conformidade_status.replace("_", " ")}
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 my-6">
                <div className="bg-gray-700 p-4 rounded-lg border border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-300">Confiança</span>
                    <Target className="w-5 h-5 text-blue-400" />
                  </div>
                  {(() => {
                    const r = complianceHook.result;
                    const conf = computeConformityConfidence({
                      status: r.ai_analysis.conformidade_status,
                      riskLevel: r.ai_analysis.risk_level,
                      legalRefs: r.legal_sources_found ?? 0,
                      evidenceSources: (r as any).legal_sources_distinct ?? r.legal_sources_found ?? 0,
                    });
                    return <p className="text-xl font-bold text-blue-400">{Math.round(conf * 100)}%</p>;
                  })()}
                </div>

                <div className="bg-gray-700 p-4 rounded-lg border border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-300">Nível de Risco</span>
                    <span className={getRiskColor(complianceHook.result.ai_analysis.risk_level)}>
                      {getRiskIcon(complianceHook.result.ai_analysis.risk_level)}
                    </span>
                  </div>
                  <p className={`text-xl font-bold capitalize ${getRiskColor(complianceHook.result.ai_analysis.risk_level)}`}>
                    {complianceHook.result.ai_analysis.risk_level}
                  </p>
                </div>

                <div className="bg-gray-700 p-4 rounded-lg border border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-300">Fontes Legais</span>
                    <Scale className="w-5 h-5 text-cyan-400" />
                  </div>
                  <p className="text-xl font-bold text-cyan-400">{complianceHook.result.legal_sources_found}</p>
                </div>
              </div>

              <div className="bg-gray-700 p-4 rounded-lg mb-6">
                <h4 className="font-semibold text-white mb-2 flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-green-400" />
                  Resumo da Análise
                </h4>
                <p className="text-gray-300 leading-relaxed">{complianceHook.result.ai_analysis.summary}</p>
              </div>

              <div className="bg-gray-700 p-4 rounded-lg mb-6">
                <h4 className="font-semibold text-white mb-2 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-blue-400" />
                  Análise Detalhada
                </h4>
                <p className="text-gray-300 leading-relaxed">{complianceHook.result.ai_analysis.detailed_analysis}</p>
              </div>

              {/* Violações */}
              {complianceHook.result.ai_analysis.violations.length > 0 && (
                <div className="bg-gray-800 rounded-lg p-6 mb-6">
                  <h4 className="font-semibold text-red-400 mb-4 flex items-center gap-2">
                    <XCircle className="w-5 h-5" />
                    Violações Identificadas ({complianceHook.result.ai_analysis.violations.length})
                  </h4>
                  <div className="space-y-3">
                    {complianceHook.result.ai_analysis.violations.map((violation, index) => (
                      <div key={index} className="bg-red-900/20 p-3 rounded-lg border border-red-500/30">
                        <p className="text-red-300 text-sm leading-relaxed">{violation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recomendações */}
              {complianceHook.result.ai_analysis.recommendations.length > 0 && (
                <div className="bg-gray-800 rounded-lg p-6">
                  <h4 className="font-semibold text-green-400 mb-4 flex items-center gap-2">
                    <CheckCircle className="w-5 h-5" />
                    Recomendações ({complianceHook.result.ai_analysis.recommendations.length})
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {complianceHook.result.ai_analysis.recommendations.map((recommendation, index) => (
                      <div key={index} className="bg-green-900/20 p-4 rounded-lg border border-green-500/30">
                        <div className="flex items-start gap-3">
                          <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                          <p className="text-green-300 text-sm leading-relaxed">{recommendation}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Rodapé do resultado */}
              <div className="bg-gray-800 rounded-lg p-4 mt-6">
                <div className="flex items-center justify-between text-sm text-gray-400">
                  <div className="flex items-center gap-4">
                    <span>Análise: {complianceHook.result.analysis_type}</span>
                    <span>Contexto: {complianceHook.result.context_area}</span>
                  </div>
                  <div>{new Date(complianceHook.result.timestamp).toLocaleString("pt-BR")}</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ================= EMPTY ================= */}
        {!complianceHook.result && !complianceHook.loading && !complianceHook.error && (
          <div className="text-center py-12">
            <Scale className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">Digite um conteúdo para analisar sua conformidade legal</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ComplianceDashboard;
