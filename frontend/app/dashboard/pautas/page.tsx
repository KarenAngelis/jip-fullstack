// src/app/dashboard/pautas/page.tsx
// Rota: /dashboard/pautas

import { cookies } from "next/headers";
import PautasDashboard from "./components/PautasDashboard";
import { API_ROOT, type PautaListItem } from "@/lib/api";

type PautasListResponse = { pautas: PautaListItem[]; total: number };

async function fetchPautas(): Promise<PautasListResponse> {
  const token = cookies().get("access_token")?.value;

  const res = await fetch(`${API_ROOT}/api/pautas`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    // queremos SEMPRE o estado atual do banco
    cache: "no-store",
  });

  if (!res.ok) {
    // 401/403/etc — devolve shape vazio para o componente lidar
    return { pautas: [], total: 0 };
  }

  return (await res.json()) as PautasListResponse;
}

export default async function Page() {
  const data = await fetchPautas();

  // Passa tudo como prop; o componente decide como renderizar
  return <PautasDashboard initialData={data} />;
}
