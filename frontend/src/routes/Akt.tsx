import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { aktPath, formatDate, loadAkt, nnRef } from "@/lib/data";
import type { AktDetail } from "@/lib/types";

const PREDIKATI: Record<string, string> = {
  repealed_by: "Ukinut aktom",
  repeals: "Ukida",
  based_on: "Temelji se na",
  basis_for: "Temelj za",
  changed_by: "Izmijenjen aktom",
  changes: "Mijenja",
};

export default function Akt() {
  const { g, broj, clanak } = useParams();
  const [akt, setAkt] = useState<AktDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!g || !broj || !clanak) return;
    loadAkt(g, broj, clanak).then(setAkt).catch((e) => setErr(String(e)));
  }, [g, broj, clanak]);

  if (err) return <p className="text-red-600">Greška: {err}</p>;
  if (!akt) return <p className="text-muted">Učitavanje…</p>;

  const nnUrl = `https://narodne-novine.nn.hr/eli/${akt.eli}`;

  return (
    <article>
      <p className="text-sm text-muted">
        <Link className="underline" to={`/godina/${akt.godina}`}>NN {akt.godina}.</Link>{" "}
        · NN {akt.broj}/{akt.godina} · broj akta {akt.clanak}
        {akt.tip ? ` · ${akt.tip}` : ""}
      </p>
      <h1 className="text-2xl font-bold text-navy mt-1 mb-2">{akt.naslov ?? "(bez naslova)"}</h1>
      <p className="text-sm text-muted mb-4">
        {akt.donositelj && <>{akt.donositelj} · </>}
        {akt.datum_akta && <>donesen {formatDate(akt.datum_akta)} · </>}
        {akt.datum_objave && <>objavljen {formatDate(akt.datum_objave)} · </>}
        <a className="underline" href={nnUrl} target="_blank" rel="noreferrer">
          izvornik na nn.hr
        </a>
      </p>

      {(akt.veze.length > 0 || akt.veze_na_ovaj.length > 0) && (
        <div className="rounded bg-navy-50 p-4 mb-4 text-sm space-y-1">
          {akt.veze.map((v, i) => (
            <p key={`v${i}`}>
              {PREDIKATI[v.predikat] ?? v.predikat}:{" "}
              <Link className="underline text-navy" to={aktPath(v.to_eli!)}>
                {nnRef(v.to_eli!)}
              </Link>
            </p>
          ))}
          {akt.veze_na_ovaj.map((v, i) => (
            <p key={`n${i}`}>
              <Link className="underline text-navy" to={aktPath(v.from_eli!)}>
                {nnRef(v.from_eli!)}
              </Link>{" "}
              → {PREDIKATI[v.predikat] ?? v.predikat} (ovaj akt)
            </p>
          ))}
        </div>
      )}

      {akt.tekst ? (
        <div className="rounded-lg bg-white shadow-card p-5 whitespace-pre-wrap text-[15px] leading-relaxed">
          {akt.tekst}
        </div>
      ) : (
        <p className="text-muted">Tekst nije dostupan — vidi izvornik na nn.hr.</p>
      )}

      {akt.oznake.length > 0 && (
        <ul className="flex flex-wrap gap-2 mt-4">
          {akt.oznake.map((o, i) => (
            <li key={i} className="rounded-sm bg-navy-100 text-navy-700 px-2 py-1 text-xs">
              {o.label ?? `${o.vrsta}:${o.uri.split("/").pop()}`}
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
