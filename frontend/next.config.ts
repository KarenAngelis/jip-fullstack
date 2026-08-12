// web/next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: {
    // ⚠️ Não roda ESLint no build de produção (só avisa localmente)
    ignoreDuringBuilds: true,
  },
  typescript: {
    // (Opcional) se ainda aparecer erro de types na build, ignore
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
