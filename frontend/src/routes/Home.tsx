import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { loadStats } from "@/lib/data";
import type { Stats } from "@/lib/types";

export default function Home() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    loadStats().then(setStats).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <p className="text-red-600">Greška pri učitavanju: {err}</p>;
  if (!stats) return <p className="text-muted">Učitavanje…</p>;

  return (
    <div>
      <div className="rounded-lg bg-white shadow-card p-5 mb-6">
        <p className="text-3xl font-bold text-navy">{stats.ukupno.toLocaleString("hr")}</p>
        <p className="text-muted text-sm">akata u katalogu</p>
      </div>

      <h2 className="font-semibold text-lg mb-3">Po godinama</h2>
      <ul className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {stats.godine.map((g) => (
          <li key={g.godina}>
            <Link
              to={`/godina/${g.godina}`}
              className="block rounded bg-white shadow-card p-4 hover:bg-navy-50"
            >
              <span className="text-navy font-bold text-lg">{g.godina}</span>
              <span className="block text-sm text-muted">
                {g.akata.toLocaleString("hr")} akata · {g.izdanja} izdanja
              </span>
            </Link>
          </li>
        ))}
      </ul>

      <h2 className="font-semibold text-lg mt-8 mb-3">Vrste akata</h2>
      <ul className="flex flex-wrap gap-2">
        {Object.entries(stats.tipovi).map(([tip, n]) => (
          <li key={tip} className="rounded-sm bg-navy-100 text-navy-700 px-2 py-1 text-xs">
            {tip} · {n.toLocaleString("hr")}
          </li>
        ))}
      </ul>
    </div>
  );
}
