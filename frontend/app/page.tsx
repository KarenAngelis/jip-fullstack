// src/app/page.tsx
import Link from "next/link";
import { HeroSection } from "./components/marketing/HeroSection";
import { Navigation } from "./components/marketing/Navigation";
import { BackgroundEffects } from "./components/marketing/BackgroundEffects";
import { Button } from "./components/ui/button";
import { TrendingUp, Search, Zap, Target, BarChart3, Lightbulb, Scale } from "lucide-react";

export default function HomePage() {
  return (
    <main className="dark bg-background text-foreground">
      <BackgroundEffects />
      <Navigation />
      <HeroSection />

      {/* Acesso rápido */}
      <section className="relative z-10 py-16 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-4">Acesse o Dashboard</h2>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">
              Gerencie suas pautas de podcast com IA e explore tendências em tempo real
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {/* Dashboard */}
            <Link href="/dashboard" prefetch={false} className="group">
              <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 hover:bg-gray-800/70 transition-all hover:border-blue-500">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-blue-600/20 rounded-lg">
                    <BarChart3 className="w-6 h-6 text-blue-400" />
                  </div>
                  <h3 className="text-xl font-semibold text-white">Dashboard</h3>
                </div>
                <p className="text-gray-400 mb-4">Visão geral das suas pautas e métricas</p>
                <div className="text-blue-400 font-medium group-hover:text-blue-300">Acessar →</div>
              </div>
            </Link>

            {/* Pesquisa & Insights (aponta para buscar-tendencias) */}
            <Link href="/dashboard/buscar-tendencias" prefetch={false} className="group">
              <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 hover:bg-gray-800/70 transition-all hover:border-green-500">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-green-600/20 rounded-lg">
                    <Search className="w-6 h-6 text-green-400" />
                  </div>
                  <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                    Pesquisa & Insights
                  </h3>
                </div>
                <p className="text-gray-400 mb-4">Descubra tendências e oportunidades</p>
                <div className="text-green-400 font-medium group-hover:text-green-300">Explorar →</div>
              </div>
            </Link>

            {/* Geração de Pautas */}
            <Link href="/dashboard/pautas" prefetch={false} className="group">
              <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 hover:bg-gray-800/70 transition-all hover:border-purple-500">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-purple-600/20 rounded-lg">
                    <Lightbulb className="w-6 h-6 text-purple-400" />
                  </div>
                  <h3 className="text-xl font-semibold text-white">Gerar Pautas</h3>
                </div>
                <p className="text-gray-400 mb-4">Crie pautas completas com IA</p>
                <div className="text-purple-400 font-medium group-hover:text-purple-300">Criar →</div>
              </div>
            </Link>

            {/* Compliance */}
            <Link href="/dashboard/compliance" prefetch={false} className="group md:col-span-2 lg:col-span-1">
              <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 hover:bg-gray-800/70 transition-all hover:border-cyan-500">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-cyan-600/20 rounded-lg">
                    <Scale className="w-6 h-6 text-cyan-400" />
                  </div>
                  <h3 className="text-xl font-semibold text-white">Compliance</h3>
                </div>
                <p className="text-gray-400 mb-4">Verifique a conformidade legal do seu conteúdo</p>
                <div className="text-cyan-400 font-medium group-hover:text-cyan-300">Analisar →</div>
              </div>
            </Link>
          </div>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/dashboard/buscar-tendencias" prefetch={false}>
              <Button size="lg" className="bg-blue-600 hover:bg-blue-700 w-full sm:w-auto">
                <Search className="w-5 h-5 mr-2" />
                Pesquisar Tendências
              </Button>
            </Link>

            <Link href="/dashboard/compliance" prefetch={false}>
              <Button size="lg" variant="outline" className="border-cyan-400 text-cyan-300 hover:bg-gray-800 w-full sm:w-auto">
                <Scale className="w-5 h-5 mr-2" />
                Analisar Compliance
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Funcionalidades */}
      <section className="relative z-10 py-16 px-4 bg-gray-900/30">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-4">Funcionalidades Poderosas</h2>
            <p className="text-gray-400 text-lg">Tudo que você precisa para criar conteúdo de qualidade</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600/20 rounded-full mb-4">
                <TrendingUp className="w-8 h-8 text-blue-400" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-3">Análise de Tendências</h3>
              <p className="text-gray-400">
                Descubra tópicos em alta com dados reais de volume de busca e crescimento
              </p>
            </div>

            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-purple-600/20 rounded-full mb-4">
                <Zap className="w-8 h-8 text-purple-400" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-3">IA Generativa</h3>
              <p className="text-gray-400">
                Gere pautas completas, roteiros e insights automaticamente com inteligência artificial
              </p>
            </div>

            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-green-600/20 rounded-full mb-4">
                <Target className="w-8 h-8 text-green-400" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-3">Oportunidades</h3>
              <p className="text-gray-400">
                Identifique nichos com baixa competição e alto potencial de engajamento
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="relative z-10 py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-12">Dados em Tempo Real</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-gray-800/30 rounded-xl p-6 border border-gray-700">
              <div className="text-3xl font-bold text-blue-400 mb-2">10M+</div>
              <div className="text-gray-300 font-medium mb-1">Buscas Analisadas</div>
              <div className="text-gray-500 text-sm">Dados atualizados diariamente</div>
            </div>

            <div className="bg-gray-800/30 rounded-xl p-6 border border-gray-700">
              <div className="text-3xl font-bold text-green-400 mb-2">1000+</div>
              <div className="text-gray-300 font-medium mb-1">Pautas Geradas</div>
              <div className="text-gray-500 text-sm">Com score de viabilidade</div>
            </div>

            <div className="bg-gray-800/30 rounded-xl p-6 border border-gray-700">
              <div className="text-3xl font-bold text-purple-400 mb-2">50+</div>
              <div className="text-gray-300 font-medium mb-1">Categorias</div>
              <div className="text-gray-500 text-sm">Tecnologia, educação, finanças...</div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA final */}
      <section className="relative z-10 py-16 px-4 bg-gradient-to-r from-blue-600/20 to-purple-600/20">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Pronto para Criar Conteúdo de Alto Impacto?</h2>
          <p className="text-gray-300 text-lg mb-8 max-w-2xl mx-auto">
            Junte-se aos criadores que já estão usando IA para descobrir as melhores oportunidades de conteúdo
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/dashboard/buscar-tendencias" prefetch={false}>
              <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3">
                Começar Agora
              </Button>
            </Link>
            <Link href="/dashboard/compliance" prefetch={false}>
              <Button
                variant="outline"
                size="lg"
                className="border-gray-400 text-gray-300 hover:bg-gray-800 px-8 py-3"
              >
                Ver Compliance
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
