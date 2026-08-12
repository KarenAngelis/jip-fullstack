// components/ContentDisplay.tsx
"use client";

import { useState } from 'react';
import { 
  Copy, 
  Save, 
  Star, 
  TrendingUp, 
  Eye,
  Search,
  Download,
  Share2,
  Edit,
  Trash2,
  MoreVertical,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import { GeneratedContent } from '../hooks/useContentGeneration';

interface ContentDisplayProps {
  content: GeneratedContent[];
  type: 'titulos' | 'episodios';
  onSave?: (contentId: string, title: string) => void;
  onEdit?: (contentId: string) => void;
  onDelete?: (contentId: string) => void;
}

interface ContentItemProps {
  item: GeneratedContent;
  type: 'titulos' | 'episodios';
  onSave?: (contentId: string, title: string) => void;
  onEdit?: (contentId: string) => void;
  onDelete?: (contentId: string) => void;
}

const ContentItem: React.FC<ContentItemProps> = ({ 
  item, 
  type, 
  onSave, 
  onEdit, 
  onDelete 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showActions, setShowActions] = useState(false);
  const [copied, setCopied] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Erro ao copiar:', err);
    }
  };

  const handleSave = async () => {
    if (!onSave) return;
    
    setSaving(true);
    try {
      await onSave(item.id, item.content.split('\n')[0] || 'Conteúdo sem título');
    } finally {
      setSaving(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-400';
    if (score >= 80) return 'text-yellow-400';
    if (score >= 70) return 'text-orange-400';
    return 'text-red-400';
  };

  const getScoreBg = (score: number) => {
    if (score >= 90) return 'bg-green-500/20 border-green-500/30';
    if (score >= 80) return 'bg-yellow-500/20 border-yellow-500/30';
    if (score >= 70) return 'bg-orange-500/20 border-orange-500/30';
    return 'bg-red-500/20 border-red-500/30';
  };

  const formatContent = (content: string) => {
    if (type === 'titulos') {
      return content;
    }
    
    // Para roteiros e episódios, formata markdown básico
    return content
      .split('\n')
      .map((line, index) => {
        if (line.startsWith('# ')) {
          return <h3 key={index} className="text-lg font-bold text-white mt-4 mb-2">{line.slice(2)}</h3>;
        }
        if (line.startsWith('## ')) {
          return <h4 key={index} className="text-md font-semibold text-cyan-400 mt-3 mb-1">{line.slice(3)}</h4>;
        }
        if (line.startsWith('### ')) {
          return <h5 key={index} className="text-sm font-medium text-gray-300 mt-2 mb-1">{line.slice(4)}</h5>;
        }
        if (line.startsWith('- ')) {
          return <li key={index} className="text-gray-300 ml-4">{line.slice(2)}</li>;
        }
        if (line.trim() === '') {
          return <br key={index} />;
        }
        return <p key={index} className="text-gray-300 mb-1">{line}</p>;
      });
  };

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg hover:bg-gray-800 transition-all duration-200 group">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              {/* Score */}
              {item.score && (
                <div className={`px-2 py-1 rounded border ${getScoreBg(item.score)}`}>
                  <div className="flex items-center gap-1">
                    <Star className={`h-3 w-3 ${getScoreColor(item.score)}`} />
                    <span className={`text-xs font-medium ${getScoreColor(item.score)}`}>
                      {item.score}/100
                    </span>
                  </div>
                </div>
              )}
              
              {/* Métricas */}
              {item.metadata && (
                <div className="flex gap-2">
                  <div className="flex items-center gap-1 text-xs text-gray-400">
                    <TrendingUp className="h-3 w-3" />
                    <span>{item.metadata.engagement_potential}%</span>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-gray-400">
                    <Search className="h-3 w-3" />
                    <span>{item.metadata.seo_score}%</span>
                  </div>
                </div>
              )}
            </div>

            {/* Conteúdo Preview */}
            <div className={`${type === 'titulos' ? '' : 'cursor-pointer'}`} 
                 onClick={() => type !== 'titulos' && setIsExpanded(!isExpanded)}>
              {type === 'titulos' ? (
                <p className="text-white font-medium">{item.content}</p>
              ) : (
                <div>
                  <p className="text-white font-medium line-clamp-2">
                    {item.content.split('\n')[0] || 'Conteúdo sem título'}
                  </p>
                  {!isExpanded && (
                    <p className="text-gray-400 text-sm mt-1 line-clamp-2">
                      {item.content.split('\n').slice(1, 3).join(' ')}...
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 ml-4">
            {/* Copy Button */}
            <button
              onClick={() => handleCopy(item.content)}
              className={`p-2 rounded-lg transition-all duration-200 ${
                copied 
                  ? 'bg-green-500/20 text-green-400' 
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
              title={copied ? 'Copiado!' : 'Copiar'}
            >
              {copied ? <CheckCircle className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            </button>

            {/* Save Button */}
            {onSave && (
              <button
                onClick={handleSave}
                disabled={saving}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                title="Salvar"
              >
                {saving ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-400 border-t-transparent"></div>
                ) : (
                  <Save className="h-4 w-4" />
                )}
              </button>
            )}

            {/* More Actions */}
            <div className="relative">
              <button
                onClick={() => setShowActions(!showActions)}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
                title="Mais ações"
              >
                <MoreVertical className="h-4 w-4" />
              </button>

              {showActions && (
                <div className="absolute right-0 top-full mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-10 min-w-[120px]">
                  {onEdit && (
                    <button
                      onClick={() => { onEdit(item.id); setShowActions(false); }}
                      className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 flex items-center gap-2"
                    >
                      <Edit className="h-3 w-3" />
                      Editar
                    </button>
                  )}
                  <button
                    onClick={() => handleCopy(item.content)}
                    className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 flex items-center gap-2"
                  >
                    <Share2 className="h-3 w-3" />
                    Compartilhar
                  </button>
                  {onDelete && (
                    <button
                      onClick={() => { onDelete(item.id); setShowActions(false); }}
                      className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-gray-700 flex items-center gap-2"
                    >
                      <Trash2 className="h-3 w-3" />
                      Excluir
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && type !== 'titulos' && (
        <div className="p-4 border-t border-gray-700">
          <div className="prose prose-invert max-w-none">
            {formatContent(item.content)}
          </div>
        </div>
      )}
    </div>
  );
};

const ContentDisplay: React.FC<ContentDisplayProps> = ({ 
  content, 
  type, 
  onSave, 
  onEdit, 
  onDelete 
}) => {
  const [sortBy, setSortBy] = useState<'score' | 'engagement' | 'seo'>('score');
  const [filterScore, setFilterScore] = useState<number>(0);

  const sortedContent = [...content].sort((a, b) => {
    switch (sortBy) {
      case 'score':
        return (b.score || 0) - (a.score || 0);
      case 'engagement':
        return (b.metadata?.engagement_potential || 0) - (a.metadata?.engagement_potential || 0);
      case 'seo':
        return (b.metadata?.seo_score || 0) - (a.metadata?.seo_score || 0);
      default:
        return 0;
    }
  }).filter(item => (item.score || 0) >= filterScore);

  if (content.length === 0) {
    return (
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-8 text-center backdrop-blur-sm">
        <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-400 text-lg mb-2">Nenhum conteúdo gerado ainda</p>
        <p className="text-gray-500 text-sm">
          Preencha os campos acima e clique em "Gerar" para começar
        </p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-6 backdrop-blur-sm">
      {/* Header com controles */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">
          {content.length} {type} gerado{content.length !== 1 ? 's' : ''}
        </h3>
        
        <div className="flex items-center gap-3">
          {/* Filtro por Score */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400">Score mín:</span>
            <select
              value={filterScore}
              onChange={(e) => setFilterScore(Number(e.target.value))}
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white"
            >
              <option value={0}>Todos</option>
              <option value={70}>70+</option>
              <option value={80}>80+</option>
              <option value={90}>90+</option>
            </select>
          </div>

          {/* Ordenação */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400">Ordenar:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'score' | 'engagement' | 'seo')}
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white"
            >
              <option value="score">Score</option>
              <option value="engagement">Engajamento</option>
              <option value="seo">SEO</option>
            </select>
          </div>
        </div>
      </div>

      {/* Lista de conteúdo */}
      <div className="space-y-4">
        {sortedContent.map((item) => (
          <ContentItem
            key={item.id}
            item={item}
            type={type}
            onSave={onSave}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        ))}
      </div>

      {sortedContent.length === 0 && content.length > 0 && (
        <div className="text-center py-8">
          <p className="text-gray-400">
            Nenhum conteúdo corresponde aos filtros selecionados
          </p>
        </div>
      )}
    </div>
  );
};

export default ContentDisplay;