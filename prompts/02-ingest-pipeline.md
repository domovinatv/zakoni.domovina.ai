# Prompt: Faza 1 — Ingest pipeline (testiran na 2026.)

Učitaj `prompts/00-kontekst.md`. Preduvjet: Faza 0 gotova. Napravi skripte 01–06 i dokaži ih na
godini 2026 (mala, ~20-ak izdanja do srpnja — brz feedback loop).

## Skripte

### `scripts/01_enumerate.py --godina G`
Za `broj = 1, 2, 3, …`: dohvati (kroz `fetch_cached`) stranicu pretrage
(`search_url`, cache: `data/raw/nn/{G}/search/{broj}.html`), izvuci linkove regexom
`clanci/sluzbeni/(\d{4})_(\d{2})_(\d+)_(\d+)\.html` → `(godina, mjesec, broj, clanak)`.
- upsert u `izdanja` i `akti` (`status='enumeriran'`, `eli = f"sluzbeni/{G}/{broj}/{clanak}"`)
- ⚠️ ako stranica ima točno `rpp` (200) linkova, dohvati i 2. stranicu (paginacija) — provjeri
  parametar za stranicu u HTML-u i dokumentiraj ga u docs/01
- stop: 3 uzastopna prazna broja
- zapiši `ingest_runs(faza='enumeracija')`

### `scripts/02_fetch_rdf.py --godina G [--limit N]`
Anti-join: akti godine G sa `status='enumeriran'`. Za svaki: `fetch_cached(rdf_url(...),
data/raw/nn/{G}/rdf/{broj}_{clanak}.rdf)` → `status='rdf_ok'`. Robots-disallowed → `skipped_robots`.

### `scripts/03_fetch_html.py --godina G [--limit N]`
Isto za full HTML: `data/raw/nn/{G}/html/{broj}_{clanak}.html`, `status='html_ok'`.
(PDF-ove NE preuzimamo u prvom prolazu — često su PDF cijelog izdanja, ~2 MB po aktu.)

### `scripts/04_parse.py --godina G`
Za akte sa `status='html_ok'` parsiraj raw datoteke:
- **RDF** (`lxml`, namespace `http://data.europa.eu/eli/ontology#`):
  `naslov` (eli:title), `tip_akta` (zadnji segment type_document URI-ja), `datum_akta`,
  `datum_objave`, `donositelj_nn_id` (zadnji segment passed_by URI-ja) → update `akti`
  - svi predikati koji pokazuju na drugi `…/eli/sluzbeni/...` (repealed_by, based_on, changed_by,
    changes, repeals, …) → `akt_veze`; NE filtriraj listu predikata unaprijed — spremi sve ELI veze
  - `is_about` → `oznake` (vrsta prema URI-ju: eurovoc / legal_area / index_term / content_type)
- **HTML**: ekstrahiraj plain text tijela akta (BeautifulSoup, ukloni skripte/stilove/navigaciju;
  u "full" varijanti tijelo je glavni sadržaj) → `akt_tekst`. Iz zaglavlja akta pokušaj pročitati
  naziv donositelja (npr. "VLADA REPUBLIKE HRVATSKE") → `upsert_institucija(nn_id, naziv)`.
- `status='parsiran'`; na iznimku → `status='greska'` + log, nastavi dalje.

### `scripts/05_build_fts.py`
Drop+recreate `akti_fts` (naslov, tekst) iz `akti` + `akt_tekst`, tokenizer
`unicode61 remove_diacritics 2`. Obrazac: `stranke.domovina.ai/scripts/05_build_fts.py`.

### `scripts/06_stats.py [--godina G]`
Ispis po godini: broj izdanja, broj akata po statusu, top tipovi akata, **rupe u sekvenci
`clanak`** (1..max mora biti kontinuirano — rupa znači propušten akt u enumeraciji),
broj veza i oznaka. Exit code 1 ako ima rupa ili grešaka (za CI/orkestrator).

## Verifikacija ("Gotovo kad")

```bash
uv run python scripts/01_enumerate.py --godina 2026
uv run python scripts/02_fetch_rdf.py --godina 2026
uv run python scripts/03_fetch_html.py --godina 2026
uv run python scripts/04_parse.py --godina 2026
uv run python scripts/05_build_fts.py
uv run python scripts/06_stats.py --godina 2026   # exit 0, bez rupa
# FTS smoke test:
uv run python -c "from src.db import connect; c=connect(); print(c.execute(\"select naslov from akti_fts where akti_fts match 'porez' limit 5\").fetchall())"
```

Ručna provjera: usporedi 3 nasumična akta s live stranicom na narodne-novine.nn.hr
(naslov, tip, datum, donositelj moraju odgovarati).
