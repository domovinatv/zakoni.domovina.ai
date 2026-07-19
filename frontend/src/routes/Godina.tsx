import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { aktPath, deburr, formatDate, loadGodina } from "@/lib/data";
import { IzmjenaBadge, TekstBadge, TipBadge } from "@/components/Oznake";
import type { AktSummary } from "@/lib/types";

type TekstFilter = "sve" | "s-tekstom" | "bez-teksta";

export default function Godina() {
  const { g } = useParams();
  const [akti, setAkti] = useState<AktSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [tip, setTip] = useState<string>("sve");
  const [tekst, setTekst] = useState<TekstFilter>("sve");

  useEffect(() => {
    if (!g) return;
    setAkti(null);
    setTip("sve");
    setTekst("sve");
    loadGodina(g).then(setAkti).catch((e) => setErr(String(e)));
  }, [g]);

  // Vrste akata s brojem pojavljivanja — daje pregled sastava godine bez otvaranja akata.
  const tipovi = useMemo(() => {
    if (!akti) return [];
    const m = new Map<string, number>();
    for (const a of akti) m.set(a.tip ?? "—", (m.get(a.tip ?? "—") ?? 0) + 1);
    return [...m.entries()].sort((x, y) => y[1] - x[1]);
  }, [akti]);

  const bezTeksta = useMemo(() => akti?.filter((a) => !a.ima_tekst).length ?? 0, [akti]);

  const filtered = useMemo(() => {
    if (!akti) return null;
    const needle = deburr(q.trim());
    return akti.filter((a) => {
      if (tip !== "sve" && (a.tip ?? "—") !== tip) return false;
      if (tekst === "s-tekstom" && !a.ima_tekst) return false;
      if (tekst === "bez-teksta" && a.ima_tekst) return false;
      if (!needle) return true;
      return deburr(
        `${a.naslov ?? ""} ${a.tip ?? ""} ${a.donositelj ?? ""}`
      ).includes(needle);
    });
  }, [akti, q, tip, tekst]);

  if (err) return <p className="text-red-600">Greška: {err}</p>;
  if (!filtered || !akti) return <p className="text-muted">Učitavanje…</p>;

  const chip = (aktivan: boolean) =>
    `rounded-full border px-2.5 py-1 text-xs transition ${
      aktivan
        ? "border-navy bg-navy text-white"
        : "border-border bg-white text-muted hover:border-navy"
    }`;

  return (
    <div>
      <h1 className="text-2xl font-bold text-navy mb-4">Narodne novine {g}.</h1>

      <input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Filtriraj po naslovu, vrsti, donositelju…"
        className="w-full rounded border border-border bg-white px-3 py-2 mb-3 shadow-card"
      />

      <div className="flex flex-wrap gap-1.5 mb-2">
        <button className={chip(tip === "sve")} onClick={() => setTip("sve")}>
          sve vrste ({akti.length.toLocaleString("hr")})
        </button>
        {tipovi.map(([t, n]) => (
          <button key={t} className={chip(tip === t)} onClick={() => setTip(t)}>
            {t === "—" ? "bez vrste" : t.replace(/_/g, " ").toLowerCase()} ({n.toLocaleString("hr")})
          </button>
        ))}
      </div>

      {bezTeksta > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          <button className={chip(tekst === "sve")} onClick={() => setTekst("sve")}>
            svi
          </button>
          <button className={chip(tekst === "s-tekstom")} onClick={() => setTekst("s-tekstom")}>
            s tekstom ({(akti.length - bezTeksta).toLocaleString("hr")})
          </button>
          <button className={chip(tekst === "bez-teksta")} onClick={() => setTekst("bez-teksta")}>
            bez teksta ({bezTeksta.toLocaleString("hr")})
          </button>
        </div>
      )}

      <p className="text-sm text-muted mb-3">
        {filtered.length.toLocaleString("hr")}
        {filtered.length !== akti.length ? ` od ${akti.length.toLocaleString("hr")}` : ""} akata
      </p>

      <ul className="space-y-2">
        {filtered.map((a) => (
          <li key={a.eli}>
            <Link
              to={aktPath(a.eli)}
              className="block rounded bg-white shadow-card p-4 hover:bg-navy-50"
            >
              <div className="flex flex-wrap items-center gap-1.5 mb-1">
                <TipBadge tip={a.tip} />
                <IzmjenaBadge izmjena={a.izmjena} />
                <TekstBadge akt={a} />
                <span className="text-xs text-muted">
                  NN {a.broj}/{g} · br. {a.clanak}
                  {a.datum ? ` · ${formatDate(a.datum)}` : ""}
                </span>
              </div>
              <span className="block font-medium">{a.naslov ?? "(bez naslova)"}</span>
              {a.donositelj && (
                <span className="block text-sm text-muted">{a.donositelj}</span>
              )}
            </Link>
          </li>
        ))}
      </ul>

      {filtered.length === 0 && (
        <p className="text-muted py-8 text-center">Nema akata koji odgovaraju filtru.</p>
      )}
    </div>
  );
}
