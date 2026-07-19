import type { AktDetail, AktSummary, Stats } from "./types";

const memo = new Map<string, Promise<unknown>>();

function fetchJson<T>(url: string): Promise<T> {
  const cached = memo.get(url) as Promise<T> | undefined;
  if (cached) return cached;
  const p = fetch(url, { credentials: "omit" }).then((r) => {
    if (!r.ok) throw new Error(`${url} → ${r.status}`);
    return r.json() as Promise<T>;
  });
  memo.set(url, p);
  return p;
}

export const loadStats = () => fetchJson<Stats>("/data/stats.json");
export const loadGodina = (g: number | string) =>
  fetchJson<AktSummary[]>(`/data/godine/${g}.json`);
export const loadAkt = (g: string, broj: string, clanak: string) =>
  fetchJson<AktDetail>(`/data/akt/${g}/${broj}_${clanak}.json`);

const DIACRITIC_RE = /[̀-ͯ]/g;

export function deburr(s: string): string {
  return s.normalize("NFKD").replace(DIACRITIC_RE, "").toLowerCase();
}

/** "2026-01-02" → "2. 1. 2026." */
export function formatDate(iso?: string | null): string | null {
  if (!iso) return null;
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return iso;
  return `${Number(m[3])}. ${Number(m[2])}. ${m[1]}.`;
}

/** "sluzbeni/2026/78/937" → "/akt/2026/78/937" */
export function aktPath(eli: string): string {
  const [, g, b, c] = eli.split("/");
  return `/akt/${g}/${b}/${c}`;
}

/** "sluzbeni/2026/78/937" → "NN 78/2026, čl. 937" */
export function nnRef(eli: string): string {
  const [, g, b, c] = eli.split("/");
  return `NN ${b}/${g}, br. ${c}`;
}
