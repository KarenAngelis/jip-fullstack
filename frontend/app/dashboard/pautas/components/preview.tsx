// pages/api/pautas/preview.js (ou app/api/pautas/preview/route.js para App Router)

// Para Pages Router (pages/api/pautas/preview.js)
export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Método não permitido' });
  }

  const { 
    tema, 
    incluir_dados_tendencia = true, 
    duracao_minutos = 15,
    use_gpt_insights = true 
  } = req.body;

  if (!tema || tema.trim().length === 0) {
    return res.status(400).json({ 
      error: 'Tema é obrigatório',
      details: 'O campo tema não pode estar vazio'
    });
  }

  try {
    // URL do seu backend Python
  const pythonApiUrl = (process.env.NEXT_PUBLIC_API_URL || 'https://jip-api-1.onrender.com').replace(/\/$/, '');
    
    const response = await fetch(`${pythonApiUrl}/api/preview`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.API_TOKEN}` // se você usar auth
      },
      body: JSON.stringify({
        tema,
        incluir_dados_tendencia,
        duracao_minutos,
        use_gpt_insights
      }),
      timeout: 30000 // 30s timeout
    });

    if (!response.ok) {
      throw new Error(`Erro na API Python: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    
    // Log para debug (remover em produção)
    console.log(`Preview gerado para tema: "${tema}" - Score: ${data.viabilidade_score}`);
    
    res.status(200).json(data);
    
  } catch (error) {
    console.error('Erro ao processar preview:', error);
    
    // Fallback com dados mockados se a API falhar
    const mockData = {
      contract_version: "preview_v2",
      id: `mock-${Date.now()}`,
      generated_at: new Date().toISOString(),
      tema,
      categoria: "geral",
      viabilidade_score: 65,
      oportunidade: {
        label: "Boa oportunidade",
        score_pct: 0.65,
        score: 65
      },
      score_breakdown: {
        base: 50,
        fontes_alta: 0,
        fontes_media: 0,
        artigos: 0,
        relevancia_temporal: 5,
        especificidade: 10,
        sazonalidade: 0,
        categorias_bonus: 0
      },
      trend_growth_pct: 80,
      volume_estimado: 6000,
      dificuldade: "Medium",
      dificuldade_score: 50,
      seasonality: {
        score: 40,
        months: [1,2,3,4,5,6,7,8,9,10,11,12],
        label: "ano todo",
        is_seasonal: false
      },
      palavras_chave: tema.split(' ').slice(0, 4),
      insights: [
        "Análise offline - conecte com a API Python para dados completos",
        `Tema "${tema}" tem potencial moderado`,
        "Recomendamos especificar mais o tópico"
      ],
      badges: ["Modo Offline"],
      noticias: {
        has_news: false,
        count: 0,
        items: []
      },
      tempo_estimado_preparo: `${duracao_minutos} minutos`,
      proximos_passos: [
        "Conectar API Python",
        "Buscar dados reais",
        "Gerar insights com IA"
      ],
      cta: {
        label: "Reconectar API",
        endpoint: "/api/pautas/gerar"
      },
      busca_noticias_ativa: incluir_dados_tendencia,
      recomendacao: "Conecte a API Python para análises completas"
    };

    res.status(200).json(mockData);
  }
}

// Para App Router (app/api/pautas/preview/route.js)
export async function POST(request) {
  try {
    const body = await request.json();
    const { 
      tema, 
      incluir_dados_tendencia = true, 
      duracao_minutos = 15,
      use_gpt_insights = true 
    } = body;

    if (!tema || tema.trim().length === 0) {
      return Response.json({ 
        error: 'Tema é obrigatório',
        details: 'O campo tema não pode estar vazio'
      }, { status: 400 });
    }

    // URL do seu backend Python
    const pythonApiUrl = (process.env.NEXT_PUBLIC_API_URL || 'https://jip-api-1.onrender.com').replace(/\/$/, '');
    
    const response = await fetch(`${pythonApiUrl}/api/preview`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.API_TOKEN}`
      },
      body: JSON.stringify({
        tema,
        incluir_dados_tendencia,
        duracao_minutos,
        use_gpt_insights
      })
    });

    if (!response.ok) {
      throw new Error(`Erro na API Python: ${response.status}`);
    }

    const data = await response.json();
    
    return Response.json(data);
    
  } catch (error) {
    console.error('Erro ao processar preview:', error);
    
    // Mesmo fallback que acima...
    const { tema = "Tema não especificado", duracao_minutos = 15, incluir_dados_tendencia = true } = await request.json().catch(() => ({}));
    
    const mockData = {
      contract_version: "preview_v2",
      id: `mock-${Date.now()}`,
      generated_at: new Date().toISOString(),
      tema,
      categoria: "geral",
      viabilidade_score: 65,
      oportunidade: {
        label: "Boa oportunidade (offline)",
        score_pct: 0.65,
        score: 65
      },
      error_mode: true,
      message: "API Python indisponível - exibindo dados de exemplo"
    };

    return Response.json(mockData);
  }
}