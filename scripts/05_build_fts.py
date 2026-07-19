"""FTS5 indeks (drop+recreate) nad naslovima i tekstovima akata.

Tokenizer unicode61 remove_diacritics 2 — pretraga radi i bez dijakritika.
Idempotentno: uvijek gradi ispocetka iz akti + akt_tekst.
"""

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from src import db


def main():
    conn = db.connect()
    conn.execute("DROP TABLE IF EXISTS akti_fts")
    conn.execute(
        """CREATE VIRTUAL TABLE akti_fts USING fts5(
             naslov, tekst, tip_akta UNINDEXED, eli UNINDEXED,
             tokenize = "unicode61 remove_diacritics 2")"""
    )
    n = conn.execute(
        """INSERT INTO akti_fts (naslov, tekst, tip_akta, eli)
           SELECT a.naslov, t.tekst, a.tip_akta, a.eli
           FROM akti a LEFT JOIN akt_tekst t ON t.akt_id = a.id
           WHERE a.status = 'parsiran'"""
    ).rowcount
    conn.commit()
    print(f"FTS izgradjen: {n} akata indeksirano.")


if __name__ == "__main__":
    main()
