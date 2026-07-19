"""Enumeracija akata jedne godine preko stranica pretrage.

Izvor: search.aspx po (godina, broj) — docs/01 §4. Cache: data/raw/nn/{G}/search/{broj}.html.
Idempotentno: upsert izdanja/akti; postojeci cache se ne dohvaca ponovno.
Stop: 3 uzastopna prazna broja izdanja.
"""

import argparse
import re
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from src import db, nn_client

LINK_RE = re.compile(r"clanci/sluzbeni/(\d{4})_(\d{2})_(\d+)_(\d+)\.html")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--godina", type=int, required=True)
    ap.add_argument("--max-broj", type=int, default=250, help="sigurnosna granica petlje")
    args = ap.parse_args()
    g = args.godina

    conn = db.connect()
    run_id = db.start_run(conn, g, "enumeracija")
    ukupno, prazni_zaredom, greske = 0, 0, 0

    for broj in range(1, args.max_broj + 1):
        cache = nn_client.RAW_DIR / str(g) / "search" / f"{broj}.html"
        html = nn_client.fetch_cached(nn_client.search_url(g, broj), cache).decode(
            "utf-8", "replace"
        )
        found = sorted(
            {
                (int(gg), int(mm), int(bb), int(cc))
                for gg, mm, bb, cc in LINK_RE.findall(html)
                if int(gg) == g and int(bb) == broj
            }
        )
        if not found:
            prazni_zaredom += 1
            # prazan broj ne cachiramo trajno — izdanje mozda jos nije objavljeno
            cache.unlink(missing_ok=True)
            if prazni_zaredom >= 3:
                break
            continue
        prazni_zaredom = 0
        if len(found) >= 200:
            print(f"UPOZORENJE: broj {broj} ima >=200 akata — provjeri paginaciju!", file=sys.stderr)
            greske += 1
        mjesec = found[0][1]
        db.upsert_izdanje(conn, g, broj, mjesec, len(found))
        for _, mm, bb, cc in found:
            db.upsert_akt(conn, {
                "eli": f"sluzbeni/{g}/{bb}/{cc}",
                "godina": g, "broj": bb, "clanak": cc, "mjesec": mm,
            })
        conn.commit()
        ukupno += len(found)
        print(f"NN {g}/{broj} (mjesec {mjesec:02d}): {len(found)} akata")

    db.finish_run(conn, run_id, ukupno, greske, f"zadnji provjereni broj={broj}")
    print(f"\nGotovo: {ukupno} akata enumerirano za {g}.")


if __name__ == "__main__":
    main()
