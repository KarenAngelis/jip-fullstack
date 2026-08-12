"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Button } from "../ui/button";
import { Menu, X, LogIn } from "lucide-react";
import { useRouter } from "next/navigation";
import Link from "next/link";

// 📷 Importa o Image do Next e o arquivo do logo
import Image from "next/image";
import logoIcon from "@/assets/4.png"; // ✅ caminho conferido

// 🧭 Barra de navegação principal
export function Navigation() {
  // Estado para aplicar fundo quando a página rola
  const [isScrolled, setIsScrolled] = useState(false);
  // Estado do menu mobile (aberto/fechado)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  // Router do Next para navegação programática
  const router = useRouter();

  // 🔎 Observa o scroll da página para estilizar o nav
  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 50);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Links do menu (desktop e mobile)
  const navItems = [
    { name: "Tendências", href: "#tendencias" },
    { name: "Deep Research", href: "#pesquisa" },
    { name: "Compliance", href: "#compliance" },
    { name: "Preços", href: "#precos" },
  ];

  // Faz scroll suave para a seção e fecha o menu mobile
  const handleNavClick = (href: string) => {
    const el = document.querySelector(href);
    if (el) el.scrollIntoView({ behavior: "smooth" });
    setIsMobileMenuOpen(false);
  };

  return (
    <>
      {/* 🔝 Navbar fixa no topo com animação de entrada */}
      <motion.nav
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8, ease: [0.23, 1, 0.32, 1] }}
        className={`fixed top-0 w-full z-50 transition-all duration-500 ${
          isScrolled
            ? "bg-black/80 backdrop-blur-xl border-b border-cyan-500/20"
            : "bg-transparent"
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            {/* 🔗 Logo (volta ao topo ao clicar) */}
            <motion.div
              whileHover={{ scale: 1.05 }}
              className="flex items-center cursor-pointer"
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
            >
              <div className="relative">
                <motion.div whileHover={{ rotate: 360 }} transition={{ duration: 0.8 }}>
                  <Image
                    src={logoIcon}
                    alt="JIP Icon"
                    width={80}
                    height={80}
                    priority // carrega rápido
                  />
                </motion.div>

                {/* Glow atrás do logo */}
                <motion.div
                  className="absolute inset-0 bg-gradient-to-r from-cyan-500 via-blue-600 to-purple-600 rounded-full opacity-50 blur-lg"
                  animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.6, 0.3] }}
                  transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                />
              </div>
            </motion.div>

            {/* 🖥️ Menu Desktop */}
            <div className="hidden lg:flex items-center space-x-8">
              {navItems.map((item, index) => (
                <motion.button
                  key={item.name} // ✅ chave estável
                  onClick={() => handleNavClick(item.href)}
                  className="text-gray-300 hover:text-cyan-400 transition-colors duration-300 relative group px-3 py-2"
                  whileHover={{ scale: 1.05 }}
                  initial={{ opacity: 0, y: -20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                >
                  {item.name}
                  {/* sublinhado animado */}
                  <motion.div
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-cyan-400 to-blue-400 scale-x-0 group-hover:scale-x-100 transition-transform duration-300"
                    initial={{ scaleX: 0 }}
                  />
                </motion.button>
              ))}
            </div>

            {/* 🔐 CTA Desktop (Login) */}
            <div className="hidden lg:flex items-center">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="relative group">
                <Button
                  variant="outline"
                  onClick={() => router.push("/auth/login")}
                  className="border-2 border-cyan-400/50 text-cyan-300 hover:bg-cyan-400/10 hover:border-cyan-300 px-6 py-2 rounded-full backdrop-blur-sm bg-black/20 relative overflow-hidden group"
                >
                  <span className="relative z-10 flex items-center">
                    <LogIn className="mr-2 h-4 w-4" />
                    Login
                  </span>
                </Button>
              </motion.div>
            </div>

            {/* 📱 Botão que abre/fecha o menu mobile */}
            <motion.button
              className="lg:hidden p-2 text-gray-300 hover:text-cyan-400 transition-colors"
              onClick={() => setIsMobileMenuOpen((v) => !v)}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              aria-label={isMobileMenuOpen ? "Fechar menu" : "Abrir menu"}
            >
              {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </motion.button>
          </div>
        </div>
      </motion.nav>

      {/* 📱 Menu Mobile deslizante */}
      <motion.div
        initial={{ opacity: 0, x: "100%" }}
        animate={{
          opacity: isMobileMenuOpen ? 1 : 0,
          x: isMobileMenuOpen ? "0%" : "100%",
        }}
        transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
        className={`fixed inset-0 z-40 lg:hidden ${
          isMobileMenuOpen ? "pointer-events-auto" : "pointer-events-none"
        }`}
      >
        {/* overlay */}
        <div className="absolute inset-0 bg-black/80 backdrop-blur-xl" />

        {/* conteúdo do menu */}
        <div className="relative h-full flex flex-col justify-center items-center space-y-8 px-6">
          {navItems.map((item, index) => (
            <motion.button
              key={item.name} // ✅ chave estável
              onClick={() => handleNavClick(item.href)}
              className="text-2xl text-gray-300 hover:text-cyan-400 transition-colors duration-300"
              initial={{ opacity: 0, y: 50 }}
              animate={{
                opacity: isMobileMenuOpen ? 1 : 0,
                y: isMobileMenuOpen ? 0 : 50,
              }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
            >
              {item.name}
            </motion.button>
          ))}

          {/* 🔐 CTA Mobile (Login) — ✅ sem asChild, sem Link envolvendo Button */}
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{
              opacity: isMobileMenuOpen ? 1 : 0,
              y: isMobileMenuOpen ? 0 : 50,
            }}
            transition={{ duration: 0.3, delay: navItems.length * 0.1 }}
            className="pt-8"
          >
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setIsMobileMenuOpen(false); // fecha menu
                router.push("/auth/login"); // navega
              }}
              className="border-2 border-cyan-400/50 text-cyan-300 hover:bg-cyan-400/10 hover:border-cyan-300 px-8 py-3 rounded-full backdrop-blur-sm bg-black/20 text-lg"
              aria-label="Ir para a página de login"
            >
              <LogIn className="mr-2 h-5 w-5" />
              <span>Login</span>
            </Button>
          </motion.div>

          {/* opcional: link “voltar”/“termos” etc. */}
          <Link
            href="/"
            className="text-sm text-gray-400 hover:text-gray-200 transition-colors mt-4"
            onClick={() => setIsMobileMenuOpen(false)}
          >
            Voltar para a Home
          </Link>
        </div>
      </motion.div>
    </>
  );
}
