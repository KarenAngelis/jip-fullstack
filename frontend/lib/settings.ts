// web/lib/settings.ts
import { z } from "zod";
import http, { get } from "./api";

/* ---------------- Tipos + validação ---------------- */
export const PersonTypeLiteral = z.enum(["PF", "PJ"]);

export const SettingsBase = z.object({
  person_type: PersonTypeLiteral.default("PF"),
  display_name: z.string().min(2).max(120),
  niche: z.string().max(120).nullish(),
  bio: z.string().max(500).nullish(),
  street: z.string().nullish(),
  number: z.string().nullish(),
  city: z.string().nullish(),
  state: z.string().nullish(),
  zip_code: z.string().nullish(),
  media_url: z.string().url().or(z.string()).nullish(),
});

export const SettingsOut = SettingsBase.extend({
  id: z.number().int(),
  user_id: z.number().int(),
  created_at: z.string(), // ISO
  updated_at: z.string(),
});

export type TSettingsOut = z.infer<typeof SettingsOut>;
export type TSettingsPutBody = z.infer<typeof SettingsBase>;
export type TSettingsPatchBody = Partial<TSettingsPutBody>;

/* ----------------------- API ----------------------- */
/** ⚠️ Suas rotas são /settings/* (sem /api) */
const PREFIX = "/settings";

export async function apiGetMySettings(): Promise<TSettingsOut> {
  const data = await get<unknown>(`${PREFIX}/me`);
  return SettingsOut.parse(data);
}

export async function apiPutMySettings(
  body: TSettingsPutBody
): Promise<TSettingsOut> {
  const { data } = await http.put<unknown>(`${PREFIX}/me`, body);
  return SettingsOut.parse(data);
}

export async function apiPatchMySettings(
  patch: TSettingsPatchBody
): Promise<TSettingsOut> {
  const { data } = await http.patch<unknown>(`${PREFIX}/me`, patch);
  return SettingsOut.parse(data);
}

export async function apiUploadMySettingsMedia(
  file: File
): Promise<{ url: string }> {
  const form = new FormData();
  form.append("file", file, file.name);
  const { data } = await http.post<{ url: string }>(`${PREFIX}/me/media`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}
