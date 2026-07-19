# Prompt: Faza 4 — ClickHouse RAG (semantičko pretraživanje)

Učitaj `prompts/00-kontekst.md`. Preduvjet: bar nekoliko godina parsiranih akata u SQLite-u.

## Arhitektura RAG sloja

- **ClickHouse u Dockeru**: `docker/clickhouse/docker-compose.yml` (image `clickhouse/clickhouse-server`,
  volume za podatke, port 8123/9000, korisnik/lozinka iz `.env`)
- **Chunking po pravnim jedinicama**: hrvatski propisi imaju strukturu "Članak 1.", "Članak 2." …
  → chunk = jedan članak propisa (regex `^Članak \d+\.` na plain tekstu). Predugi članci (> ~1500
  tokena) dijele se na stavke; kratki susjedni članci se NE spajaju (granica članka je semantički
  bitna za citiranje). Preambula/potpis = zasebni chunkovi.
- **Embeddinzi**: multijezični model koji dobro pokriva hrvatski. Preferirano lokalno:
  `BAAI/bge-m3` (1024 dim, `sentence-transformers`); alternativa API: Voyage `voyage-3` ili
  OpenAI `text-embedding-3-large` — odluka kroz `.env` (`EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`).
  Isti model MORA embedati i upite (zapiši model u tablicu!).

### ClickHouse shema

```sql
CREATE TABLE zakoni.chunks (
  eli            String,                 -- "sluzbeni/2024/1/1"
  chunk_idx      UInt16,
  clanak_zakona  String,                 -- "Članak 5." ili "preambula"
  godina         UInt16,
  tip_akta       LowCardinality(String),
  naslov         String,
  tekst          String,
  embedding      Array(Float32),
  embedding_model LowCardinality(String),
  inserted_at    DateTime DEFAULT now()
) ENGINE = MergeTree ORDER BY (godina, eli, chunk_idx);
```

Za pretragu: `cosineDistance(embedding, [upit])` + filtri po godini/tipu. Na manjim volumenima
(< par milijuna chunkova) brute-force skeniranje je dovoljno; vektorski indeks
(`vector_similarity`) dodaj tek ako latencija postane problem.

## Skripte

### `scripts/20_rag_chunks.py [--godina G]`
SQLite → chunkovi (JSON Lines u `data/rag/chunks_{G}.jsonl`, idempotentno po eli+chunk_idx).
Uključi test: chunkanje poznatog zakona daje očekivani broj članaka.

### `scripts/21_rag_embed.py [--godina G] [--batch 64]`
JSONL → embeddinzi → insert u ClickHouse. Anti-join: preskoči (eli, chunk_idx, embedding_model)
koji već postoje. Batchevi, progres ispis, nastavljivo nakon prekida.

### `scripts/22_rag_search.py "upit" [--top 10] [--godina-od X] [--tip ZAKON]`
CLI za hibridnu pretragu: (1) vektorski top-50 iz ClickHousea, (2) FTS5 top-50 iz SQLite-a,
(3) Reciprocal Rank Fusion → top-N s ispisom eli, naslova, članka i isječka.

## Verifikacija ("Gotovo kad")

- `docker compose up -d` + `21_rag_embed --godina 2026` prolazi bez grešaka
- `22_rag_search "najviša cijena goriva"` vraća Uredbu o najvišim maloprodajnim cijenama
  naftnih derivata u top 3
- `22_rag_search "naknada za nezaposlene"` vraća relevantne akte (semantika, ne samo keyword)
