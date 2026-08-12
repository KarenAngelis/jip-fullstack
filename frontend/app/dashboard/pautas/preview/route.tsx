// src/app/api/pautas/preview/route.ts
import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic'; // evita cache em dev

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const {
      tema,
      incluir_dados_tendencia = true,
      duracao_minutos = 15,
      use_gpt_insights = true,
    } = body || {};

    if (!tema || !String(tema).trim()) {
      return NextResponse.json(
        { error: 'Tema é obrigatório' },
        { status: 400 }
      );
    }

    const pythonApiUrl = (process.env.NEXT_PUBLIC_API_URL || 'https://jip-api-1.onrender.com').replace(/\/$/, '');


    // IMPORTANTE: seu backend expõe /api/pautas/preview
    const res = await fetch(`${pythonApiUrl}/api/pautas/preview`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(process.env.API_TOKEN
          ? { Authorization: `Bearer ${process.env.API_TOKEN}` }
          : {}),
      },
      body: JSON.stringify({
        tema,
        incluir_dados_tendencia,
        duracao_minutos,
        use_gpt_insights,
      }),
      // @ts-expect-error: keepalive não é tipado em todos runtimes
      keepalive: true,
      cache: 'no-store',
    });

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(`FastAPI ${res.status}: ${text || res.statusText}`);
    }

    const data = await res.json();
    return NextResponse.json(data, { status: 200 });
  } catch (err: any) {
    console.error('[preview proxy] erro:', err?.message || err);

    // fallback mínimo só para não quebrar a UI
    const now = new Date().toISOString();
    return NextResponse.json(
      {
        contract_version: 'preview_v2',
        id: `mock-${Date.now()}`,
        generated_at: now,
        tema: 'Tema indisponível',
        viabilidade_score: 65,
        oportunidade: { label: 'Boa oportunidade (offline)', score_pct: 0.65, score: 65 },
        trend_growth_pct: 50,
        dificuldade: 'Medium',
        dificuldade_score: 50,
        error_mode: true,
        message: 'API Python indisponível - exibindo dados de exemplo',
      },
      { status: 200 }
    );
  }
}
