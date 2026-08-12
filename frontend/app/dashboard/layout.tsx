// src/app/dashboard/layout.tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { Sidebar } from "./components/Sidebar";
import { Header } from "./components/Header";
import { authAPI, type User } from "@/lib/api";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();

  // UI
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Auth state
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);

  // Guards p/ evitar loops / updates após unmount
  const redirected = useRef(false);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;

    const verify = async () => {
      try {
        // 1) Curto-circuito: sem token → não chama /me
        const token =
          Cookies.get("access_token") ||
          (typeof window !== "undefined"
            ? localStorage.getItem("access_token")
            : null);

        if (!token) {
          if (!redirected.current) {
            redirected.current = true;
            authAPI.logout(); // limpeza local defensiva
            router.replace("/auth/login");
          }
          // garante que o spinner pare nessa branch
          if (alive.current) setChecking(false);
          return;
        }

        // 2) Com token → valida no backend
        const me = await authAPI.getMe();
        if (!alive.current) return;
        setUser(me);
      } catch {
        // 3) Token inválido/expirado → limpa e manda pro login (1x só)
        if (!redirected.current) {
          redirected.current = true;
          authAPI.logout();
          router.replace("/auth/login");
        }
      } finally {
        if (alive.current) setChecking(false);
      }
    };

    verify();

    return () => {
      alive.current = false;
    };
  }, [router]);

  if (checking) {
    return (
      <div className="dark bg-gray-900 min-h-screen flex items-center justify-center">
        <p className="text-white">Carregando…</p>
      </div>
    );
  }

  // Se não há usuário, já redirecionamos acima — evita flicker/layout vazio
  if (!user) return null;

  return (
    <div className="dark flex min-h-screen bg-gray-900 text-gray-200">
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen((v) => !v)} />
      <div className="flex-1 flex flex-col">
        <Header user={user} />
        <main className="flex-1 p-6 lg:p-8 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
