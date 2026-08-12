// web/app/dashboard/settings/page.tsx
"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useSettings } from "../../../hooks/useSettings";
import type { TSettingsPatchBody, TSettingsPutBody, PersonTypeLiteral } from "../../../lib/settings";

/** debounce simples p/ PATCH automático */
function useDebounced<T extends (...args: any[]) => void>(fn: T, delay = 600) {
  const [t, setT] = useState<NodeJS.Timeout | null>(null);
  return (...args: Parameters<T>) => {
    if (t) clearTimeout(t);
    const nt = setTimeout(() => fn(...args), delay);
    setT(nt);
  };
}

export default function SettingsPage() {
  // Hook usa o axios do projeto (token já é injetado)
  const { data, isLoading, isError, error, patch, save, uploadMedia } =
    useSettings({ enabled: true });

  // form controlado para PUT “Salvar tudo”
  const [form, setForm] = useState<TSettingsPutBody | null>(null);

  // quando os dados carregarem, popular o form
  useEffect(() => {
    if (!data) return;
    setForm({
      person_type: data.person_type,
      display_name: data.display_name,
      niche: data.niche ?? null,
      bio: data.bio ?? null,
      street: data.street ?? null,
      number: data.number ?? null,
      city: data.city ?? null,
      state: data.state ?? null,
      zip_code: data.zip_code ?? null,
      media_url: data.media_url ?? null,
    });
  }, [data]);

  const debouncedPatch = useDebounced(async (p: TSettingsPatchBody) => {
    await patch(p);
  }, 600);

  const onChange = (k: keyof TSettingsPutBody, v: any) => {
    setForm((prev) => (prev ? { ...prev, [k]: v } : prev));
    // autosave para campos mais comuns
    if (["display_name", "person_type", "bio", "niche"].includes(k)) {
      debouncedPatch({ [k]: v } as TSettingsPatchBody);
    }
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form) await save(form);
  };

  const avatar = useMemo(() => form?.media_url ?? "", [form]);

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Configurações</h1>
        <button
          onClick={onSubmit}
          className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 font-medium"
          disabled={!form}
        >
          Salvar tudo
        </button>
      </div>

      {isLoading && !form && (
        <div className="animate-pulse grid lg:grid-cols-[240px_1fr] gap-6">
          <div className="h-48 bg-gray-800 rounded-2xl" />
          <div className="h-48 bg-gray-800 rounded-2xl" />
        </div>
      )}

      {isError && (
        <div className="p-4 rounded-xl border border-red-700 bg-red-900/20 text-red-300">
          Erro ao carregar: {error?.message}
        </div>
      )}

      {form && (
        <div className="grid lg:grid-cols-[240px_1fr] gap-6">
          {/* avatar */}
          <div className="bg-gray-900/70 border border-gray-800 rounded-2xl p-4">
            <div className="flex flex-col items-center gap-4">
              <div className="w-36 h-36 rounded-2xl overflow-hidden bg-gray-800 border border-gray-700">
                {avatar ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={avatar} alt="Foto" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-500">
                    sem imagem
                  </div>
                )}
              </div>
              <label className="w-full">
                <span className="block text-sm text-gray-300 mb-2">Foto</span>
                <input
                  type="file"
                  accept="image/png, image/jpeg, image/webp"
                  className="block w-full text-sm text-gray-300 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-cyan-600 file:text-white hover:file:bg-cyan-500"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) uploadMedia(f);
                  }}
                />
              </label>
            </div>
          </div>

          {/* formulário */}
          <form
            onSubmit={onSubmit}
            className="bg-gray-900/70 border border-gray-800 rounded-2xl p-6 grid md:grid-cols-2 gap-5"
          >
            <div>
              <label className="block text-sm text-gray-300 mb-1">Tipo</label>
              <select
                value={form.person_type}
                onChange={(e) => onChange("person_type", e.target.value as PersonTypeLiteral)}
                className="w-full bg-gray-800 text-white border border-gray-700 rounded-xl p-3"
              >
                <option value="PF">Pessoa Física</option>
                <option value="PJ">Pessoa Jurídica</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-300 mb-1">Nome</label>
              <input
                value={form.display_name}
                onChange={(e) => onChange("display_name", e.target.value)}
                className="w-full bg-gray-800 text-white border border-gray-700 rounded-xl p-3"
                placeholder="Como quer aparecer"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm text-gray-300 mb-1">Nicho</label>
              <input
                value={form.niche ?? ""}
                onChange={(e) => onChange("niche", e.target.value)}
                className="w-full bg-gray-800 text-white border border-gray-700 rounded-xl p-3"
                placeholder="Seu nicho"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm text-gray-300 mb-1">Bio</label>
              <textarea
                value={form.bio ?? ""}
                onChange={(e) => onChange("bio", e.target.value)}
                rows={4}
                className="w-full bg-gray-800 text-white border border-gray-700 rounded-xl p-3"
                placeholder="Fale sobre você"
              />
            </div>

            {/* endereço */}
            <div className="md:col-span-2 grid md:grid-cols-4 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm text-gray-300 mb-1">Rua</label>
                <input
                  value={form.street ?? ""}
                  onChange={(e) => onChange("street", e.target.value)}
                  className="w-full bg-gray-800 text-white border border-gray-700 rounded-xl p-3"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Número</label>
                <input
                  value={form.number ?? ""}
                  onChange={(e) => onChange("number", e.target.value)}
                  className="w-full bg-gray-800 text-white border border-gray-700 rounded-xl p-3"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">CEP</label>
                <input
                  value={form.zip_code ?? ""}
                  onChange={(e) => onChange("zip_code", e.target.value)}
                  className="w-full bg-gray-800 text-white border border-gray-700 rounded-xl p-3"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Cidade</label>
                <input
                  value={form.city ?? ""}
                  onChange={(e) => onChange("city", e.target.value)}
                  className="w-full bg-gray-800 text-white border border-gray-700 rounded-xl p-3"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Estado</label>
                <input
                  value={form.state ?? ""}
                  onChange={(e) => onChange("state", e.target.value)}
                  className="w-full bg-gray-800 text-white border border-gray-700 rounded-xl p-3"
                />
              </div>
            </div>

            <div className="md:col-span-2 flex justify-end">
              <button
                type="submit"
                className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 font-medium"
              >
                Salvar
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
