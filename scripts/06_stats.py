"""Kontrolni izvjestaj: statusi, tipovi, nedostajuci akti, veze/oznake.

Nedostajuci akti se usporedjuju s tablicom `katalog` (sluzbeno Kazalo NN) — ne s
pretpostavkom da su brojevi akata neprekinuti, jer NN brojeve preskace.
Ako katalog za godinu nije ucitan, pada natrag na staru provjeru uz upozorenje.

Exit code 1 ako nedostaju akti ili postoje akti sa status=greska (za orkestrator).
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
        # Nedostajuci akti se mjere prema KATALOGU (sluzbeno Kazalo), ne prema
        # pretpostavci da su brojevi neprekinuti. NN preskace brojeve: 2024. nema
        # clanak 1786 (izd. 102 zavrsava na 1785, izd. 103 pocinje na 1787; oba
        # URL-a vracaju 404). Provjera neprekinutosti je davala lazne uzbune i
        # zaustavljala orkestrator. Vidi docs/06 §5.
        nasi = {r[0] for r in conn.execute(
            "SELECT clanak FROM akti WHERE godina=?", (g,))}
        u_katalogu = {r[0] for r in conn.execute(
            "SELECT clanak FROM katalog WHERE godina=? AND serija='sluzbeni'", (g,))}
        if u_katalogu:
            rupe = sorted(u_katalogu - nasi, key=lambda x: (len(x), x))
            izvor_rupa = "prema katalogu"
        else:
            # katalog za tu godinu jos nije ucitan -> stara provjera, uz napomenu
            brojevi = sorted(int(c) for c in nasi if str(c).isdigit())
            rupe = [str(x) for x in
                    sorted(set(range(1, max(brojevi) + 1)) - set(brojevi))] if brojevi else []
            izvor_rupa = "neprekinutost niza (katalog nije ucitan — moguce lazne uzbune)"
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
            print(f"  !! NEDOSTAJE {len(rupe)} akata ({izvor_rupa}): "
                  f"{rupe[:20]}{'...' if len(rupe) > 20 else ''}")
            problem = True
        if statusi.get("greska"):
            print(f"  !! {statusi['greska']} akata sa statusom greska")
            problem = True

    sys.exit(1 if problem else 0)


if __name__ == "__main__":
    main()
