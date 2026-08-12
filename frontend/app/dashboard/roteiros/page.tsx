"use client";

import { useRef, useState } from "react";
import {
  Play,
  Clock,
  Hash,
  Film,
  ChevronDown,
  Loader2,
  Copy,
  CheckCircle,
  ShieldCheck,
} from "lucide-react";
import { useRoteiros } from "@/hooks/useRoteiros";
import type { EpisodeRequest, EpisodeBlock } from "@/lib/roteiros";

/* ========================= Constantes ========================= */
const TIPOS_SERIE = [
  "motivacional",
  "educativo",
  "inspirador",
  "casual",
  "profissional",
] as const;

const RISK_OPTS = ["low", "medium", "high"] as const;

/** Gera uma key estável sem usar o índice puro. */
const makeKey = (a?: string, b?: string, i?: number) =>
  [a?.toLowerCase().slice(0, 24) || "item", b || "", String(i ?? "")].join("|");

/* ========================= Página ========================= */
export default function RoteirosPage() {
  const { loading, error, episode, generate, clear } = useRoteiros();
  const [copied, setCopied] = useState<string | null>(null);

  // form state
  const [titulo, setTitulo] = useState("");
  const [tipoSerie, setTipoSerie] =
    useState<(typeof TIPOS_SERIE)[number]>("motivacional");
  const [numeroEpisodio, setNumeroEpisodio] = useState(1);
  const [duracaoEstimada, setDuracaoEstimada] = useState(15);
  const [historia, setHistoria] = useState("");
  const [safetyOn, setSafetyOn] = useState(true);
  const [riskTolerance, setRiskTolerance] =
    useState<(typeof RISK_OPTS)[number]>("medium");

  const resultsRef = useRef<HTMLDivElement | null>(null);

  async function onGenerate() {
    if (titulo.trim().length < 5) {
      alert("Título mínimo: 5 caracteres.");
      return;
    }
    clear();

    const payload: EpisodeRequest = {
      titulo: titulo.trim(),
      tipo_serie: tipoSerie,
      numero_episodio: numeroEpisodio,
      duracao_estimada: duracaoEstimada,
      historia_pessoal: historia.trim() || undefined,
      enable_safety_check: safetyOn,
      risk_tolerance: riskTolerance,
    };

    const res = await generate(payload);
    if ((res as any).error) return;

    // rolar até os resultados
    setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth" }), 150);
  }

  function copy(text: string, key: string) {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(null), 2000);
    });
  }

  function formatBlocos(blocos: Array<Partial<EpisodeBlock>>) {
    if (!Array.isArray(blocos)) return "";
    return blocos
      .map(
        (b, i) =>
          `### ${b?.titulo || `Bloco ${i + 1}`}\n\n${b?.conteudo ?? (b as any)?.texto ?? ""}\n`
      )
      .join("\n");
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Film className="h-8 w-8 text-purple-400" />
            Gerar Roteiro (Episódio)
          </h1>
          <p className="text-gray-400 mt-2">
            Crie roteiros completos com outline, blocos e metadados usando IA.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Form */}
          <div className="lg:col-span-1">
            <div className="bg-gray-800 rounded-lg p-6 sticky top-4">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Hash className="h-5 w-5" />
                Configurações
              </h2>

              <div className="space-y-4">
                {/* Título */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Título do episódio
                  </label>
                  <input
                    type="text"
                    value={titulo}
                    onChange={(e) => setTitulo(e.target.value)}
                    placeholder="Ex.: A vida na cidade grande"
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    maxLength={120}
                  />
                  <p className="text-xs text-gray-400 mt-1">{titulo.length}/120</p>
                </div>

                {/* Tipo */}
                <div>
                  <label className="block text-sm font-medium mb-2">Tipo/Série</label>
                  <div className="relative">
                    <select
                      value={tipoSerie}
                      onChange={(e) =>
                        setTipoSerie(e.target.value as (typeof TIPOS_SERIE)[number])
                      }
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 pr-8 focus:ring-2 focus:ring-purple-500 focus:border-transparent appearance-none"
                    >
                      {TIPOS_SERIE.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                  </div>
                </div>

                {/* Número e Duração */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2"># Episódio</label>
                    <input
                      type="number"
                      min={1}
                      max={999}
                      value={numeroEpisodio}
                      onChange={(e) =>
                        setNumeroEpisodio(Math.max(1, parseInt(e.target.value) || 1))
                      }
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Duração (min)</label>
                    <input
                      type="number"
                      min={5}
                      max={60}
                      value={duracaoEstimada}
                      onChange={(e) =>
                        setDuracaoEstimada(
                          Math.max(5, Math.min(60, parseInt(e.target.value) || 15))
                        )
                      }
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    />
                  </div>
                </div>

                {/* História */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    História pessoal / contexto (opcional)
                  </label>
                  <textarea
                    rows={4}
                    value={historia}
                    onChange={(e) => setHistoria(e.target.value)}
                    placeholder="Algo que ajude a personalizar o roteiro…"
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  />
                </div>

                {/* Safety + Risco */}
                <div className="grid grid-cols-2 gap-4 items-end">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={safetyOn}
                      onChange={(e) => setSafetyOn(e.target.checked)}
                      className="h-4 w-4"
                    />
                    <span className="flex items-center gap-1">
                      <ShieldCheck className="h-4 w-4 text-cyan-400" />
                      Verificação de segurança
                    </span>
                  </label>

                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Nível de risco
                    </label>
                    <select
                      value={riskTolerance}
                      onChange={(e) =>
                        setRiskTolerance(e.target.value as (typeof RISK_OPTS)[number])
                      }
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2"
                    >
                      {RISK_OPTS.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Botão */}
                <button
                  onClick={onGenerate}
                  disabled={loading || titulo.trim().length < 5}
                  className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white py-3 px-4 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Gerando...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4" />
                      Gerar roteiro
                    </>
                  )}
                </button>

                {error && <p className="text-red-400 text-sm pt-2">Erro: {error}</p>}
              </div>
            </div>
          </div>

          {/* Resultados */}
          <div className="lg:col-span-2" ref={resultsRef}>
            {loading && (
              <div className="bg-gray-800 rounded-lg p-8 text-center">
                <Loader2 className="h-12 w-12 animate-spin text-purple-400 mx-auto mb-4" />
                <p className="text-lg font-medium">Gerando roteiro…</p>
                <p className="text-gray-400 text-sm mt-2">
                  A IA está criando outline, blocos e metadados.
                </p>
              </div>
            )}

            {!loading && !episode && (
              <div className="bg-gray-800 rounded-lg p-8 text-center">
                <Film className="h-16 w-16 text-gray-600 mx-auto mb-4" />
                <p className="text-lg font-medium text-gray-400">
                  Configure os campos e clique em “Gerar roteiro”.
                </p>
                <p className="text-gray-500 text-sm mt-2">
                  O resultado aparecerá aqui com opções para copiar.
                </p>
              </div>
            )}

            {episode && (
              <div className="space-y-6">
                {/* Header do resultado */}
                <div className="bg-gray-800 rounded-lg p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-2xl font-bold">{episode.titulo}</h2>
                    <div className="flex items-center gap-2 text-sm text-gray-400">
                      <Clock className="h-4 w-4" />
                      {episode.tempo_geracao?.toFixed?.(2) ?? episode.tempo_geracao}s
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <span className="bg-purple-600/20 text-purple-300 px-3 py-1 rounded-full text-sm">
                      {episode.tipo_serie}
                    </span>
                    <span className="bg-blue-600/20 text-blue-300 px-3 py-1 rounded-full text-sm">
                      Episódio #{episode.numero_episodio}
                    </span>
                    {episode.metadados?.tempo_total_estimado && (
                      <span className="bg-green-600/20 text-green-300 px-3 py-1 rounded-full text-sm">
                        {episode.metadados.tempo_total_estimado}
                      </span>
                    )}
                  </div>
                </div>

                {/* Outline */}
                {episode.outline && (
                  <div className="bg-gray-800 rounded-lg p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xl font-semibold">📋 Outline</h3>
                      <button
                        onClick={() =>
                          copy(JSON.stringify(episode.outline, null, 2), "outline")
                        }
                        className="text-gray-400 hover:text-white transition-colors"
                      >
                        {copied === "outline" ? (
                          <CheckCircle className="h-4 w-4" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </button>
                    </div>

                    <div className="space-y-4 text-gray-300">
                      {episode.outline.introducao && (
                        <div>
                          <strong>Introdução:</strong>
                          <p className="mt-1">{episode.outline.introducao}</p>
                        </div>
                      )}

                      {Array.isArray(episode.outline.desenvolvimento) && (
                        <div>
                          <strong>Desenvolvimento:</strong>
                          <ul className="mt-1 space-y-1">
                            {episode.outline.desenvolvimento.map((item, i) => (
                              <li
                                key={makeKey(item, "desenvolvimento", i)}
                                className="flex items-start gap-2"
                              >
                                <span className="text-purple-400 mt-1">•</span>
                                {item}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {episode.outline.conclusao && (
                        <div>
                          <strong>Conclusão:</strong>
                          <p className="mt-1">{episode.outline.conclusao}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Roteiro */}
                {episode.roteiro && (
                  <div className="bg-gray-800 rounded-lg p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xl font-semibold">🎬 Roteiro</h3>
                      <button
                        onClick={() => {
                          const txt = `${episode.roteiro.abertura || ""}\n\n${formatBlocos(
                            (episode.roteiro.blocos ?? []) as Array<Partial<EpisodeBlock>>
                          )}\n${episode.roteiro.encerramento || ""}`;
                          copy(txt, "roteiro");
                        }}
                        className="text-gray-400 hover:text-white transition-colors"
                      >
                        {copied === "roteiro" ? (
                          <CheckCircle className="h-4 w-4" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </button>
                    </div>

                    <div className="space-y-6 text-gray-300">
                      {episode.roteiro.abertura && (
                        <div>
                          <h4 className="font-semibold text-purple-400 mb-2">
                            Abertura
                          </h4>
                          <p className="whitespace-pre-wrap">
                            {episode.roteiro.abertura}
                          </p>
                        </div>
                      )}

                      {Array.isArray(episode.roteiro.blocos) &&
                        episode.roteiro.blocos.map((b, i) => {
                          const pb = b as Partial<EpisodeBlock>;
                          return (
                            <div
                              key={makeKey(pb?.titulo, pb?.tempo_estimado, i)}
                            >
                              <h4 className="font-semibold text-blue-400 mb-2">
                                {pb?.titulo || `Bloco ${i + 1}`}
                                {pb?.tempo_estimado && (
                                  <span className="text-sm text-gray-400 ml-2">
                                    ({pb.tempo_estimado})
                                  </span>
                                )}
                              </h4>
                              <p className="whitespace-pre-wrap">
                                {pb?.conteudo ?? (pb as any)?.texto ?? ""}
                              </p>
                            </div>
                          );
                        })}

                      {episode.roteiro.encerramento && (
                        <div>
                          <h4 className="font-semibold text-green-400 mb-2">
                            Encerramento
                          </h4>
                          <p className="whitespace-pre-wrap">
                            {episode.roteiro.encerramento}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Metadados */}
                {episode.metadados && (
                  <div className="bg-gray-800 rounded-lg p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xl font-semibold">📊 Metadados</h3>
                      <button
                        onClick={() =>
                          copy(JSON.stringify(episode.metadados, null, 2), "metadados")
                        }
                        className="text-gray-400 hover:text-white transition-colors"
                      >
                        {copied === "metadados" ? (
                          <CheckCircle className="h-4 w-4" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-gray-300">
                      {Array.isArray(episode.metadados?.principais_ctas) && (
                        <div>
                          <strong className="text-purple-400">CTAs:</strong>
                          <ul className="mt-1 space-y-1">
                            {episode.metadados.principais_ctas.map((cta, i) => (
                              <li key={makeKey(cta, "cta", i)} className="text-sm">
                                • {cta}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {Array.isArray(episode.metadados?.hashtags_sugeridas) && (
                        <div>
                          <strong className="text-blue-400">Hashtags:</strong>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {episode.metadados.hashtags_sugeridas.map((tag, i) => (
                              <span
                                key={makeKey(tag, "hashtag", i)}
                                className="text-xs bg-gray-700 px-2 py-1 rounded"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {Array.isArray(episode.metadados?.pontos_chave) && (
                        <div className="md:col-span-2">
                          <strong className="text-green-400">Pontos-chave:</strong>
                          <ul className="mt-1 space-y-1">
                            {episode.metadados.pontos_chave.map((p, i) => (
                              <li key={makeKey(p, "ponto", i)} className="text-sm">
                                • {p}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
