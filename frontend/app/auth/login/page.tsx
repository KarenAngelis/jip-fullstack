// app/auth/login/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { LoginForm } from "../components/LoginForm";
import { BackgroundEffects } from "@/app/components/marketing/BackgroundEffects";
import { authAPI } from "@/lib/api";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
const ME_URL = `${API_BASE}/api/auth/me`;

export default function LoginPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let cancel = false;

    // 🔧 remove chave legada que causava loop
    if (typeof window !== "undefined") {
      localStorage.removeItem("authToken");
    }

    (async () => {
      try {
        // ✅ usa a mesma chave do restante do app
        const lsToken =
          typeof window !== "undefined"
            ? localStorage.getItem("access_token")
            : null;
        const cookieToken = Cookies.get("access_token");
        const token = lsToken || cookieToken || null;

        if (!token) {
          setChecking(false);
          return;
        }

        // ✅ valida o token no backend antes de redirecionar
        const r = await fetch(ME_URL, {
          method: "GET",
          headers: { Authorization: `Bearer ${token}` },
          cache: "no-store",
        });

        if (cancel) return;

        if (r.ok) {
          router.replace("/dashboard");
        } else {
          // ❌ inválido → limpa tudo e permanece na tela de login
          authAPI.logout(); // remove cookies/localStorage e header global
          setChecking(false);
        }
      } catch {
        authAPI.logout();
        setChecking(false);
      }
    })();

    return () => {
      cancel = true;
    };
  }, [router]);

  if (checking) {
    return (
      <div className="dark bg-gray-900 min-h-screen grid place-items-center">
        <p className="text-white/80">Verificando sessão…</p>
      </div>
    );
  }

  return (
    <div className="dark flex items-center justify-center min-h-screen bg-background text-foreground">
      <BackgroundEffects />
      <main className="z-10">
        <LoginForm />
      </main>
    </div>
  );
}
