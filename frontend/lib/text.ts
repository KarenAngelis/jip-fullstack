// src/lib/text.ts
export const normalize = (s: string) =>
  (s || "").normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().trim();

export const isGenericTitle = (title: string, query: string) => {
  const t = normalize(title);
  const q = normalize(query);
  if (!q || q.length < 2) return false;
  return !t.includes(q);
};
