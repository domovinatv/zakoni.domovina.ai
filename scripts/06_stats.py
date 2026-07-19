"""Kontrolni izvjestaj: statusi, tipovi, rupe u sekvenci clanaka, veze/oznake.

Exit code 1 ako postoje rupe u sekvenci ili akti sa status=greska (za orkestrator).
"""

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from src import db


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--godina", type=int, default=None)
    args = ap.parse_args()

    conn = db.connect()
    where, params = ("WHERE godina = ?", (args.godina,)) if args.godina else ("", ())
    godine = [r[0] for r in conn.execute(
        f"SELECT DISTINCT godina FROM akti {where} ORDER BY godina DESC", params)]
    problem = False

    for g in godine:
        n_izd = conn.execute("SELECT COUNT(*) FROM izdanja WHERE godina=?", (g,)).fetchone()[0]
        statusi = dict(conn.execute(
            "SELECT status, COUNT(*) FROM akti WHERE godina=? GROUP BY status", (g,)))
        ukupno = sum(statusi.values())
        clanci = [r[0] for r in conn.execute(
            "SELECT clanak FROM akti WHERE godina=? ORDER BY clanak", (g,))]
        rupe = sorted(set(range(1, max(clanci) + 1)) - set(clanci)) if clanci else []
        n_veze = conn.execute(
            "SELECT COUNT(*) FROM akt_veze WHERE from_eli LIKE ?", (f"sluzbeni/{g}/%",)).fetchone()[0]
        n_ozn = conn.execute(
            "SELECT COUNT(*) FROM oznake WHERE akt_eli LIKE ?", (f"sluzbeni/{g}/%",)).fetchone()[0]
        top_tip = conn.execute(
            """SELECT tip_akta, COUNT(*) c FROM akti WHERE godina=? AND tip_akta IS NOT NULL
               GROUP BY tip_akta ORDER BY c DESC LIMIT 5""", (g,)).fetchall()

        print(f"=== {g}: {n_izd} izdanja, {ukupno} akata ===")
        print(f"  statusi: {statusi}")
        print(f"  top tipovi: {[f'{t}:{c}' for t, c in top_tip]}")
        print(f"  veze: {n_veze}, oznake: {n_ozn}")
        if rupe:
            print(f"  !! RUPE u sekvenci clanaka ({len(rupe)}): {rupe[:20]}{'...' if len(rupe) > 20 else ''}")
            problem = True
        if statusi.get("greska"):
            print(f"  !! {statusi['greska']} akata sa statusom greska")
            problem = True

    sys.exit(1 if problem else 0)


if __name__ == "__main__":
    main()
