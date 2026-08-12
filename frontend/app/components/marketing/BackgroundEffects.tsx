"use client"; // Executa no lado do cliente, necessário para usar hooks como useState

// Hooks do React e animações
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

export function BackgroundEffects() {
  // Estado que guarda as dimensões da tela (largura e altura)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  // Atualiza as dimensões da tela sempre que a janela for redimensionada
  useEffect(() => {
    const updateDimensions = () => {
      setDimensions({
        width: window.innerWidth,
        height: window.innerHeight
      });
    };

    updateDimensions(); // Atualiza ao montar
    window.addEventListener('resize', updateDimensions); // Escuta mudanças de tamanho
    return () => window.removeEventListener('resize', updateDimensions); // Limpa evento
  }, []);

  // Se ainda não tem dimensões, evita renderizar (evita bug visual em SSR)
  if (dimensions.width === 0) {
    return null;
  }

  return (
    // Container das partículas: ocupa toda a tela e fica no fundo (z-0)
    <div className="absolute inset-0 overflow-hidden z-0">
      {/* Cria 20 bolinhas animadas */}
      {Array.from({ length: 20 }).map(() => (
        <motion.div
          key={crypto.randomUUID()}
          className="absolute w-1 h-1 bg-cyan-400/30 rounded-full" // Bolinha azul transparente
          
          // Posição inicial aleatória
          initial={{
            x: Math.random() * dimensions.width,
            y: Math.random() * dimensions.height,
          }}

          // Anima a posição para novos pontos aleatórios
          animate={{
            x: [null, Math.random() * dimensions.width, Math.random() * dimensions.width],
            y: [null, Math.random() * dimensions.height, Math.random() * dimensions.height],
          }}

          // Controla duração e looping suave (espelhado)
          transition={{
            duration: Math.random() * 10 + 10,  // Entre 10s e 20s
            repeat: Infinity,
            repeatType: "mirror",
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}
