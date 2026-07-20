# zakoni.domovina.ai

Otvoreni katalog svih akata službenog dijela Narodnih novina (zakoni, uredbe, pravilnici…),
backfill 2026 → 1990, SQLite + FTS5, kasnije ClickHouse RAG i Magisterium AI analiza.

## Prvo pročitaj

- `prompts/00-kontekst.md` — konvencije i pravila (OBAVEZNO za svaki zadatak)
- `docs/01-izvor-podataka-nn.md` — verificirani nn.hr endpointi (ELI/RDF); ako se stvarnost
  razlikuje od ovog dokumenta, prvo ažuriraj dokument
- `docs/02-arhitektura.md` — stack, shema, pipeline
- `docs/03-plan-faza.md` — faze i "Gotovo kad" kriteriji; radi fazu po fazu, promptovi su u `prompts/`

## Bitno

- Python 3.13 + `uv`; pokretanje skripti: `uv run python scripts/NN_*.py`
- Podaci fizički žive na vanjskom disku `/Volumes/DOMOVINA2TB/zakoni_domovina_ai_podaci/`;
  `data/` i `frontend/public/data` u repou su symlinkovi na njega. Disk mora biti montiran
  (`src/__init__.py` to provjerava i digne jasnu grešku ako nije).
- Sve idempotentno; raw cache u `data/raw/nn/` se nikad ne briše i nikad ne commita
- Rate limit prema nn.hr: 1–2 req/s, UA s kontaktom
- Sestrinski repoi s obrascima za kopiranje: `../stranke.domovina.ai`, `../klubovi.domovina.ai`
