"""Dohvat "full" HTML-a akata (anti-join: status=rdf_ok).

Cache: data/raw/nn/{G}/html/{broj}_{clanak}.html. Idempotentno.
PDF-ovi se NE preuzimaju u prvom prolazu (docs/01 §2).
"""

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from src import db, nn_client


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--godina", type=int, required=True)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    g = args.godina

    conn = db.connect()
    akti = conn.execute(
        "SELECT eli, broj, clanak, mjesec FROM akti WHERE godina=? AND status='rdf_ok' ORDER BY clanak"
        + (f" LIMIT {int(args.limit)}" if args.limit else ""),
        (g,),
    ).fetchall()
    run_id = db.start_run(conn, g, "html")
    ok = err = 0
    for i, a in enumerate(akti, 1):
        url = nn_client.full_html_url(g, a["mjesec"], a["broj"], a["clanak"])
        if nn_client.is_disallowed(url):
            db.set_status(conn, a["eli"], "skipped_robots")
            continue
        try:
            nn_client.fetch_cached(url, nn_client.RAW_DIR / str(g) / "html" / f"{a['broj']}_{a['clanak']}.html")
            db.set_status(conn, a["eli"], "html_ok")
            ok += 1
        except (nn_client.NotFound, nn_client.FetchError) as exc:
            print(f"GRESKA {a['eli']}: {exc}", file=sys.stderr)
            db.set_status(conn, a["eli"], "greska")
            err += 1
        if i % 25 == 0:
            conn.commit()
            print(f"  {i}/{len(akti)}")
    conn.commit()
    db.finish_run(conn, run_id, ok, err)
    print(f"HTML gotovo: {ok} ok, {err} gresaka od {len(akti)}.")


if __name__ == "__main__":
    main()
