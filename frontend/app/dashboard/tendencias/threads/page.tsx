"use client";

import { useEffect, useState, FormEvent } from "react";
import { Search, Heart, MessageCircle, Link as LinkIcon } from "lucide-react";

type ThreadsPost = {
  id: string;
  username: string;
  text: string;
  media_type: "IMAGE" | "TEXT";
  media_url: string;
  permalink: string;
  like_count: number;
  reply_count: number;
  quotes_count: number;
  engagement_rate: number;
  is_reply: boolean;
  timestamp: string;
  cached: boolean;
};

export default function ThreadsTrendsPage() {
  const [posts, setPosts] = useState<ThreadsPost[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const fetchThreadsTrends = async (searchQuery: string) => {
    setIsLoading(true);
    setError(null);
    setPosts([]);
    try {
  const encodedQuery = encodeURIComponent(searchQuery);
  const base = (process.env.NEXT_PUBLIC_API_URL || 'https://jip-api-1.onrender.com').replace(/\/$/, '');
  const response = await fetch(`${base}/api/threads/trends?query=${encodedQuery}`);
  if (!response.ok) throw new Error("Falha ao carregar dados da API.");
  const data = await response.json();
  setPosts(data.posts);
} catch (err) {
  if (err instanceof Error) setError(err.message);
  else setError("Ocorreu um erro desconhecido.");
  console.error("Erro ao buscar dados do Threads:", err);
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
    fetchThreadsTrends(query);
  };

  return (
    <div className="flex-1 p-6 lg:p-8 overflow-y-auto">
      <h1 className="text-3xl font-semibold mb-2 text-white">
        Tendências do Threads
      </h1>
      <p className="text-gray-400 mb-6">
        Busque posts populares sobre o seu nicho.
      </p>

      {/* Campo de Busca */}
      <form onSubmit={handleSubmit} className="mb-8 flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ex: 'inteligência artificial', 'empreendedorismo'"
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
          <p className="text-gray-500">Carregando posts...</p>
        </div>
      )}

      {error && (
        <div className="flex justify-center items-center h-64">
          <p className="text-red-500">{error}</p>
        </div>
      )}

      {!isLoading && !error && posts.length === 0 && (
        <div className="flex justify-center items-center h-64">
          <p className="text-gray-500">
            Nenhum post encontrado. Tente buscar um novo nicho.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {posts.map((post) => (
          <a
            key={post.id}
            href={post.permalink}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-gray-800 rounded-lg p-5 shadow-sm hover:bg-gray-700 transition-colors flex flex-col justify-between"
          >
            <div>
              <p className="text-sm font-bold text-cyan-400 mb-2">
                @{post.username}
              </p>
              <p className="text-gray-200">{post.text}</p>
              {post.media_type === "IMAGE" && post.media_url && (
                <img
                  src={post.media_url}
                  alt="Post media"
                  className="mt-4 rounded-lg w-full h-auto object-cover"
                />
              )}
            </div>
            <div className="mt-4 flex items-center justify-between text-sm text-gray-400">
              <span className="flex items-center gap-1">
                <Heart className="h-4 w-4" /> {post.like_count}
              </span>
              <span className="flex items-center gap-1">
                <MessageCircle className="h-4 w-4" /> {post.reply_count}
              </span>
              <span className="flex items-center gap-1">
                <LinkIcon className="h-4 w-4" /> {post.quotes_count}
              </span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
