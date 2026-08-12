// hooks/usePreviewData.js
import { useState, useEffect } from 'react';

export const usePreviewData = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPreview = async (tema, incluirNoticias = true, duracaoMinutos = 15) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/pautas/preview', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tema,
          incluir_dados_tendencia: incluirNoticias,
          duracao_minutos: duracaoMinutos,
          use_gpt_insights: true
        })
      });

      if (!response.ok) {
        throw new Error(`Erro ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result);
      
      return result;
    } catch (err) {
      setError(err.message);
      console.error('Erro ao buscar preview:', err);
    } finally {
      setLoading(false);
    }
  };

  return {
    data,
    loading,
    error,
    fetchPreview
  };
};

// components/PreviewResultCard.jsx
import React from 'react';
import { TrendingUp, Clock, Target, Zap, Star, ArrowUp } from 'lucide-react';

export const PreviewResultCard = ({ data }) => {
  if (!data) return null;

  const getScoreColor = (score) => {
    if (score >= 85) return 'text-green-600 bg-green-50 border-green-200';
    if (score >= 65) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-red-600 bg-red-50 border-red-200';
  };

  const getDifficultyColor = (difficulty) => {
    switch (difficulty.toLowerCase()) {
      case 'easy': return 'bg-green-100 text-green-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'hard': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header com Score */}
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xl font-bold text-gray-900 mb-1">{data.tema}</h3>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              {data.categoria}
            </span>
          </div>
          
          <div className={`text-center px-4 py-2 rounded-lg border ${getScoreColor(data.viabilidade_score)}`}>
            <div className="text-2xl font-bold">{data.viabilidade_score}</div>
            <div className="text-xs font-medium">Score</div>
          </div>
        </div>
        
        <p className="mt-3 text-sm font-medium text-gray-700">
          {data.oportunidade.label}
        </p>
      </div>

      {/* Métricas Principais */}
      <div className="p-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="text-center">
            <div className="flex items-center justify-center w-10 h-10 bg-blue-100 rounded-lg mx-auto mb-2">
              <TrendingUp className="w-5 h-5 text-blue-600" />
            </div>
            <div className="text-xl font-bold text-gray-900">+{data.trend_growth_pct}%</div>
            <div className="text-xs text-gray-600">Crescimento</div>
          </div>
          
          <div className="text-center">
            <div className="flex items-center justify-center w-10 h-10 bg-green-100 rounded-lg mx-auto mb-2">
              <Target className="w-5 h-5 text-green-600" />
            </div>
            <div className="text-xl font-bold text-gray-900">{data.volume_estimado.toLocaleString()}</div>
            <div className="text-xs text-gray-600">Volume</div>
          </div>
          
          <div className="text-center">
            <div className="flex items-center justify-center w-10 h-10 bg-purple-100 rounded-lg mx-auto mb-2">
              <Clock className="w-5 h-5 text-purple-600" />
            </div>
            <div className="text-xl font-bold text-gray-900">{data.tempo_estimado_preparo}</div>
            <div className="text-xs text-gray-600">Prep. Time</div>
          </div>
          
          <div className="text-center">
            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${getDifficultyColor(data.dificuldade)}`}>
              {data.dificuldade}
            </span>
            <div className="text-xs text-gray-600 mt-1">Dificuldade</div>
          </div>
        </div>

        {/* Badges */}
        {data.badges && data.badges.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-6">
            {data.badges.map((badge, index) => (
              <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                {badge}
              </span>
            ))}
          </div>
        )}

        {/* Sazonalidade */}
        {data.seasonality && data.seasonality.is_seasonal && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-amber-600" />
              <span className="text-sm font-medium text-amber-900">Sazonalidade Detectada</span>
            </div>
            <p className="text-sm text-amber-800">
              Período ótimo: <strong>{data.seasonality.label}</strong> 
              (Score: {data.seasonality.score})
            </p>
          </div>
        )}

        {/* Insights */}
        {data.insights && data.insights.length > 0 && (
          <div className="mb-6">
            <h4 className="text-sm font-semibold text-gray-900 mb-3">💡 Insights</h4>
            <ul className="space-y-2">
              {data.insights.map((insight, index) => (
                <li key={index} className="text-sm text-gray-700 flex items-start gap-2">
                  <ArrowUp className="w-3 h-3 text-blue-500 mt-0.5 flex-shrink-0" />
                  {insight}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Palavras-chave */}
        {data.palavras_chave && data.palavras_chave.length > 0 && (
          <div className="mb-6">
            <h4 className="text-sm font-semibold text-gray-900 mb-3">🔑 Palavras-chave</h4>
            <div className="flex flex-wrap gap-2">
              {data.palavras_chave.map((keyword, index) => (
                <span key={index} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Score Breakdown */}
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-gray-900 mb-3">📊 Breakdown do Score</h4>
          <div className="space-y-2">
            {Object.entries(data.score_breakdown).map(([key, value]) => {
              if (value === 0) return null;
              
              const labels = {
                'base': 'Base',
                'fontes_alta': 'Fontes Confiáveis',
                'fontes_media': 'Fontes Médias',
                'artigos': 'Artigos',
                'relevancia_temporal': 'Relevância Temporal',
                'especificidade': 'Especificidade',
                'sazonalidade': 'Sazonalidade',
                'categorias_bonus': 'Bônus Categoria'
              };
              
              return (
                <div key={key} className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">{labels[key] || key}</span>
                  <span className="text-sm font-medium text-gray-900">+{value}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Notícias */}
        {data.noticias && data.noticias.has_news && (
          <div className="mb-6">
            <h4 className="text-sm font-semibold text-gray-900 mb-3">
              📰 Notícias Relacionadas ({data.noticias.count})
            </h4>
            <div className="space-y-2">
              {data.noticias.items.slice(0, 3).map((noticia, index) => (
                <div key={index} className="p-3 bg-gray-50 rounded-lg">
                  <h5 className="text-sm font-medium text-gray-900 mb-1">{noticia.title}</h5>
                  <p className="text-xs text-gray-600">{noticia.source} • {noticia.confiabilidade}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CTA */}
        <button className="w-full bg-gray-900 hover:bg-gray-800 text-white font-medium py-3 px-4 rounded-lg transition-colors">
          {data.cta.label}
        </button>
      </div>
    </div>
  );
};

// components/SearchInterface.jsx
import React, { useState } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { usePreviewData } from './usePreviewData';
import { PreviewResultCard } from './PreviewResultCard';

export const SearchInterface = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [includeNews, setIncludeNews] = useState(true);
  const [duration, setDuration] = useState(15);
  const { data, loading, error, fetchPreview } = usePreviewData();

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;
    
    await fetchPreview(searchTerm, includeNews, duration);
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Formulário de Busca */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
        <form onSubmit={handleSearch} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tema para análise
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Ex: Enem 2025, Inteligência Artificial, Imposto de Renda..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tempo estimado (minutos)
              </label>
              <input
                type="number"
                min="10"
                max="120"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={duration}
                onChange={(e) => setDuration(parseInt(e.target.value))}
              />
            </div>
            
            <div className="flex items-center pt-6">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  checked={includeNews}
                  onChange={(e) => setIncludeNews(e.target.checked)}
                />
                <span className="ml-2 text-sm text-gray-700">Incluir busca de notícias</span>
              </label>
            </div>
          </div>
          
          <button
            type="submit"
            disabled={loading || !searchTerm.trim()}
            className="w-full bg-gray-900 hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analisando...
              </>
            ) : (
              'Analisar Tema'
            )}
          </button>
        </form>
        
        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">Erro: {error}</p>
          </div>
        )}
      </div>

      {/* Resultado */}
      {data && <PreviewResultCard data={data} />}
    </div>
  );
};