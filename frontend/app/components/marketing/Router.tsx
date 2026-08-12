"use client";

import React, {
  createContext,
  useContext,
  useState,
  useMemo,
  useCallback,
  useEffect,
  ReactNode,
} from "react";

/** ✅ Lista de páginas válidas; o tipo Page é derivado desta tupla */
const VALID_PAGES = ["home", "login", "forgot-password", "support"] as const;
type Page = (typeof VALID_PAGES)[number];

/** Contrato exposto pelo contexto do "roteador" */
interface RouterContextType {
  currentPage: Page;           // Página atual
  navigate: (page: Page) => void; // Função para trocar de página
}

/** Contexto em si (pode iniciar indefinido até o Provider ser montado) */
const RouterContext = createContext<RouterContextType | undefined>(undefined);

/** ✅ Props do Provider marcados como somente-leitura (resolve Sonar S6759) */
type RouterProviderProps = Readonly<{ children: ReactNode }>;

/** Helper: pega a página a partir do hash da URL (#login, #support, ...) */
function getPageFromHash(): Page {
  const raw = window.location.hash.replace(/^#/, "");
  return (VALID_PAGES as readonly string[]).includes(raw) ? (raw as Page) : "home";
}

/** 🌍 Provider que controla e disponibiliza a "rota" da sua SPA */
export function RouterProvider({ children }: RouterProviderProps) {
  /** Estado com a página atual (default = home) */
  const [currentPage, setCurrentPage] = useState<Page>("home");

  /** 🔄 Sincroniza com a URL:
   *  - ao montar, lê o hash inicial (#login, etc.)
   *  - escuta hashchange (back/forward do navegador) */
  useEffect(() => {
    const applyHash = () => setCurrentPage(getPageFromHash());
    applyHash(); // estado inicial vindo da URL
    window.addEventListener("hashchange", applyHash);
    return () => window.removeEventListener("hashchange", applyHash);
  }, []);

  /** 🚀 Navegação programática
   *  useCallback mantém a identidade estável (evita recriar a função) */
  const navigate = useCallback((page: Page) => {
    setCurrentPage(page);
    // Atualiza o hash da URL (suporta deep-link, refresh e compartilhamento)
    window.location.hash = page === "home" ? "" : page;
  }, []);

  /** 🧠 Memoiza o objeto de value (resolve Sonar S6481) */
  const value = useMemo<RouterContextType>(
    () => ({ currentPage, navigate }),
    [currentPage, navigate]
  );

  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
}

/** 🔌 Hook para consumir o roteador em qualquer componente filho */
export function useRouter(): RouterContextType {
  const ctx = useContext(RouterContext);
  if (!ctx) {
    throw new Error("useRouter must be used within a RouterProvider");
  }
  return ctx;
}
