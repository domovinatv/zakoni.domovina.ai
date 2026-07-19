# Plan implementacije po fazama

Svaka faza ima svoj izvršni prompt u `prompts/` — dizajnirano tako da svaku fazu može odraditi
agent (npr. Opus 4.8) uz minimalno dodatnog konteksta: prompt kaže što čitati, što napraviti i
kako verificirati. Faze se rade redom; svaka završava provjerljivim stanjem.

## Faza 0 — Scaffold (prompts/01-scaffold.md)
`pyproject.toml` (uv, Python 3.13), struktura direktorija, `src/db.py` sa shemom iz
docs/02-arhitektura.md §4, `src/nn_client.py` (httpx + rate limit + raw cache), `.env.example`,
`.gitignore`, licence.
**Gotovo kad:** `uv run python -c "import src.db; src.db.connect()"` kreira praznu bazu sa svim tablicama.

## Faza 1 — Ingest pipeline (prompts/02-ingest-pipeline.md)
Skripte `01_enumerate` … `06_stats` iz docs/02 §5, testirano na **jednoj godini (2026)**.
**Gotovo kad:** za 2026. svi akti imaju `status=parsiran`, naslovi i tipovi popunjeni,
`06_stats.py` ne prijavljuje rupe u sekvenci `clanak`, FTS pretraga vraća rezultate.

## Faza 2 — Backfill 2026 → 1990 (prompts/03-backfill.md)
`10_backfill.py` orkestrator, godina po godinu unatrag, uz QA nakon svake godine.
Stariji HTML (posebno < 2000.) može tražiti parser fallback — prilagođavati postupno.
**Gotovo kad:** sve godine do cilja imaju parsirane akte; `06_stats.py` izvještaj po godinama čist.

## Faza 3 — Otvoreni podaci + statički export (prompts/04-export-otvoreni-podaci.md)
`07_export_static.py`: JSON za budući frontend + CSV/Parquet dump cijele baze, `manifest.json`
(generated_at, schema_version), `LICENSE-DATA`.
**Gotovo kad:** exporti se generiraju reproducibilno iz SQLite-a jednom naredbom.

## Faza 4 — ClickHouse RAG (prompts/05-clickhouse-rag.md)
Docker ClickHouse, chunking po člancima zakona ("Članak 1.", "Članak 2." …), embeddinzi
(multijezični model — vidi prompt), hibridna pretraga (FTS5 + kosinusna udaljenost).
**Gotovo kad:** semantički upit na hrvatskom ("naknada za nezaposlene") vraća relevantne članke zakona.

## Faza 5 — Magisterium AI teološka analiza (prompts/06-magisterium-analiza.md)
Smoke test na malom uzorku akata (etički osjetljiva područja: obitelj, život, brak, bioetika),
preko Magisterium AI MCP-a; rezultat u tablicu `analize` + markdown izvještaji.
**Gotovo kad:** ≥ 5 akata ima kompletnu analizu s citatima crkvenih izvora i ocjenom usklađenosti.

## Faza 6 — Frontend (kasnije, zaseban plan)
React PWA po uzoru na stranke/klubovi, Cloudflare Pages. Nije dio prvog prolaza.

## Redoslijed i ovisnosti

```
0 → 1 → 2 → 3
        2 → 4 → 5      (RAG i analiza mogu krenuti čim postoji nekoliko godina podataka)
```

## Načela (vrijede za sve faze)

1. **Raw prvo** — ništa se ne parsira što nije prvo spremljeno na disk.
2. **Idempotentno** — svaka skripta se smije ponovno pokrenuti; anti-join bira samo neobrađeno.
3. **Pristojno** — rate limit, UA s kontaktom, robots.txt se poštuje.
4. **Verificirano** — faza nije gotova dok njen "Gotovo kad" kriterij ne prođe.
5. **Sve odluke u docs/** — agent koji nešto promijeni (npr. parser fallback za stare godine)
   dužan je ažurirati dokumentaciju.
