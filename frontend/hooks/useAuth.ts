// src/hooks/useAuth.ts
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { authAPI, type User } from "@/lib/api";

type Opts = { redirectIfUnauthed?: boolean };

export function useAuth(opts: Opts = {}) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    (async () => {
      try {
        // ✅ checa cookie OU localStorage antes de chamar /me
        const token =
          Cookies.get("access_token") ||
          (typeof window !== "undefined" ? localStorage.getItem("access_token") : null);

        if (!token) {
          if (opts.redirectIfUnauthed) {
            authAPI.logout();                 // limpa tokens/header
            router.replace("/auth/login");    // path correto
          }
          return;
        }

        // ✅ token existe → valida com a API
        const me = await authAPI.getMe();
        if (!mounted) return;
        setUser(me);
      } catch {
        authAPI.logout();
        if (opts.redirectIfUnauthed) router.replace("/auth/login");
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => {
      mounted = false;
    };
  }, [router, opts.redirectIfUnauthed]);

  return { user, loading, isAuthenticated: !!user };
}
