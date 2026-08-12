// src/app/api/pautas/trending/route.ts
import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pythonApiUrl = (process.env.NEXT_PUBLIC_API_URL || 'https://jip-api-1.onrender.com').replace(/\/$/, '');


    const res = await fetch(`${pythonApiUrl}/api/pautas/trending`, {
      cache: 'no-store',
      // @ts-expect-error
      keepalive: true,
      headers: {
        ...(process.env.API_TOKEN
          ? { Authorization: `Bearer ${process.env.API_TOKEN}` }
          : {}),
      },
    });

    if (!res.ok) {
      throw new Error(`FastAPI ${res.status}`);
    }

    const data = await res.json();
    return NextResponse.json(data, { status: 200 });
  } catch (err: any) {
    console.error('[trending proxy] erro:', err?.message || err);
    return NextResponse.json({ temas_recomendados: [] }, { status: 200 });
  }
}
