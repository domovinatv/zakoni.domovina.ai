# Zajednički kontekst za sve promptove (učitaj UVIJEK prvi)

Ti si inženjer na projektu **zakoni.domovina.ai** — otvoreni katalog svih akata službenog dijela
Narodnih novina (NN), s backfillom od 2026. unatrag.

## Obavezno pročitaj prije rada

1. `docs/01-izvor-podataka-nn.md` — verificirani endpointi nn.hr (ELI, RDF, enumeracija, stop-uvjeti)
2. `docs/02-arhitektura.md` — stack, struktura direktorija, SQLite shema, pipeline
3. `docs/03-plan-faza.md` — u kojoj smo fazi i što znači "gotovo"

## Konvencije (iste kao stranke.domovina.ai i klubovi.domovina.ai)

- Python 3.13, `uv` — pokretanje: `uv run python scripts/NN_naziv.py [--flags]`
- SQLite bez ORM-a; sav SQL u `src/db.py`; upsert po `eli`, `INSERT OR IGNORE` za veze/oznake
- Svaki HTTP odgovor prvo na disk u `data/raw/nn/{godina}/…`; ako datoteka postoji → ne dohvaćaj
- Svaka skripta ima docstring: izvor, cache lokacija, garancija idempotentnosti
- Rate limit 1–2 req/s; `User-Agent: zakoni.domovina.ai (stepanic.matija@gmail.com)`
- Komentari i identifikatori: hrvatski za domenu (akt, izdanje, donositelj), engleski za tehniku
- Ne commitaj `data/` (osim eventualnih malih šifrarnika); `.gitignore` to već pokriva

## Pravila ponašanja

- Ako nešto na nn.hr ne odgovara opisu u docs/01 (promijenjen HTML, novi format) — **prvo
  ažuriraj docs/01**, pa onda kod.
- Nikad ne "izmišljaj" podatke koji nedostaju; zapiši `status=greska` i nastavi.
- Nakon svake faze pokreni verifikaciju iz "Gotovo kad" kriterija i ispiši rezultat.
- Radiš li backfill: godinu po godinu, **od novijih prema starijima**, i nakon svake godine
  pokreni `scripts/06_stats.py` prije prelaska na sljedeću.
