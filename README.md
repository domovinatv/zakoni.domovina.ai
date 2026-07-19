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
- [x] Faza 0: Scaffold (`prompts/01-scaffold.md`)
- [x] Faza 1: Ingest pipeline na 2026 (`prompts/02-ingest-pipeline.md`) — 78 izdanja, 937 akata, sve parsirano
- [x] **Katalog cijelog arhiva** (`scripts/00_katalog.py`) — 97.561 propis, 5.077 izdanja,
      1990–2026, iz službenog Kazala u 37 zahtjeva. Služi i kao neovisna kontrola ingesta.
- [~] Faza 2: Backfill 2025 → 1990 — **pauziran nakon 2024.**
      Plan s izmjerenim brojkama: `docs/05-plan-punog-backfilla.md` (~24 h, ~6,9 GB)
  - [x] **2025** — 158 izdanja, 2.404 akta, 0 grešaka (54 min); QA prošao
  - [x] **2024** — 155 izdanja, 2.576 akata, 0 grešaka; QA prošao
  - [ ] 2023 → 1990 — ⚠️ **RDF postoji tek od 2015.**; za 1990–2014 katalog je jedini
        izvor tipa akta i donositelja (`docs/01` §0)
  - [ ] **Poznata rupa:** serija *Međunarodni ugovori* nije u bazi (`docs/01` §7)
  - [ ] **Poznata rupa:** ~5 % akata nema tekst jer NN objavi samo PDF; PDF import
        moguć tek za 2023+ (`docs/05` §6)
- [~] Faza 3: Otvoreni podaci export (`prompts/04-export-otvoreni-podaci.md`) — JSON+CSV rade (`07_export_static.py`), Parquet TODO
- [x] Deploy: https://zakoni.domovina.ai (Cloudflare Pages, `frontend/scripts/deploy.sh`)
- [ ] Faza 4: ClickHouse RAG (`prompts/05-clickhouse-rag.md`) — prije toga izmjeriti
      gubi li se struktura tablica u HTML tekstu (`docs/06` §5.1)
- [ ] Faza 5: Magisterium AI analiza (`prompts/06-magisterium-analiza.md`)

## Pokretanje (od Faze 0 nadalje)

```bash
uv sync

# 1) katalog cijelog arhiva iz sluzbenog Kazala (37 zahtjeva, ~1 min)
uv run python scripts/00_katalog.py
uv run python scripts/00_katalog.py --procjena   # opseg + procjena vremena/diska

# 2) backfill jedne godine (dohvat + parse + kontrola)
uv run python scripts/10_backfill.py --samo-godina 2024

# 3) indeks, export i objava
uv run python scripts/05_build_fts.py
./frontend/scripts/deploy.sh
```

Srodni projekti istog enginea: [stranke.domovina.ai](../stranke.domovina.ai),
[klubovi.domovina.ai](../klubovi.domovina.ai).
