// Ativa o modo "cliente" no Next.js (necessário para usar hooks)
"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Eye, EyeOff, Mail, Lock, ArrowRight } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Card } from "../../components/ui/card";

// ✅ use o SDK centralizado (faz login, salva cookie/localStorage e seta Authorization)
import { authAPI } from "@/lib/api";;

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      await authAPI.login({ email: email.trim(), password });
      router.push("/dashboard");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Ocorreu um erro inesperado."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, ease: "easeOut" }}
      className="w-full max-w-md mx-auto"
    >
      <Card className="bg-black/40 backdrop-blur-xl border-cyan-400/20 shadow-2xl shadow-cyan-400/10">
        <div className="p-8">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent mb-2">
              Bem-vindo de volta
            </h2>
            <p className="text-gray-400">Entre na sua conta para continuar</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <Label htmlFor="email" className="text-gray-300 mb-2 block">
                Email
              </Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-cyan-400 w-5 h-5" />
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10 h-12 bg-black/30 border-cyan-400/30 text-white placeholder-gray-500 focus:border-cyan-400 transition-all duration-300"
                  placeholder="seu@email.com"
                  required
                />
              </div>
            </div>

            <div>
              <Label htmlFor="password" className="text-gray-300 mb-2 block">
                Senha
              </Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-cyan-400 w-5 h-5" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 pr-10 h-12 bg-black/30 border-cyan-400/30 text-white placeholder-gray-500 focus:border-cyan-400 transition-all duration-300"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-cyan-400 transition-colors"
                  aria-label={showPassword ? "Esconder senha" : "Mostrar senha"}
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center text-gray-400 cursor-pointer">
                <input
                  type="checkbox"
                  className="mr-2 h-4 w-4 rounded bg-black/30 border-cyan-400/50 text-cyan-400 focus:ring-cyan-400"
                />
                Lembrar de mim
              </label>
              <Link href="/recuperar-senha" className="text-cyan-400 hover:text-cyan-300 transition-colors">
                Esqueceu a senha?
              </Link>
            </div>

            {error && <p className="text-sm text-red-400 text-center">{error}</p>}

            <div>
              <Button
                type="submit"
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white font-bold h-12 rounded-lg group transition-all duration-300 transform hover:scale-[1.02]"
              >
                {isLoading ? (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                  />
                ) : (
                  <>
                    Entrar
                    <ArrowRight className="ml-2 w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </>
                )}
              </Button>
            </div>
          </form>

          <div className="mt-8 text-center">
            <p className="text-gray-400">
              Não tem uma conta?{" "}
              {/* <Link href="/register">Cadastrar</Link> */}
            </p>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
