# zakoni.domovina.ai

Otvoreni katalog svih akata službenog dijela **Narodnih novina** — zakoni, uredbe, pravilnici,
odluke — kronološki, s backfillom od 2026. prema starijim godinama. Cilj: otvorena baza podataka
(SQLite + CSV/Parquet export), brza FTS pretraga, ClickHouse RAG za semantičko pretraživanje i
AI analiza usklađenosti civilnih zakona s naukom Katoličke Crkve (Magisterium AI).

## Kako je projekt organiziran

| Gdje | Što |
|---|---|
| `docs/01-izvor-podataka-nn.md` | Verificirani nn.hr endpointi (ELI, RDF, enumeracija) |
| `docs/02-arhitektura.md` | Stack, struktura, SQLite shema, pipeline |
| `docs/03-plan-faza.md` | Faze implementacije s kriterijima završetka |
| `prompts/` | Izvršni promptovi po fazama — svaku fazu može odraditi AI agent |
| `src/`, `scripts/` | Kod (nastaje kroz faze 0–5) |

## Status

- [x] Istraživanje izvora podataka (ELI/RDF verificiran uživo)
- [x] Arhitektura + plan + promptovi
- [ ] Faza 0: Scaffold (`prompts/01-scaffold.md`)
- [ ] Faza 1: Ingest pipeline na 2026 (`prompts/02-ingest-pipeline.md`)
- [ ] Faza 2: Backfill 2026 → 1990 (`prompts/03-backfill.md`)
- [ ] Faza 3: Otvoreni podaci export (`prompts/04-export-otvoreni-podaci.md`)
- [ ] Faza 4: ClickHouse RAG (`prompts/05-clickhouse-rag.md`)
- [ ] Faza 5: Magisterium AI analiza (`prompts/06-magisterium-analiza.md`)

## Pokretanje (od Faze 0 nadalje)

```bash
uv sync
uv run python scripts/01_enumerate.py --godina 2026
```

Srodni projekti istog enginea: [stranke.domovina.ai](../stranke.domovina.ai),
[klubovi.domovina.ai](../klubovi.domovina.ai).
