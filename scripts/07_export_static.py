"""Statički export SQLite -> JSON za frontend + CSV otvoreni podaci.

Izlaz:
  frontend/public/data/stats.json           — brojevi po godini/tipu (naslovnica)
  frontend/public/data/godine/{G}.json      — lista akata godine (bez teksta)
  frontend/public/data/akt/{G}/{B}_{C}.json — detalj akta (tekst, veze, oznake)
  frontend/public/data/manifest.json        — generated_at, schema_version, raspon
  data/export/*.csv                         — akti, veze, oznake, institucije (bez teksta)

Idempotentno i reproducibilno: uvijek prebrise izlaz iz trenutnog stanja baze.
Exporta samo akte sa status='parsiran'.
"""

import csv
import json
import pathlib
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import db

SCHEMA_VERSION = 1
ROOT = db.ROOT
DATA_DIR = ROOT / "frontend" / "public" / "data"
CSV_DIR = ROOT / "data" / "export"


def clean(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def main():
    conn = db.connect()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    akti = [dict(r) for r in conn.execute(
        """SELECT a.*, i.naziv AS donositelj
           FROM akti a LEFT JOIN institucije i ON i.nn_id = a.donositelj_nn_id
           WHERE a.status = 'parsiran'
           ORDER BY a.godina DESC, a.clanak DESC"""
    )]
    godine = sorted({a["godina"] for a in akti}, reverse=True)

    # --- godine/{G}.json + akt/{G}/{B}_{C}.json
    for g in godine:
        ga = [a for a in akti if a["godina"] == g]
        (DATA_DIR / "godine").mkdir(exist_ok=True)
        with open(DATA_DIR / "godine" / f"{g}.json", "w", encoding="utf-8") as f:
            json.dump([clean({
                "eli": a["eli"], "broj": a["broj"], "clanak": a["clanak"],
                "naslov": a["naslov"], "tip": a["tip_akta"],
                "datum": a["datum_objave"], "donositelj": a["donositelj"],
            }) for a in ga], f, ensure_ascii=False, separators=(",", ":"))

        akt_dir = DATA_DIR / "akt" / str(g)
        akt_dir.mkdir(parents=True, exist_ok=True)
        for a in ga:
            tekst = conn.execute(
                "SELECT tekst FROM akt_tekst WHERE akt_id=?", (a["id"],)).fetchone()
            veze = [dict(r) for r in conn.execute(
                "SELECT predikat, to_eli FROM akt_veze WHERE from_eli=?", (a["eli"],))]
            veze_na = [dict(r) for r in conn.execute(
                "SELECT predikat, from_eli FROM akt_veze WHERE to_eli=?", (a["eli"],))]
            oznake = [dict(r) for r in conn.execute(
                "SELECT vrsta, uri, label FROM oznake WHERE akt_eli=?", (a["eli"],))]
            with open(akt_dir / f"{a['broj']}_{a['clanak']}.json", "w", encoding="utf-8") as f:
                json.dump(clean({
                    "eli": a["eli"], "godina": g, "broj": a["broj"], "clanak": a["clanak"],
                    "naslov": a["naslov"], "tip": a["tip_akta"], "donositelj": a["donositelj"],
                    "datum_akta": a["datum_akta"], "datum_objave": a["datum_objave"],
                    "tekst": tekst["tekst"] if tekst else None,
                    "veze": veze, "veze_na_ovaj": veze_na,
                    "oznake": [clean(o) for o in oznake],
                }), f, ensure_ascii=False, separators=(",", ":"))

    # --- stats.json
    stats = {
        "godine": [{
            "godina": g,
            "akata": sum(1 for a in akti if a["godina"] == g),
            "izdanja": conn.execute(
                "SELECT COUNT(*) FROM izdanja WHERE godina=?", (g,)).fetchone()[0],
        } for g in godine],
        "tipovi": dict(conn.execute(
            """SELECT tip_akta, COUNT(*) FROM akti
               WHERE status='parsiran' AND tip_akta IS NOT NULL
               GROUP BY tip_akta ORDER BY COUNT(*) DESC""")),
        "ukupno": len(akti),
    }
    (DATA_DIR / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # --- manifest.json
    (DATA_DIR / "manifest.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "schema_version": SCHEMA_VERSION,
        "godine": godine,
        "ukupno_akata": len(akti),
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # --- CSV otvoreni podaci
    def dump_csv(name: str, rows, header):
        with open(CSV_DIR / name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    dump_csv("akti.csv",
             [(a["eli"], a["godina"], a["broj"], a["clanak"], a["naslov"], a["tip_akta"],
               a["donositelj_nn_id"], a["donositelj"], a["datum_akta"], a["datum_objave"])
              for a in akti],
             ["eli", "godina", "broj", "clanak", "naslov", "tip_akta",
              "donositelj_nn_id", "donositelj", "datum_akta", "datum_objave"])
    dump_csv("akt_veze.csv", conn.execute("SELECT from_eli, predikat, to_eli FROM akt_veze"),
             ["from_eli", "predikat", "to_eli"])
    dump_csv("oznake.csv", conn.execute("SELECT akt_eli, vrsta, uri, label FROM oznake"),
             ["akt_eli", "vrsta", "uri", "label"])
    dump_csv("institucije.csv", conn.execute("SELECT nn_id, naziv FROM institucije"),
             ["nn_id", "naziv"])

    print(f"Export gotov: {len(akti)} akata, godine {godine or '—'}")
    print(f"  JSON: {DATA_DIR}")
    print(f"  CSV:  {CSV_DIR}")


if __name__ == "__main__":
    main()
