// src/app/dashboard/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authAPI, type User, get } from "@/lib/api";
import {
  complianceAPI,
  type ComplianceHistoryItem,
} from "@/lib/compliance";
import { Scale, Clock, FileText } from "lucide-react";

type PautasListResponse = {
  pautas: Array<{
    id: number;
    tema: string;
    duracao_min: number;
    status: string;
    popularidade_score?: number | null;
    tendencia?: string | null;
    created_at: string;
  }>;
  total: number;
};

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // === Compliance card ===
  const [compLoading, setCompLoading] = useState(true);
  const [compCount, setCompCount] = useState(0);
  const [lastCompAt, setLastCompAt] = useState<string | null>(null);

  // === Pautas card ===
  const [pautasLoading, setPautasLoading] = useState(true);
  const [pautasCount, setPautasCount] = useState(0);
  const [lastPautaAt, setLastPautaAt] = useState<string | null>(null);

  // auth
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const me = await authAPI.getMe();
        if (!alive) return;
        setUser(me);
      } catch {
        authAPI.logout();
        router.replace("/auth/login");
        return;
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [router]);

  // carrega histórico de compliance quando tiver usuário
  useEffect(() => {
    if (!user) return;
    let alive = true;

    (async () => {
      try {
        setCompLoading(true);
        const rows: ComplianceHistoryItem[] = await complianceAPI.listMy();
        if (!alive) return;

        setCompCount(rows.length);

        if (rows.length) {
          const latest = [...rows].sort(
            (a, b) =>
              new Date(b.created_at).getTime() -
              new Date(a.created_at).getTime()
          )[0];
          setLastCompAt(latest.created_at);
        } else {
          setLastCompAt(null);
        }
      } catch (e) {
        console.error("Erro ao carregar histórico de compliance:", e);
        setCompCount(0);
        setLastCompAt(null);
      } finally {
        if (alive) setCompLoading(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, [user]);

  // carrega resumo de Pautas quando tiver usuário
  useEffect(() => {
    if (!user) return;
    let alive = true;

    (async () => {
      try {
        setPautasLoading(true);
        const data = await get<PautasListResponse>("/api/pautas");

        if (!alive) return;

        // total pode vir em `total` ou (fallback) pelo tamanho do array
        const total = Number(data?.total ?? data?.pautas?.length ?? 0);
        setPautasCount(total);

        if (data?.pautas?.length) {
          // o backend já retorna order by created_at desc; se não, garantimos
          const latest = [...data.pautas].sort(
            (a, b) =>
              new Date(b.created_at).getTime() -
              new Date(a.created_at).getTime()
          )[0];
          setLastPautaAt(latest?.created_at ?? null);
        } else {
          setLastPautaAt(null);
        }
      } catch (e) {
        console.error("Erro ao carregar resumo de pautas:", e);
        setPautasCount(0);
        setLastPautaAt(null);
      } finally {
        if (alive) setPautasLoading(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, [user]);

  if (loading) {
    return (
      <div className="dark bg-gray-900 min-h-screen flex items-center justify-center">
        <p className="text-white">Carregando...</p>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="p-6 text-white">
      <h1 className="text-2xl font-bold">
        Olá, {user.nome ?? user.email} 👋
      </h1>
      <p className="text-gray-400 mt-2">Bem-vinda ao seu dashboard.</p>

      {/* ===== Cards ===== */}
      <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Card de Compliance */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Scale className="w-5 h-5 text-cyan-400" />
              <h3 className="font-semibold">Compliance gerado</h3>
            </div>
            {compLoading && (
              <span className="text-xs text-gray-400">carregando…</span>
            )}
          </div>

          <div className="mt-4 flex items-end justify-between">
            <div>
              <div className="text-4xl font-bold text-cyan-400">
                {compCount}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {lastCompAt ? (
                  <span className="inline-flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    última: {new Date(lastCompAt).toLocaleString("pt-BR")}
                  </span>
                ) : (
                  "nenhuma análise ainda"
                )}
              </div>
            </div>

            <Link
              href="/dashboard/compliance"
              className="text-sm px-3 py-2 rounded border border-cyan-600 text-cyan-300 hover:bg-cyan-600/10 transition"
            >
              Abrir Compliance
            </Link>
          </div>
        </div>

        {/* ✅ Card de Pautas IA */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-cyan-400" />
              <h3 className="font-semibold">Pautas IA</h3>
            </div>
            {pautasLoading && (
              <span className="text-xs text-gray-400">carregando…</span>
            )}
          </div>

          <div className="mt-4 flex items-end justify-between">
            <div>
              <div className="text-4xl font-bold text-cyan-400">
                {pautasCount}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {lastPautaAt ? (
                  <span className="inline-flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    última: {new Date(lastPautaAt).toLocaleString("pt-BR")}
                  </span>
                ) : (
                  "nenhuma pauta ainda"
                )}
              </div>
            </div>

            <Link
              href="/dashboard/pautas"
              className="text-sm px-3 py-2 rounded border border-cyan-600 text-cyan-300 hover:bg-cyan-600/10 transition"
            >
              Abrir Pautas
            </Link>
          </div>
        </div>

        {/* …aqui podem ficar outros cards do dashboard… */}
      </div>
    </div>
  );
}
