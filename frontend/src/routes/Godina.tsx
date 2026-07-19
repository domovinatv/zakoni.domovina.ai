import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { aktPath, deburr, formatDate, loadGodina } from "@/lib/data";
import type { AktSummary } from "@/lib/types";

export default function Godina() {
  const { g } = useParams();
  const [akti, setAkti] = useState<AktSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    if (!g) return;
    loadGodina(g).then(setAkti).catch((e) => setErr(String(e)));
  }, [g]);

  const filtered = useMemo(() => {
    if (!akti) return null;
    const needle = deburr(q.trim());
    if (!needle) return akti;
    return akti.filter((a) =>
      deburr(`${a.naslov ?? ""} ${a.tip ?? ""} ${a.donositelj ?? ""}`).includes(needle)
    );
  }, [akti, q]);

  if (err) return <p className="text-red-600">Greška: {err}</p>;
  if (!filtered) return <p className="text-muted">Učitavanje…</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-navy mb-4">Narodne novine {g}.</h1>
      <input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Filtriraj po naslovu, vrsti, donositelju…"
        className="w-full rounded border border-border bg-white px-3 py-2 mb-4 shadow-card"
      />
      <p className="text-sm text-muted mb-3">{filtered.length.toLocaleString("hr")} akata</p>
      <ul className="space-y-2">
        {filtered.map((a) => (
          <li key={a.eli}>
            <Link
              to={aktPath(a.eli)}
              className="block rounded bg-white shadow-card p-4 hover:bg-navy-50"
            >
              <span className="text-xs text-muted">
                NN {a.broj}/{g} · br. {a.clanak}
                {a.datum ? ` · ${formatDate(a.datum)}` : ""}
                {a.tip ? ` · ${a.tip}` : ""}
              </span>
              <span className="block font-medium">{a.naslov ?? "(bez naslova)"}</span>
              {a.donositelj && (
                <span className="block text-sm text-muted">{a.donositelj}</span>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
