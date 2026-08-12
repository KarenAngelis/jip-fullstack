"use client"; // Indica que esse componente é renderizado no lado do cliente (React Hooks requerem isso)

import React from 'react';
import { motion, useScroll, useTransform } from 'framer-motion'; // Animações de scroll e transições
import { Button } from '../ui/button'; // Botão customizado da sua UI
import {
  ArrowRight, Play, Rocket, ChevronDown,
  Users, Target, Zap
} from 'lucide-react'; // Ícones SVG minimalistas

export function HeroSection() {
  const { scrollYProgress } = useScroll(); // Progresso de rolagem da tela (0 a 1)

  // Escala e opacidade do título principal animados conforme o scroll
  const heroScale = useTransform(scrollYProgress, [0, 0.3], [1, 0.8]);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.2], [1, 0]);

  return (
    <section className="relative min-h-screen flex items-center justify-center pt-24 pb-12">
      <div className="text-center max-w-5xl mx-auto px-6 z-10">

        {/* Título principal com efeito visual de brilho e camadas */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8, y: 50 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 1.2, ease: [0.23, 1, 0.32, 1] }}
          className="relative mb-6"
          style={{ scale: heroScale, opacity: heroOpacity }}
        >
          {/* Fundo gradiente pulsante */}
          <div className="absolute inset-0 flex items-center justify-center">
            <motion.div
              className="w-[600px] h-[200px] bg-gradient-to-r from-cyan-500/20 via-blue-500/30 to-purple-500/20 rounded-full blur-3xl"
              animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.6, 0.3] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            />
          </div>

          {/* Camadas de texto sobrepostas para criar glow */}
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold mb-6 relative">
            <span className="bg-gradient-to-r from-cyan-300 via-blue-400 to-purple-400 bg-clip-text text-transparent drop-shadow-2xl">
              Just-in-point
            </span>
            <span className="absolute inset-0 text-5xl md:text-6xl lg:text-7xl font-bold text-cyan-400/30 blur-xl">
              Just-in-point
            </span>
            <span className="absolute inset-0 text-5xl md:text-6xl lg:text-7xl font-bold text-blue-400/20 blur-2xl scale-110">
              Just-in-point
            </span>
          </h1>

          {/* Linhas de feixe animadas girando ao redor do título */}
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -z-10">
            {[...Array(8)].map((_, i) => (
              <motion.div
                key={crypto.randomUUID()} // ✅ Correção real aplicada: chave única e segura
                className="absolute w-px h-32 bg-gradient-to-b from-transparent via-cyan-400/40 to-transparent"
                style={{ transform: `rotate(${i * 45}deg)`, transformOrigin: 'center' }}
                animate={{ opacity: [0.2, 0.8, 0.2], scaleY: [0.5, 1.5, 0.5] }}
                transition={{
                  duration: 3,
                  repeat: Infinity,
                  delay: i * 0.2,
                  ease: "easeInOut",
                }}
              />
            ))}
          </div>
        </motion.div>

        {/* Subtítulo + parágrafo auxiliar */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.3 }}
          className="mb-10"
        >
          <p className="text-2xl md:text-3xl text-gray-200 leading-relaxed max-w-4xl mx-auto font-light">
            Transformamos dados em{' '}
            <span className="text-transparent bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text font-semibold">
              autoridade digital
            </span>{' '}
            com inteligência artificial
          </p>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1, delay: 0.8 }}
            className="mt-6"
          >
            <p className="text-lg text-gray-400 font-light">
              Crie conteúdo que conecta, convence e conquista
            </p>
          </motion.div>
        </motion.div>

        {/* Botões de chamada para ação (CTAs) */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.6 }}
          className="flex flex-col sm:flex-row gap-6 justify-center items-center mb-16"
        >
          {/* Botão 1: Começar Agora */}
          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500 via-blue-600 to-purple-600 rounded-full blur opacity-60 group-hover:opacity-100 transition duration-1000 group-hover:duration-200 animate-pulse" />
            <Button
              size="lg"
              className="relative bg-gradient-to-r from-cyan-500 via-blue-600 to-purple-600 hover:from-cyan-400 hover:via-blue-500 hover:to-purple-500 text-white px-12 py-8 text-xl rounded-full border-0 overflow-hidden group"
            >
              <span className="relative z-10 flex items-center">
                <Rocket className="mr-3 h-6 w-6" />
                Começar Agora
                <ArrowRight className="ml-3 h-6 w-6 group-hover:translate-x-1 transition-transform" />
              </span>
            </Button>
          </motion.div>

          {/* Botão 2: Agendar Demo */}
          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="relative group">
            <Button
              variant="outline"
              size="lg"
              className="border-2 border-cyan-400/50 text-cyan-300 hover:bg-cyan-400/10 hover:border-cyan-300 px-10 py-8 text-lg rounded-full backdrop-blur-sm bg-black/20 relative overflow-hidden group"
            >
              <span className="relative z-10 flex items-center">
                <Play className="mr-3 h-5 w-5" />
                Agendar Demo
              </span>
              <motion.div
                className="absolute inset-0 bg-cyan-400/5 opacity-0 group-hover:opacity-100 rounded-full"
                transition={{ duration: 0.3 }}
              />
            </Button>
          </motion.div>
        </motion.div>

        {/* Prova social com ícones e texto */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 1 }}
          className="flex flex-wrap justify-center items-center gap-12 text-gray-300"
        >
          {[ 
            { icon: Users, text: "2.500+ Criadores", gradient: "from-cyan-400 to-blue-400" },
            { icon: Target, text: "98% Satisfação", gradient: "from-blue-400 to-purple-400" },
            { icon: Zap, text: "Resultados em 24h", gradient: "from-purple-400 to-cyan-400" }
          ].map((item) => (
            <motion.div
              key={item.text} // ✅ Correção mantida: chave segura e estável
              className="flex items-center gap-3 group"
              whileHover={{ scale: 1.05, y: -2 }}
              transition={{ duration: 0.2 }}
            >
              <div className="relative">
                <motion.div
                  className={`w-10 h-10 rounded-full bg-gradient-to-r ${item.gradient} p-2 group-hover:shadow-lg transition-all duration-300`}
                  whileHover={{ rotate: 360 }}
                  transition={{ duration: 0.6 }}
                >
                  <item.icon className="h-full w-full text-white" />
                </motion.div>
              </div>
              <span className="text-lg group-hover:text-white transition-colors">
                {item.text}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* Indicador de scroll animado */}
      <motion.div
        className="absolute bottom-8 left-1/2 transform -translate-x-1/2"
        animate={{ y: [0, 10, 0] }}
        transition={{ duration: 2, repeat: Infinity }}
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: false }}
      >
        <div className="flex flex-col items-center text-gray-500 group cursor-pointer">
          <motion.span
            className="text-sm mb-3 group-hover:text-cyan-400 transition-colors"
            whileHover={{ scale: 1.1 }}
          >
            Descubra mais
          </motion.span>
          <div className="relative">
            <ChevronDown className="h-8 w-8 group-hover:text-cyan-400 transition-colors" />
            <motion.div
              className="absolute inset-0 text-cyan-400/50 blur-sm"
              animate={{ opacity: [0, 0.8, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <ChevronDown className="h-8 w-8" />
            </motion.div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
