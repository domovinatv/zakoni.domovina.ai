"""Migracija tablice `akti`: makni UNIQUE(godina, clanak), prebaci clanak na TEXT.

Zasto (docs/05-plan-punog-backfilla.md §5, docs/01 §1 i §11):

1. Broj akta NIJE jedinstven unutar godine. Kazalo pokazuje 69 slucajeva kroz arhiv,
   od toga 57 u 2008. (NN 100/2008 br. 3042 je Pravilnik, NN 101/2008 br. 3042 je
   Rjesenje — dva razlicita akta). Sa zatecenim UNIQUE(godina, clanak) backfill bi
   na 2008. pukao na IntegrityError.
2. Broj akta nije cijeli broj: `sluzbeni/2024/102/0000` je stvarna Odluka Ustavnog
   suda, a ELI radi samo s punim paddingom (/0000/rdf -> 200, /0/rdf -> 404).
   Sluzbena API dokumentacija kaze da act_num "vrlo rijetko sadrzi slovo".

`CREATE TABLE IF NOT EXISTS` ne mijenja zatecenu tablicu, pa je potrebna rucna
migracija: nova tablica -> kopija podataka -> zamjena. Strani kljuc iz akt_tekst
(akt_id) se cuva jer zadrzavamo iste id-eve.

Idempotentno: ako migracija vec provedena (nema UNIQUE(godina, clanak) i clanak je
TEXT), skripta samo javi i izadje.

  uv run python scripts/09_migracija_akti.py [--dry-run]
"""

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from src import db

NOVA_TABLICA = """
CREATE TABLE akti_nova (
  id            INTEGER PRIMARY KEY,
  eli           TEXT UNIQUE NOT NULL,
  godina        INTEGER NOT NULL,
  broj          INTEGER NOT NULL,
  clanak        TEXT NOT NULL,
  mjesec        INTEGER,
  naslov        TEXT,
  tip_akta      TEXT,
  donositelj_nn_id INTEGER,
  datum_akta    TEXT,
  datum_objave  TEXT,
  status        TEXT NOT NULL DEFAULT 'enumeriran',
  created_at    TEXT DEFAULT (datetime('now')),
  updated_at    TEXT DEFAULT (datetime('now'))
);
"""


def treba_migraciju(conn) -> tuple[bool, str]:
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='akti'"
    ).fetchone()
    if not sql:
        return False, "tablica `akti` ne postoji"
    ddl = sql[0]
    razlozi = []
    if "UNIQUE (godina, clanak)" in ddl or "UNIQUE(godina, clanak)" in ddl:
        razlozi.append("ima UNIQUE(godina, clanak)")
    if "clanak        INTEGER" in ddl or "clanak INTEGER" in ddl:
        razlozi.append("clanak je INTEGER")
    return bool(razlozi), ", ".join(razlozi) or "vec migrirano"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = db.connect()
    treba, razlog = treba_migraciju(conn)
    prije = conn.execute("SELECT COUNT(*) FROM akti").fetchone()[0]
    print(f"Zatecena tablica: {razlog}; {prije} akata.")

    if not treba:
        print("Migracija nije potrebna.")
        return
    if args.dry_run:
        print("--dry-run: nista nije promijenjeno.")
        return

    conn.execute("PRAGMA foreign_keys=OFF")
    with conn:  # jedna transakcija — ili sve prodje ili nista
        conn.execute("DROP TABLE IF EXISTS akti_nova")
        conn.executescript(NOVA_TABLICA)
        conn.execute(
            """INSERT INTO akti_nova (id, eli, godina, broj, clanak, mjesec, naslov,
                                      tip_akta, donositelj_nn_id, datum_akta, datum_objave,
                                      status, created_at, updated_at)
               SELECT id, eli, godina, broj, CAST(clanak AS TEXT), mjesec, naslov,
                      tip_akta, donositelj_nn_id, datum_akta, datum_objave,
                      status, created_at, updated_at
               FROM akti"""
        )
        conn.execute("DROP TABLE akti")
        conn.execute("ALTER TABLE akti_nova RENAME TO akti")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_akti_godina ON akti (godina, broj, clanak)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_akti_status ON akti (status)")
    conn.execute("PRAGMA foreign_keys=ON")

    poslije = conn.execute("SELECT COUNT(*) FROM akti").fetchone()[0]
    siroci = conn.execute(
        "SELECT COUNT(*) FROM akt_tekst t LEFT JOIN akti a ON a.id=t.akt_id WHERE a.id IS NULL"
    ).fetchone()[0]
    print(f"Migrirano: {prije} -> {poslije} akata; akt_tekst bez para: {siroci}")
    if poslije != prije or siroci:
        print("UPOZORENJE: brojevi se ne slazu — provjeri prije nastavka!", file=sys.stderr)
        sys.exit(1)
    print("Gotovo. Sada su moguci akti s istim brojem u razlicitim izdanjima (npr. 2008).")


if __name__ == "__main__":
    main()
