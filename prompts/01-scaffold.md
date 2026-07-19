# Prompt: Faza 0 — Scaffold projekta

Učitaj `prompts/00-kontekst.md` i dokumente koje navodi. Zatim napravi kostur projekta.

## Zadatak

1. **`pyproject.toml`** — Python >= 3.13, ovisnosti: `httpx`, `lxml`, `beautifulsoup4`,
   `python-dotenv`. Dev: `pytest`. Inicijaliziraj `uv sync`.
2. **Struktura direktorija** iz docs/02 §2 (`src/`, `scripts/`, `data/raw/nn/`, `docs/`, `prompts/`
   već postoje). Dodaj `src/__init__.py`.
3. **`src/db.py`** — preuzmi obrazac iz `/Users/ms/git/domovinatv/stranke.domovina.ai/src/db.py`
   (SCHEMA string, `connect()`, upsert helperi) i prilagodi shemi iz docs/02 §4 doslovno.
   Dodaj: `upsert_akt(conn, akt: dict) -> int` (po `eli`), `insert_veza`, `insert_oznaka`,
   `upsert_institucija`, `start_run`/`finish_run` za `ingest_runs`.
4. **`src/nn_client.py`** — httpx klijent:
   - `get(url) -> bytes` s rate limitom (min. 0.6 s između zahtjeva), retry 3× s backoffom,
     User-Agent iz 00-kontekst.md
   - `fetch_cached(url, path) -> bytes` — ako `path` postoji, čitaj s diska; inače dohvati, spremi, vrati
   - helperi za URL-ove: `search_url(godina, broj)`, `rdf_url(godina, broj, clanak)`,
     `full_html_url(godina, mjesec, broj, clanak)` — formati iz docs/01
   - učitaj robots.txt Disallow listu jednom i izloži `is_disallowed(url)`
5. **`.env.example`** (za sada samo placeholder komentari — NN ne treba ključeve),
   **`.gitignore`** (`data/`, `.env`, `__pycache__`, `*.db`, `frontend/dist`, `node_modules`),
   **`LICENSE`** (MIT) i **`LICENSE-DATA`** (CC BY 4.0, po uzoru na stranke.domovina.ai).
6. **`README.md`** — kratki opis projekta, kako pokrenuti, linkovi na docs/ i prompts/.

## Verifikacija ("Gotovo kad")

```bash
uv run python -c "from src.db import connect; c=connect(); print([r[0] for r in c.execute(\"select name from sqlite_master where type='table'\")])"
# → mora ispisati: izdanja, akti, akt_tekst, akt_veze, institucije, oznake, ingest_runs, analize
uv run python -c "from src.nn_client import rdf_url; assert rdf_url(2024,1,1).endswith('/eli/sluzbeni/2024/1/1/rdf')"
```
