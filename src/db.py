"""SQLite baza (data/zakoni.db) — shema iz docs/02-arhitektura.md §4.

Idempotentnost: upsert po `eli`; veze/oznake INSERT OR IGNORE. Sve skripte smiju
se pokretati vise puta bez stete.
"""

from __future__ import annotations

import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "zakoni.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS izdanja (
  godina        INTEGER NOT NULL,
  broj          INTEGER NOT NULL,
  mjesec        INTEGER,
  broj_akata    INTEGER,
  created_at    TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (godina, broj)
);

CREATE TABLE IF NOT EXISTS akti (
  id            INTEGER PRIMARY KEY,
  eli           TEXT UNIQUE NOT NULL,
  godina        INTEGER NOT NULL,
  broj          INTEGER NOT NULL,
  clanak        INTEGER NOT NULL,
  mjesec        INTEGER,
  naslov        TEXT,
  tip_akta      TEXT,
  donositelj_nn_id INTEGER,
  datum_akta    TEXT,
  datum_objave  TEXT,
  status        TEXT NOT NULL DEFAULT 'enumeriran',
  created_at    TEXT DEFAULT (datetime('now')),
  updated_at    TEXT DEFAULT (datetime('now'))
  -- NEMA UNIQUE(godina, clanak)! Broj akta NIJE jedinstven unutar godine:
  -- npr. 2008 ima 57 brojeva koji se ponavljaju u dva izdanja
  -- (NN 100/2008 br. 3042 != NN 101/2008 br. 3042). Jedinstven je samo `eli`,
  -- koji nosi (godina, broj, clanak). Vidi docs/01-izvor-podataka-nn.md §1.
);

CREATE TABLE IF NOT EXISTS akt_tekst (
  akt_id        INTEGER PRIMARY KEY REFERENCES akti(id),
  tekst         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS akt_veze (
  from_eli      TEXT NOT NULL,
  predikat      TEXT NOT NULL,
  to_eli        TEXT NOT NULL,
  UNIQUE (from_eli, predikat, to_eli)
);

CREATE TABLE IF NOT EXISTS institucije (
  nn_id         INTEGER PRIMARY KEY,
  naziv         TEXT
);

CREATE TABLE IF NOT EXISTS oznake (
  akt_eli       TEXT NOT NULL,
  vrsta         TEXT NOT NULL,
  uri           TEXT NOT NULL,
  label         TEXT,
  UNIQUE (akt_eli, vrsta, uri)
);

CREATE TABLE IF NOT EXISTS ingest_runs (
  id            INTEGER PRIMARY KEY,
  godina        INTEGER,
  faza          TEXT,
  started_at    TEXT,
  finished_at   TEXT,
  ok_count      INTEGER,
  err_count     INTEGER,
  napomena      TEXT
);

CREATE TABLE IF NOT EXISTS analize (
  id            INTEGER PRIMARY KEY,
  akt_eli       TEXT NOT NULL,
  vrsta         TEXT NOT NULL DEFAULT 'magisterium',
  model         TEXT,
  ocjena        TEXT,
  sazetak       TEXT,
  analiza_md    TEXT,
  created_at    TEXT DEFAULT (datetime('now')),
  UNIQUE (akt_eli, vrsta)
);

-- Katalog iz sluzbenog Kazala (get_index_file.aspx), 1990->danas.
-- Autoritativan popis SVIH propisa po godini: naslov, vrsta, donositelj.
-- Za 1990-2014 je to jedini izvor tih metapodataka (RDF postoji tek od 2015).
-- Vidi docs/01-izvor-podataka-nn.md §12.
CREATE TABLE IF NOT EXISTS katalog (
  serija        TEXT NOT NULL DEFAULT 'sluzbeni',
  godina        INTEGER NOT NULL,
  broj          INTEGER NOT NULL,       -- broj izdanja
  clanak        TEXT NOT NULL,          -- broj dokumenta; STRING! ('0000', rijetko sa slovom)
  naslov        TEXT,
  vrsta         TEXT,                   -- zakon, odluka, pravilnik, uredba, rjesenje, ostalo
  podvrsta      TEXT,                   -- popunjeno kad je vrsta 'ostalo'
  izmjena       TEXT,                   -- cjeloviti akt / ukidanje / izmjene / dopune
  donositelj    TEXT,
  eli           TEXT,
  -- kljuc ukljucuje `broj` jer clanak nije jedinstven unutar godine (vidi `akti`)
  UNIQUE (serija, godina, broj, clanak)
);

CREATE INDEX IF NOT EXISTS idx_akti_godina ON akti (godina, broj, clanak);
CREATE INDEX IF NOT EXISTS idx_akti_status ON akti (status);
CREATE INDEX IF NOT EXISTS idx_katalog_godina ON katalog (godina, broj);
"""


def connect(path: pathlib.Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    # Bez ovoga svaki paralelni pisac odmah puca na "database is locked" —
    # npr. 00_katalog.py dok 10_backfill.py jos vrti neku godinu.
    conn.execute("PRAGMA busy_timeout=60000")
    conn.executescript(SCHEMA)
    return conn


def upsert_izdanje(conn, godina: int, broj: int, mjesec: int | None, broj_akata: int | None):
    conn.execute(
        """INSERT INTO izdanja (godina, broj, mjesec, broj_akata) VALUES (?,?,?,?)
           ON CONFLICT(godina, broj) DO UPDATE SET
             mjesec = COALESCE(excluded.mjesec, izdanja.mjesec),
             broj_akata = COALESCE(excluded.broj_akata, izdanja.broj_akata)""",
        (godina, broj, mjesec, broj_akata),
    )


def upsert_akt(conn, akt: dict) -> int:
    """Upsert po `eli`. Ne-None vrijednosti pobjedjuju, status se NE dira ako akt postoji."""
    row = conn.execute(
        """INSERT INTO akti (eli, godina, broj, clanak, mjesec, naslov, tip_akta,
                             donositelj_nn_id, datum_akta, datum_objave)
           VALUES (:eli, :godina, :broj, :clanak, :mjesec, :naslov, :tip_akta,
                   :donositelj_nn_id, :datum_akta, :datum_objave)
           ON CONFLICT(eli) DO UPDATE SET
             mjesec = COALESCE(excluded.mjesec, akti.mjesec),
             naslov = COALESCE(excluded.naslov, akti.naslov),
             tip_akta = COALESCE(excluded.tip_akta, akti.tip_akta),
             donositelj_nn_id = COALESCE(excluded.donositelj_nn_id, akti.donositelj_nn_id),
             datum_akta = COALESCE(excluded.datum_akta, akti.datum_akta),
             datum_objave = COALESCE(excluded.datum_objave, akti.datum_objave),
             updated_at = datetime('now')
           RETURNING id""",
        {
            "eli": akt["eli"], "godina": akt["godina"], "broj": akt["broj"],
            "clanak": akt["clanak"], "mjesec": akt.get("mjesec"),
            "naslov": akt.get("naslov"), "tip_akta": akt.get("tip_akta"),
            "donositelj_nn_id": akt.get("donositelj_nn_id"),
            "datum_akta": akt.get("datum_akta"), "datum_objave": akt.get("datum_objave"),
        },
    ).fetchone()
    return row[0]


def set_status(conn, eli: str, status: str):
    conn.execute(
        "UPDATE akti SET status = ?, updated_at = datetime('now') WHERE eli = ?",
        (status, eli),
    )


def set_tekst(conn, akt_id: int, tekst: str):
    conn.execute(
        "INSERT INTO akt_tekst (akt_id, tekst) VALUES (?,?) "
        "ON CONFLICT(akt_id) DO UPDATE SET tekst = excluded.tekst",
        (akt_id, tekst),
    )


def insert_veza(conn, from_eli: str, predikat: str, to_eli: str):
    conn.execute(
        "INSERT OR IGNORE INTO akt_veze (from_eli, predikat, to_eli) VALUES (?,?,?)",
        (from_eli, predikat, to_eli),
    )


def insert_oznaka(conn, akt_eli: str, vrsta: str, uri: str, label: str | None = None):
    conn.execute(
        "INSERT OR IGNORE INTO oznake (akt_eli, vrsta, uri, label) VALUES (?,?,?,?)",
        (akt_eli, vrsta, uri, label),
    )


def upsert_institucija(conn, nn_id: int, naziv: str | None):
    conn.execute(
        """INSERT INTO institucije (nn_id, naziv) VALUES (?,?)
           ON CONFLICT(nn_id) DO UPDATE SET
             naziv = COALESCE(institucije.naziv, excluded.naziv)""",
        (nn_id, naziv),
    )


def start_run(conn, godina: int | None, faza: str) -> int:
    row = conn.execute(
        "INSERT INTO ingest_runs (godina, faza, started_at) VALUES (?,?,datetime('now')) RETURNING id",
        (godina, faza),
    ).fetchone()
    conn.commit()
    return row[0]


def finish_run(conn, run_id: int, ok: int, err: int, napomena: str | None = None):
    conn.execute(
        "UPDATE ingest_runs SET finished_at = datetime('now'), ok_count = ?, err_count = ?, napomena = ? WHERE id = ?",
        (ok, err, napomena, run_id),
    )
    conn.commit()


def upsert_katalog(conn, red: dict):
    """Upsert jednog retka Kazala. Idempotentno po (serija, godina, clanak)."""
    conn.execute(
        """INSERT INTO katalog (serija, godina, broj, clanak, naslov, vrsta, podvrsta,
                                izmjena, donositelj, eli)
           VALUES (:serija, :godina, :broj, :clanak, :naslov, :vrsta, :podvrsta,
                   :izmjena, :donositelj, :eli)
           ON CONFLICT(serija, godina, broj, clanak) DO UPDATE SET
             naslov = COALESCE(excluded.naslov, katalog.naslov),
             vrsta = COALESCE(excluded.vrsta, katalog.vrsta),
             podvrsta = COALESCE(excluded.podvrsta, katalog.podvrsta),
             izmjena = COALESCE(excluded.izmjena, katalog.izmjena),
             donositelj = COALESCE(excluded.donositelj, katalog.donositelj),
             eli = COALESCE(excluded.eli, katalog.eli)""",
        red,
    )
