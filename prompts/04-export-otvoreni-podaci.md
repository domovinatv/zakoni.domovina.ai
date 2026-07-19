# Prompt: Faza 3 — Otvoreni podaci + statički export

Učitaj `prompts/00-kontekst.md`. Preduvjet: bar nekoliko godina backfillano.

## Zadatak

### `scripts/07_export_static.py [--out DIR]`
Po uzoru na `stranke.domovina.ai/scripts/09_export_static.py`:

1. **JSON za budući frontend** (`frontend/public/data/`):
   - `akti_{godina}.json` — lista akata godine (eli, naslov, tip, datumi, donositelj, broj/clanak),
     bez punog teksta (tekst se lazy-loada po aktu)
   - `akt/{godina}/{broj}_{clanak}.json` — detalj s tekstom, vezama i oznakama
   - `sifrarnici.json` — institucije, tipovi akata s brojem akata
   - `stats.json` — ukupni brojevi po godini/tipu (za naslovnicu)
   - `manifest.json` — `generated_at`, `schema_version`, raspon godina
2. **Otvoreni podaci** (`data/export/`):
   - `akti.csv` + `akt_veze.csv` + `oznake.csv` + `institucije.csv` (bez punog teksta)
   - `akti.parquet` s punim tekstom (jedan file, pogodan za analize / HuggingFace)
   - `README-DATA.md` s opisom stupaca, licencom (CC BY 4.0, izvor: Narodne novine) i datumom
3. Null vrijednosti izbaci iz JSON-a, minificirani separatori (kao u stranke exportu).

## Verifikacija ("Gotovo kad")

- export prolazi iz čiste baze jednom naredbom, reproducibilno (isti input → isti output
  osim `generated_at`)
- `jq . frontend/public/data/manifest.json` validan; nasumični detalj-JSON sadrži tekst i veze
- CSV se otvara bez grešaka (`python -c "import csv; ..."` smoke test), Parquet čitljiv
  (`uv run python -c "import pyarrow.parquet as pq; print(pq.read_metadata('data/export/akti.parquet'))"`)
