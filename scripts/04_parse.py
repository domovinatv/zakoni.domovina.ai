"""Parsiranje raw RDF-a i HTML-a u normalizirane tablice (status=html_ok -> parsiran).

RDF: naslov, tip_akta, datumi, donositelj, ELI veze (akt_veze), klasifikacije (oznake).
HTML: plain tekst tijela (div.sl-content) -> akt_tekst; prvi red = naziv donositelja.
Idempotentno: upserti; ponovno pokretanje preskace vec parsirane (anti-join po statusu).
"""

import argparse
import re
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from bs4 import BeautifulSoup
from lxml import etree

from src import db, nn_client

ELI_NS = "http://data.europa.eu/eli/ontology#"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RESOURCE = f"{{{RDF_NS}}}resource"

OZNAKA_VRSTE = [
    ("eurovoc.europa.eu", "eurovoc"),
    ("nn-legal-area", "legal_area"),
    ("nn-index-terms", "index_term"),
    ("nn-content-type", "content_type"),
]


def parse_rdf(raw: bytes, own_eli: str) -> dict:
    """Vrati polja akta + liste veza i oznaka iz ELI RDF/XML-a."""
    root = etree.fromstring(raw)
    out = {"veze": [], "oznake": []}
    own_uri = f"https://narodne-novine.nn.hr/eli/{own_eli}"
    for desc in root.iter(f"{{{RDF_NS}}}Description"):
        if desc.get(f"{{{RDF_NS}}}about") != own_uri:
            continue
        for el in desc:
            tag = etree.QName(el).localname
            res = el.get(RESOURCE, "")
            if tag == "type_document" and res:
                out["tip_akta"] = res.rstrip("/").rsplit("/", 1)[-1]
            elif tag == "date_document":
                out["datum_akta"] = el.text
            elif tag == "date_publication":
                out["datum_objave"] = el.text
            elif tag == "passed_by" and res:
                nn_id = res.rstrip("/").rsplit("/", 1)[-1]
                if nn_id.isdigit():
                    out["donositelj_nn_id"] = int(nn_id)
            elif tag == "is_about" and res:
                for needle, vrsta in OZNAKA_VRSTE:
                    if needle in res:
                        out["oznake"].append((vrsta, res))
                        break
                else:
                    out["oznake"].append(("ostalo", res))
            elif "/eli/sluzbeni/" in res and tag != "is_realized_by":
                to_eli = res.split("/eli/", 1)[1].rstrip("/")
                if to_eli != own_eli:
                    out["veze"].append((tag, to_eli))
    # naslov je na LegalExpression elementu
    for expr in root.iter(f"{{{ELI_NS}}}LegalExpression"):
        t = expr.find(f"{{{ELI_NS}}}title")
        if t is not None and t.text:
            out["naslov"] = t.text.strip()
            break
    return out


def parse_html(raw: bytes) -> tuple[str, str | None]:
    """Vrati (plain tekst, naziv donositelja iz prvog retka)."""
    soup = BeautifulSoup(raw, "lxml")
    node = soup.select_one("div.sl-content") or soup.body
    for junk in node.select("script, style"):
        junk.decompose()
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in node.get_text("\n").splitlines()]
    lines = [ln for ln in lines if ln]
    tekst = "\n".join(lines)
    donositelj = lines[0] if lines and not lines[0].isdigit() else None
    return tekst, donositelj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--godina", type=int, required=True)
    args = ap.parse_args()
    g = args.godina

    conn = db.connect()
    akti = conn.execute(
        "SELECT id, eli, broj, clanak FROM akti WHERE godina=? AND status='html_ok' ORDER BY clanak",
        (g,),
    ).fetchall()
    run_id = db.start_run(conn, g, "parse")
    ok = err = 0
    for i, a in enumerate(akti, 1):
        try:
            rdf_path = nn_client.RAW_DIR / str(g) / "rdf" / f"{a['broj']}_{a['clanak']}.rdf"
            html_path = nn_client.RAW_DIR / str(g) / "html" / f"{a['broj']}_{a['clanak']}.html"
            meta = parse_rdf(rdf_path.read_bytes(), a["eli"]) if rdf_path.exists() else {"veze": [], "oznake": []}
            tekst, donositelj = parse_html(html_path.read_bytes())

            db.upsert_akt(conn, {
                "eli": a["eli"], "godina": g, "broj": a["broj"], "clanak": a["clanak"],
                "mjesec": None,
                "naslov": meta.get("naslov"), "tip_akta": meta.get("tip_akta"),
                "donositelj_nn_id": meta.get("donositelj_nn_id"),
                "datum_akta": meta.get("datum_akta"), "datum_objave": meta.get("datum_objave"),
            })
            db.set_tekst(conn, a["id"], tekst)
            for predikat, to_eli in meta["veze"]:
                db.insert_veza(conn, a["eli"], predikat, to_eli)
            for vrsta, uri in meta["oznake"]:
                db.insert_oznaka(conn, a["eli"], vrsta, uri)
            if meta.get("donositelj_nn_id"):
                db.upsert_institucija(conn, meta["donositelj_nn_id"], donositelj)
            db.set_status(conn, a["eli"], "parsiran")
            ok += 1
        except Exception as exc:
            print(f"GRESKA {a['eli']}: {exc}", file=sys.stderr)
            db.set_status(conn, a["eli"], "greska")
            err += 1
        if i % 100 == 0:
            conn.commit()
            print(f"  {i}/{len(akti)}")
    conn.commit()
    db.finish_run(conn, run_id, ok, err)
    print(f"Parse gotovo: {ok} ok, {err} gresaka od {len(akti)}.")


if __name__ == "__main__":
    main()
