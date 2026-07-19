"""Katalog svih propisa iz sluzbenog Kazala NN — jedan zahtjev po godini.

Izvor:  https://narodne-novine.nn.hr/get_index_file.aspx?year={G}&type=csv
        (tab-separated unatoc nazivu 'csv', UTF-8 s BOM-om; raspon 1990 -> danas)
        Vidi docs/01-izvor-podataka-nn.md §12.

Cache:  data/raw/nn/kazalo/{serija}_{godina}.csv — nikad se ne brise; ako postoji,
        mrezni zahtjev se preskace.

Garancija idempotentnosti: upsert po (serija, godina, clanak); ponovno pokretanje
ne duplicira retke niti ponovno preuzima vec kesirane datoteke.

Zasto: Kazalo daje naslov, vrstu akta i donositelja za CIJELI raspon 1990-danas,
dakle i za 1990-2014 gdje ELI/RDF ne postoji. Ujedno zamjenjuje enumeraciju preko
search.aspx (94 MB kesa po godini) s jednim zahtjevom.

Primjeri:
  uv run python scripts/00_katalog.py                    # 1990..tekuca
  uv run python scripts/00_katalog.py --od 2020 --do 2026
  uv run python scripts/00_katalog.py --procjena         # samo izvjestaj iz baze
"""

import argparse
import csv
import datetime
import io
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from src import db, nn_client

BASE = "https://narodne-novine.nn.hr"

# Stupci u Kazalu (redoslijed fiksan, imena provjerena 2026-07-20)
STUPCI = {
    "izdanje": "Izdanje",
    "clanak": "Broj dokumenta",
    "naslov": "Naziv dokumenta",
    "vrsta": "Vrsta dokumenta",
    "podvrsta": "Podvrsta dokumenta (ako je dokument razvrstan u vrstu ostalo)",
    "izmjena": "Cjeloviti dokument/izmjene/dopune/ukinut",
    "donositelj": "Donositelj dokumenta",
    "eli": "Poveznica",
}


def kazalo_url(godina: int) -> str:
    return f"{BASE}/get_index_file.aspx?year={godina}&type=csv"


def parse_izdanje(vrijednost: str, godina: int) -> int | None:
    """'NN 1/1995' -> 1. Vraca None ako oblik ne odgovara (ne izmisljamo podatke)."""
    dio = vrijednost.strip().removeprefix("NN").strip()
    broj = dio.split("/", 1)[0].strip()
    return int(broj) if broj.isdigit() else None


def ucitaj_godinu(conn, godina: int, serija: str = "sluzbeni") -> tuple[int, int]:
    """Preuzmi (ili procitaj iz kesa) Kazalo za godinu i upsertaj u `katalog`."""
    cache = nn_client.RAW_DIR / "kazalo" / f"{serija}_{godina}.csv"
    sirovo = nn_client.fetch_cached(kazalo_url(godina), cache)
    tekst = sirovo.decode("utf-8-sig", "replace")

    citac = csv.DictReader(io.StringIO(tekst), delimiter="\t")
    ok, preskoceno = 0, 0
    for red in citac:
        broj = parse_izdanje(red.get(STUPCI["izdanje"], ""), godina)
        clanak = (red.get(STUPCI["clanak"]) or "").strip()
        if broj is None or not clanak:
            preskoceno += 1
            continue
        podvrsta = (red.get(STUPCI["podvrsta"]) or "").strip()
        db.upsert_katalog(conn, {
            "serija": serija,
            "godina": godina,
            "broj": broj,
            "clanak": clanak,  # STRING: '0000' i rijetki oblici sa slovom
            "naslov": (red.get(STUPCI["naslov"]) or "").strip() or None,
            "vrsta": (red.get(STUPCI["vrsta"]) or "").strip() or None,
            "podvrsta": podvrsta if podvrsta not in ("", "-") else None,
            "izmjena": (red.get(STUPCI["izmjena"]) or "").strip() or None,
            "donositelj": (red.get(STUPCI["donositelj"]) or "").strip() or None,
            "eli": (red.get(STUPCI["eli"]) or "").strip() or None,
        })
        ok += 1
    conn.commit()
    return ok, preskoceno


# --- procjene ---------------------------------------------------------------
# Izmjereno na 2025. (2.404 akta, 158 izdanja) — vidi docs/04-backfill-runbook.md
SEK_PO_AKTU_HTML = 0.71
SEK_PO_AKTU_RDF = 0.62
KB_PO_AKTU_HTML = 73
KB_PO_AKTU_RDF = 4.5
PRVA_ELI_GODINA = 2015  # prije toga RDF ne postoji (docs/01 §0)


def izvjestaj(conn):
    redovi = conn.execute(
        """SELECT godina, COUNT(*) n, COUNT(DISTINCT broj) izdanja
           FROM katalog GROUP BY godina ORDER BY godina DESC"""
    ).fetchall()
    if not redovi:
        print("Katalog je prazan — pokreni bez --procjena.")
        return

    print(f"\n{'godina':>7} {'izdanja':>8} {'akata':>8} {'sati':>7} {'GB':>7}  {'RDF?':>5}")
    print("-" * 50)
    uk_akata = uk_izdanja = 0
    uk_sati = uk_gb = 0.0
    for r in redovi:
        ima_rdf = r["godina"] >= PRVA_ELI_GODINA
        sek = r["n"] * (SEK_PO_AKTU_HTML + (SEK_PO_AKTU_RDF if ima_rdf else 0))
        kb = r["n"] * (KB_PO_AKTU_HTML + (KB_PO_AKTU_RDF if ima_rdf else 0))
        sati, gb = sek / 3600, kb / 1024 / 1024
        print(f"{r['godina']:>7} {r['izdanja']:>8} {r['n']:>8} {sati:>7.2f} {gb:>7.3f}  "
              f"{'da' if ima_rdf else 'NE':>5}")
        uk_akata += r["n"]; uk_izdanja += r["izdanja"]
        uk_sati += sati; uk_gb += gb

    print("-" * 50)
    print(f"{'UKUPNO':>7} {uk_izdanja:>8} {uk_akata:>8} {uk_sati:>7.2f} {uk_gb:>7.3f}")
    print(f"\nGodina u katalogu: {len(redovi)} ({redovi[-1]['godina']}–{redovi[0]['godina']})")
    print(f"Akata bez ELI/RDF (< {PRVA_ELI_GODINA}): "
          f"{sum(r['n'] for r in redovi if r['godina'] < PRVA_ELI_GODINA):,}")
    print(f"\nProcjene su za dohvat HTML-a (+RDF gdje postoji) uz MIN_INTERVAL="
          f"{nn_client.MIN_INTERVAL}s.")
    print("Ne ukljucuju search.aspx kes — Kazalo ga zamjenjuje (usteda ~94 MB/god).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--od", type=int, default=1990)
    ap.add_argument("--do", type=int, default=datetime.date.today().year)
    ap.add_argument("--serija", default="sluzbeni", choices=["sluzbeni", "medunarodni"])
    ap.add_argument("--procjena", action="store_true", help="samo izvjestaj iz baze")
    args = ap.parse_args()

    conn = db.connect()
    if not args.procjena:
        run_id = db.start_run(conn, None, "katalog")
        uk, uk_presk = 0, 0
        for g in range(args.od, args.do + 1):
            try:
                ok, presk = ucitaj_godinu(conn, g, args.serija)
            except nn_client.NotFound:
                print(f"{g}: Kazalo ne postoji (404) — preskacem", file=sys.stderr)
                continue
            uk += ok; uk_presk += presk
            print(f"{g}: {ok} propisa" + (f" ({presk} redaka preskoceno)" if presk else ""))
        db.finish_run(conn, run_id, uk, uk_presk, f"{args.od}-{args.do} {args.serija}")
        print(f"\nGotovo: {uk} propisa u katalogu.")

    izvjestaj(conn)


if __name__ == "__main__":
    main()
