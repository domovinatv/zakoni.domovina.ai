# Arhitektura — zakoni.domovina.ai

Katalog svih akata službenog dijela Narodnih novina (zakoni, uredbe, pravilnici, odluke…),
kronološki od 2026. prema starijim godinama, kao **otvorena baza podataka** + FTS pretraga +
ClickHouse RAG za semantičko pretraživanje + AI teološka analiza (Magisterium AI).

Arhitektura namjerno klonira provjereni "katalog engine" iz `stranke.domovina.ai` i
`klubovi.domovina.ai` (isti stack, iste konvencije) — vidi §7.

## 1. Stack

- **Python 3.13 + `uv`** (`pyproject.toml` + `uv.lock`), bez ORM-a
- `httpx` (HTTP), `lxml` + `beautifulsoup4` (HTML/RDF parsing), `python-dotenv`
- **SQLite** (stdlib `sqlite3`) — normalizirana baza, `data/zakoni.db` (gitignored)
- **FTS5** virtualna tablica, tokenizer `unicode61 remove_diacritics 2` (hrvatski dijakritici)
- **ClickHouse** (lokalni Docker) — RAG sloj: chunkovi + embeddinzi (kasnija faza)
- Frontend (kasnija faza): Vite + React PWA, statički JSON export, Cloudflare Pages

## 2. Struktura direktorija

```
zakoni.domovina.ai/
├── docs/                  # trajna dokumentacija (ovaj dokument, izvor podataka, plan)
├── prompts/               # izvršni promptovi za AI agente (Opus 4.8) — po fazama
├── src/                   # biblioteka: db.py, nn_client.py, parse_rdf.py, parse_html.py, normalize.py
├── scripts/               # numerirane pipeline skripte, ručno pokretanje: uv run python scripts/NN_*.py
├── data/
│   ├── raw/nn/{godina}/   # raw cache — SVE preuzeto s nn.hr, nikad se ne briše
│   │   ├── search/{broj}.html          # stranice pretrage (enumeracija)
│   │   ├── rdf/{broj}_{clanak}.rdf     # ELI RDF metapodaci po aktu
│   │   └── html/{broj}_{clanak}.html   # "full" HTML po aktu
│   └── zakoni.db          # SQLite (gitignored)
├── web/                   # (opcionalno) FastAPI+HTMX lokalni preview
├── frontend/              # (kasnija faza) React PWA
├── docker/clickhouse/     # docker-compose za ClickHouse (RAG faza)
├── .env.example
├── LICENSE                # kod
└── LICENSE-DATA           # otvoreni podaci
```

## 3. Slojevi podataka

1. **Raw sloj (filesystem)** — svaki HTTP odgovor sprema se na disk prije ikakve obrade.
   Ako datoteka postoji → ne preuzima se ponovno. Reprocesiranje je uvijek moguće offline.
2. **Normalizirani sloj (SQLite)** — parsirano iz raw sloja, idempotentni upserti po ELI ključu.
3. **Izvedeni slojevi** — FTS5 indeks, statički JSON export, ClickHouse chunkovi+embeddinzi,
   AI analize. Svi se mogu u cijelosti regenerirati iz slojeva 1+2.

## 4. SQLite shema (src/db.py — `SCHEMA` string, kao u stranke/klubovi)

```sql
-- izdanje Narodnih novina (jedan "broj")
CREATE TABLE IF NOT EXISTS izdanja (
  godina        INTEGER NOT NULL,
  broj          INTEGER NOT NULL,
  mjesec        INTEGER,                -- iz URL-a clanaka (YYYY_MM_BROJ_CLANAK)
  broj_akata    INTEGER,
  created_at    TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (godina, broj)
);

-- jedan akt (zakon/uredba/pravilnik/odluka/...)
CREATE TABLE IF NOT EXISTS akti (
  id            INTEGER PRIMARY KEY,
  eli           TEXT UNIQUE NOT NULL,   -- "sluzbeni/2024/1/1" (kanonski ključ)
  godina        INTEGER NOT NULL,
  broj          INTEGER NOT NULL,       -- broj izdanja
  clanak        INTEGER NOT NULL,       -- redni broj akta (sekvencijalan unutar godine)
  mjesec        INTEGER,
  naslov        TEXT,
  tip_akta      TEXT,                   -- "UREDBA","ZAKON",... (slug iz type_document URI-ja)
  donositelj_nn_id INTEGER,             -- numerički ID iz nn-institutions URI-ja
  datum_akta    TEXT,                   -- eli:date_document (ISO)
  datum_objave  TEXT,                   -- eli:date_publication (ISO)
  status        TEXT NOT NULL DEFAULT 'enumeriran',
                -- enumeriran | rdf_ok | html_ok | parsiran | skipped_robots | greska
  created_at    TEXT DEFAULT (datetime('now')),
  updated_at    TEXT DEFAULT (datetime('now')),
  UNIQUE (godina, clanak)
);

-- puni tekst odvojeno (akti ostaju lagani za listanje)
CREATE TABLE IF NOT EXISTS akt_tekst (
  akt_id        INTEGER PRIMARY KEY REFERENCES akti(id),
  tekst         TEXT NOT NULL           -- ekstrahirani plain text iz full HTML-a
);

-- veze među propisima iz ELI RDF-a → graf
CREATE TABLE IF NOT EXISTS akt_veze (
  from_eli      TEXT NOT NULL,
  predikat      TEXT NOT NULL,          -- repealed_by, based_on, changed_by, changes, ...
  to_eli        TEXT NOT NULL,          -- može referencirati akt koji još nije u bazi!
  UNIQUE (from_eli, predikat, to_eli)
);

-- šifrarnik institucija (labele se pune postupno iz HTML-a članaka)
CREATE TABLE IF NOT EXISTS institucije (
  nn_id         INTEGER PRIMARY KEY,    -- iz nn-institutions/{id}
  naziv         TEXT
);

-- klasifikacije: EuroVoc, nn-legal-area, nn-index-terms, nn-content-type
CREATE TABLE IF NOT EXISTS oznake (
  akt_eli       TEXT NOT NULL,
  vrsta         TEXT NOT NULL,          -- eurovoc | legal_area | index_term | content_type
  uri           TEXT NOT NULL,
  label         TEXT,
  UNIQUE (akt_eli, vrsta, uri)
);

-- audit trag (kao backfill_runs u stranke/klubovi)
CREATE TABLE IF NOT EXISTS ingest_runs (
  id            INTEGER PRIMARY KEY,
  godina        INTEGER,
  faza          TEXT,                   -- enumeracija | rdf | html | parse
  started_at    TEXT, finished_at TEXT,
  ok_count      INTEGER, err_count INTEGER,
  napomena      TEXT
);

-- AI teološka analiza (Magisterium) — kasnija faza
CREATE TABLE IF NOT EXISTS analize (
  id            INTEGER PRIMARY KEY,
  akt_eli       TEXT NOT NULL,
  vrsta         TEXT NOT NULL DEFAULT 'magisterium',
  model         TEXT,                   -- npr. "claude-opus-4-8 + magisterium-mcp"
  ocjena        TEXT,                   -- uskladjen | napetost | sukob | nije_primjenjivo
  sazetak       TEXT,
  analiza_md    TEXT,                   -- puni markdown s citatima
  created_at    TEXT DEFAULT (datetime('now')),
  UNIQUE (akt_eli, vrsta)
);
```

FTS (gradi se zasebnom skriptom, drop+recreate):

```sql
CREATE VIRTUAL TABLE akti_fts USING fts5(
  naslov, tekst, tip_akta UNINDEXED, eli UNINDEXED,
  tokenize = "unicode61 remove_diacritics 2"
);
```

**Idempotencija:** upsert po `eli` (`ON CONFLICT(eli) DO UPDATE`), veze/oznake `INSERT OR IGNORE`.
Sve skripte smiju se pokrenuti više puta bez štete.

## 5. Pipeline (numerirane skripte)

| Skripta | Ulaz → Izlaz |
|---|---|
| `scripts/01_enumerate.py --godina G` | search.aspx po broju → `izdanja` + `akti(status=enumeriran)` + raw search HTML |
| `scripts/02_fetch_rdf.py --godina G` | akti bez RDF-a (anti-join) → raw `.rdf` + `status=rdf_ok` |
| `scripts/03_fetch_html.py --godina G` | akti bez HTML-a → raw full `.html` + `status=html_ok` |
| `scripts/04_parse.py --godina G` | raw RDF+HTML → `akti` (naslov, datumi, tip…), `akt_tekst`, `akt_veze`, `oznake`, `institucije`; `status=parsiran` |
| `scripts/05_build_fts.py` | SQLite → FTS5 indeks (drop+recreate) |
| `scripts/06_stats.py` | kontrolni ispis: broj akata po godini/tipu, rupe u sekvenci `clanak` |
| `scripts/07_export_static.py` | SQLite → JSON za frontend + CSV/Parquet export otvorenih podataka |
| `scripts/10_backfill.py --od 2026 --do 1990` | orkestrator: vrti 01–04 godinu po godinu unatrag |
| `scripts/20_rag_chunks.py` | tekst → chunkovi po članцima zakona (vidi docs/04) |
| `scripts/21_rag_embed.py` | chunkovi → embeddinzi → ClickHouse |
| `scripts/30_analiza_magisterium.py` | odabrani akti → Magisterium analiza → `analize` |

Svaka skripta ima docstring: izvor, cache lokacija, garancija idempotentnosti (konvencija iz klubovi).

## 6. Pravila preuzimanja

- 1–2 req/s, serijski unutar godine; `User-Agent: zakoni.domovina.ai (stepanic.matija@gmail.com)`
- retry s eksponencijalnim backoffom (3×), na trajnu grešku → `status=greska` + nastavi
- URL-ovi s robots.txt Disallow liste → `status=skipped_robots`
- **backfill redoslijed: 2026 → 2025 → … → 1990** (novije prvo; stariji HTML može tražiti prilagodbu parsera — parser drži per-era fallback)

## 7. Što kopiramo iz sestrinskih repoa (konkretni fajlovi)

- `stranke.domovina.ai/src/db.py` — obrazac SCHEMA string + upsert + FTS build
- `stranke.domovina.ai/src/normalize.py` — `slugify`, `strip_diacritics`
- `stranke.domovina.ai/scripts/06_backfill.py` + `src/backfill.py` — anti-join "samo neobrađeni" obrazac
- `stranke.domovina.ai/scripts/09_export_static.py` — statički JSON export s `manifest.json`
- `klubovi.domovina.ai/src/sofascore.py` i sl. — obrazac source-client modula → naš `src/nn_client.py`
- `frontend/scripts/deploy.sh` — export → sitemap → build → `wrangler pages deploy`
- dual licenca: `LICENSE` + `LICENSE-DATA`

Firecrawl **nije potreban** — nn.hr se dohvaća izravno httpx-om (nema bot-zaštite, sadržaj je statičan).
