// Ativa o modo client-side (necessário para usar hooks do React no Next.js)
"use client";

// Hooks e ícones
import { useState } from "react";
import { Eye, EyeOff, Mail, Lock, User, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

// Componente de página de cadastro
export default function RegisterPage() {
  const router = useRouter();

  // Estado principal do formulário
  const [formData, setFormData] = useState({
    nome: "",
    email: "",
    password: "",
    confirmPassword: "",
    terms: false,
  });

  // Estados auxiliares
  const [showPassword, setShowPassword] = useState(false);           // Mostrar/ocultar senha
  const [showConfirmPassword, setShowConfirmPassword] = useState(false); // Mostrar/ocultar confirmação
  const [error, setError] = useState<string>("");                    // Mensagem de erro
  const [loading, setLoading] = useState(false);                    // Loading do botão

  // Atualiza estado do formulário conforme digita ou clica
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value
    }));
  };

  // Lida com envio do formulário
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");

    // ⚠️ Validações manuais rápidas
    if (formData.password !== formData.confirmPassword) {
      setError("As senhas não coincidem");
      return;
    }
    if (formData.password.length < 6) {
      setError("A senha deve ter pelo menos 6 caracteres");
      return;
    }
    if (!formData.terms) {
      setError("Você deve aceitar os termos de uso");
      return;
    }

    setLoading(true);

    try {
      // 🔗 Define URL da API (ajusta se houver barra no final)
      const base = (process.env.NEXT_PUBLIC_API_URL || "https://jip-api-1.onrender.com").replace(/\/$/, "");

      // 📨 Envia requisição para cadastrar usuário
      const resp = await fetch(`${base}/api/auth/register`, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          nome: formData.nome || undefined
        })
      });

      // ❌ Trata erro de API
      if (!resp.ok) {
        let msg = "Erro ao criar conta";
        try {
          const data = await resp.json();
          if (typeof data?.detail === "string") msg = data.detail;
          else if (Array.isArray(data?.detail)) msg = "Por favor, verifique os campos informados.";
        } catch {
          /* mantém mensagem padrão */
        }
        throw new Error(msg);
      }

      // ✅ Sucesso → redireciona para login
      router.push("/auth/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro inesperado ao criar conta.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      {/* 🌌 Efeitos visuais de fundo (esferas com blur colorido) */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-4 -left-4 w-24 h-24 bg-cyan-500/20 rounded-full blur-xl" />
        <div className="absolute top-1/3 -right-4 w-32 h-32 bg-blue-500/20 rounded-full blur-xl" />
        <div className="absolute bottom-1/4 left-1/4 w-20 h-20 bg-purple-500/20 rounded-full blur-xl" />
      </div>

      {/* 🧾 Cartão do formulário */}
      <div className="relative w-full max-w-md">
        <div className="bg-gray-800/80 backdrop-blur-sm border border-gray-700 rounded-2xl p-8 shadow-2xl">
          {/* 🧩 Cabeçalho do formulário */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-transparent bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text">
              Criar Conta
            </h1>
            <p className="text-gray-400 mt-2">Junte-se à nossa plataforma de IA</p>
          </div>

          {/* 🔥 Exibe erro, se existir */}
          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* 🧾 FORMULÁRIO */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Nome */}
            <div>
              <label htmlFor="nome" className="block text-sm font-medium text-gray-300 mb-2">
                Nome (opcional)
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  id="nome"
                  name="nome"
                  value={formData.nome}
                  onChange={handleChange}
                  placeholder="Seu nome"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-4 py-3 text-white focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
                />
              </div>
            </div>

            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="seu@email.com"
                  required
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-4 py-3 text-white focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
                />
              </div>
            </div>

            {/* Senha */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                Senha
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type={showPassword ? "text" : "password"}
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  required
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-12 py-3 text-white focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 hover:text-gray-300 transition-colors"
                >
                  {showPassword ? <EyeOff /> : <Eye />}
                </button>
              </div>
            </div>

            {/* Confirmar Senha */}
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-2">
                Confirmar Senha
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  id="confirmPassword"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="••••••••"
                  required
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-12 py-3 text-white focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 hover:text-gray-300 transition-colors"
                >
                  {showConfirmPassword ? <EyeOff /> : <Eye />}
                </button>
              </div>
            </div>

            {/* Aceite de Termos */}
            <div className="flex items-start">
              <input
                type="checkbox"
                id="terms"
                name="terms"
                checked={formData.terms}
                onChange={handleChange}
                className="h-4 w-4 mt-1 rounded border-gray-600 bg-gray-700 text-cyan-500 focus:ring-cyan-500/20 focus:ring-2"
              />
              <label htmlFor="terms" className="ml-3 text-sm text-gray-300">
                Eu aceito os{" "}
                <Link href="/terms" className="text-cyan-400 hover:text-cyan-300 transition-colors">
                  Termos de Uso
                </Link>{" "}
                e{" "}
                <Link href="/privacy" className="text-cyan-400 hover:text-cyan-300 transition-colors">
                  Política de Privacidade
                </Link>
              </label>
            </div>

            {/* Botão de enviar */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-cyan-500 to-blue-500 text-white py-3 px-4 rounded-lg font-medium hover:from-cyan-600 hover:to-blue-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Criando conta...
                </>
              ) : (
                "Criar Conta"
              )}
            </button>
          </form>

          {/* Link para login */}
          <div className="text-center mt-8 pt-6 border-t border-gray-700">
            <p className="text-gray-400">
              Já tem uma conta?{" "}
              <Link href="/auth/login" className="text-cyan-400 hover:text-cyan-300 transition-colors font-medium">
                Entrar
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
