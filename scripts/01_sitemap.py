"""Enumeracija akata iz sluzbenih sitemapova + metapodaci iz kataloga.

Zamjenjuje 01_enumerate.py (struganje search.aspx-a). Prednosti:
  - 1 zahtjev po IZDANJU umjesto po izdanju + 600 KB HTML-a (sitemap je nekoliko KB)
  - daje MJESEC, koji katalog nema a `full/` URL ga trazi
  - daje broj akta u izvornom obliku, s paddingom ('0000') — vise nema rucnog krpanja
  - popis izdanja dolazi iz kataloga, pa nema heuristike "3 prazna broja zaredom"
  - naslov, tip akta i donositelj se odmah pune iz kataloga; za 1990-2014 je to
    JEDINI izvor tih podataka jer ELI/RDF postoji tek od 2015. (docs/01 §0)

Izvor:  https://narodne-novine.nn.hr/sitemap_1_{godina}_{broj}.xml
        (kaskadni sitemapovi s /sitemap.xml; sluzbeno namijenjeni crawlerima)
Cache:  data/raw/nn/{godina}/sitemap/{broj}.xml — nikad se ne brise.

Preduvjet: katalog za tu godinu (uv run python scripts/00_katalog.py --od G --do G).

Garancija idempotentnosti: upsert po `eli`; ponovno pokretanje ne duplicira nista
i ne preuzima vec kesirane sitemapove.

  uv run python scripts/01_sitemap.py --godina 2023
"""

import argparse
import re
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from src import db, nn_client

BASE = "https://narodne-novine.nn.hr"
# clanci/sluzbeni/{YYYY}_{MM}_{BROJ}_{CLANAK}.html — clanak ostaje STRING (padding!)
LINK_RE = re.compile(r"clanci/sluzbeni/(\d{4})_(\d{2})_(\d+)_([0-9A-Za-z]+)\.html")

# Kazalo koristi male pocetne slove ('zakon'), RDF velika ('ZAKON') — ujednacujemo na RDF oblik.
def normaliziraj_vrstu(v: str | None) -> str | None:
    if not v or v == "-":
        return None
    return v.strip().upper().replace(" ", "_")


def sitemap_url(godina: int, broj: int) -> str:
    return f"{BASE}/sitemap_1_{godina}_{broj}.xml"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--godina", type=int, required=True)
    args = ap.parse_args()
    g = args.godina

    conn = db.connect()
    izdanja = [r[0] for r in conn.execute(
        "SELECT DISTINCT broj FROM katalog WHERE godina=? AND serija='sluzbeni' ORDER BY broj",
        (g,))]
    if not izdanja:
        print(f"Katalog za {g}. je prazan. Prvo: uv run python scripts/00_katalog.py "
              f"--od {g} --do {g}", file=sys.stderr)
        sys.exit(1)

    # metapodaci iz kataloga, kljuc (broj, clanak) — clanak kao STRING
    kat = {(r["broj"], r["clanak"]): r for r in conn.execute(
        """SELECT broj, clanak, naslov, vrsta, donositelj FROM katalog
           WHERE godina=? AND serija='sluzbeni'""", (g,))}

    run_id = db.start_run(conn, g, "sitemap")
    ukupno, bez_kataloga, praznih = 0, 0, 0

    for broj in izdanja:
        cache = nn_client.RAW_DIR / str(g) / "sitemap" / f"{broj}.xml"
        try:
            xml = nn_client.fetch_cached(sitemap_url(g, broj), cache).decode("utf-8", "replace")
        except nn_client.NotFound:
            print(f"NN {g}/{broj}: sitemap ne postoji (404)", file=sys.stderr)
            praznih += 1
            continue

        nadjeni = sorted({
            (int(mm), int(bb), cc)
            for gg, mm, bb, cc in LINK_RE.findall(xml)
            if int(gg) == g and int(bb) == broj
        }, key=lambda t: (len(t[2]), t[2]))
        if not nadjeni:
            print(f"NN {g}/{broj}: sitemap bez akata", file=sys.stderr)
            praznih += 1
            cache.unlink(missing_ok=True)  # ne kesiraj prazan odgovor
            continue

        mjesec = nadjeni[0][0]
        db.upsert_izdanje(conn, g, broj, mjesec, len(nadjeni))
        for mm, bb, cc in nadjeni:
            meta = kat.get((bb, cc))
            if meta is None:
                bez_kataloga += 1
            db.upsert_akt(conn, {
                "eli": f"sluzbeni/{g}/{bb}/{cc}",
                "godina": g, "broj": bb, "clanak": cc, "mjesec": mm,
                "naslov": meta["naslov"] if meta else None,
                "tip_akta": normaliziraj_vrstu(meta["vrsta"]) if meta else None,
            })
        conn.commit()
        ukupno += len(nadjeni)
        print(f"NN {g}/{broj} (mjesec {mjesec:02d}): {len(nadjeni)} akata")

    db.finish_run(conn, run_id, ukupno, bez_kataloga,
                  f"{len(izdanja)} izdanja, {praznih} praznih sitemapova")
    print(f"\nGotovo: {ukupno} akata iz {len(izdanja) - praznih} izdanja za {g}.")
    if bez_kataloga:
        print(f"NAPOMENA: {bez_kataloga} akata nije u katalogu (ostaju bez naslova/tipa "
              f"dok ih ne popuni RDF).")
    u_katalogu = len(kat)
    if ukupno != u_katalogu:
        print(f"NAPOMENA: sitemap {ukupno} vs katalog {u_katalogu} akata — razlika "
              f"{ukupno - u_katalogu:+d}. Provjeri 06_stats.")


if __name__ == "__main__":
    main()
