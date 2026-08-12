"use client";

import { useEffect, useState, FormEvent } from "react";
import { ChevronRight, Search } from "lucide-react";

type YouTubeVideo = {
  title: string;
  channel_name: string;
  url: string;
};

export default function TrendsPage() {
  const [videos, setVideos] = useState<YouTubeVideo[]>([]);
  const [isLoading, setIsLoading] = useState(false); // Definido como false para não carregar na primeira renderização
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const fetchYouTubeTrends = async (searchQuery: string) => {
    setIsLoading(true);
    setError(null);
    setVideos([]); // Limpar vídeos anteriores
    try {
      const encodedQuery = encodeURIComponent(searchQuery);
      const base = (process.env.NEXT_PUBLIC_API_URL || 'https://jip-api-1.onrender.com').replace(/\/$/, '');
      const url = `${base}/api/youtube/trends?q=${encodedQuery}`;

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error("Falha ao carregar dados da API.");
      }
      const data = await response.json();
      setVideos(data.videos);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Ocorreu um erro desconhecido.");
      }
      console.error("Erro ao buscar dados do YouTube:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (query.trim() === "") {
      setError("Por favor, digite uma palavra-chave para buscar.");
      return;
    }
    fetchYouTubeTrends(query);
  };

  return (
    <div className="flex-1 p-6 lg:p-8 overflow-y-auto">
      <h1 className="text-3xl font-semibold mb-2 text-white">Tendências do YouTube</h1>
      <p className="text-gray-400 mb-6">
        Busque vídeos populares sobre o seu nicho.
      </p>

      {/* Campo de Busca */}
      <form onSubmit={handleSubmit} className="mb-8 flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ex: 'marketing digital', 'desenvolvimento web'"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-cyan-500"
          />
        </div>
        <button
          type="submit"
          className="bg-cyan-600 hover:bg-cyan-500 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
        >
          Buscar
        </button>
      </form>

      {/* Exibição dos dados */}
      {isLoading && (
        <div className="flex justify-center items-center h-64">
          <p className="text-gray-500">Carregando vídeos...</p>
        </div>
      )}

      {error && (
        <div className="flex justify-center items-center h-64">
          <p className="text-red-500">{error}</p>
        </div>
      )}

      {!isLoading && !error && videos.length === 0 && (
        <div className="flex justify-center items-center h-64">
          <p className="text-gray-500">Nenhum vídeo encontrado. Tente buscar um novo nicho.</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {videos.map((video, index) => (
          <a
            key={index}
            href={video.url}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-gray-800 rounded-lg p-5 shadow-sm hover:bg-gray-700 transition-colors flex flex-col justify-between"
          >
            <div>
              <h2 className="text-lg font-bold text-white mb-2">{video.title}</h2>
              <p className="text-sm text-gray-400">
                Canal: <span className="font-semibold">{video.channel_name}</span>
              </p>
            </div>
            <div className="mt-4 flex items-center gap-1 text-sm text-cyan-400">
              Ver no YouTube
              <ChevronRight className="h-4 w-4" />
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
