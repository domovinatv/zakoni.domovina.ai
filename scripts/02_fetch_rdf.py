"""Dohvat ELI RDF metapodataka za enumerirane akte (anti-join po statusu).

Cache: data/raw/nn/{G}/rdf/{broj}_{clanak}.rdf. Idempotentno.
Robots-disallowed -> status=skipped_robots; 404/greska -> status=greska.
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
        "SELECT eli, broj, clanak FROM akti WHERE godina=? AND status='enumeriran' ORDER BY CAST(clanak AS INTEGER), clanak"
        + (f" LIMIT {int(args.limit)}" if args.limit else ""),
        (g,),
    ).fetchall()
    run_id = db.start_run(conn, g, "rdf")
    ok = err = 0
    for i, a in enumerate(akti, 1):
        url = nn_client.rdf_url(g, a["broj"], a["clanak"])
        if nn_client.is_disallowed(url):
            db.set_status(conn, a["eli"], "skipped_robots")
            continue
        try:
            nn_client.fetch_cached(url, nn_client.RAW_DIR / str(g) / "rdf" / f"{a['broj']}_{a['clanak']}.rdf")
            db.set_status(conn, a["eli"], "rdf_ok")
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
    print(f"RDF gotovo: {ok} ok, {err} gresaka od {len(akti)}.")


if __name__ == "__main__":
    main()
