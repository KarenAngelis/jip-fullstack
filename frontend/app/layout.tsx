// src/app/layout.tsx
import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "JIP Content",
  description: "Do dado bruto ao conteúdo publicável com IA + Compliance",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className="dark">
      {}
      <body>
        {children}
      </body>
    </html>
  );
}
