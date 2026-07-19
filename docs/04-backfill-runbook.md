# Backfill runbook — 2025 → 1990

Operativni vodič za punjenje baze godinu po godinu. 2026. je već kompletna (937 akata,
verificirano). Svaki korak je idempotentan — prekid i ponovno pokretanje su normalni.

## TL;DR

```bash
# jedna godina (preporučeno — kontrola nakon svake):
uv run python scripts/10_backfill.py --samo-godina 2025

# ili raspon (staje na prvoj grešci):
uv run python scripts/10_backfill.py --od 2025 --do 2020

# nakon svake dovršene godine (ili serije godina):
uv run python scripts/05_build_fts.py
uv run python scripts/07_export_static.py
./frontend/scripts/deploy.sh          # objavi novo stanje na zakoni-domovina.pages.dev
```

## Očekivano trajanje i opseg

Brojke su **izmjerene** (tablica `ingest_runs`), ne procijenjene:

- ~150–160 izdanja i **~2.000–2.500 akata** po godini
  (2026. do srpnja: 78 izdanja / 937 akata; 2025.: 158 izdanja / 2.404 akta)
- ~2 HTTP zahtjeva po aktu (RDF + HTML) uz rate limit 0.6 s → **~1,33 s po aktu**:
  RDF 0,62 s + HTML 0,71 s. Za 2.404 akta ≈ **56 min po godini**, ne 1,5–2 h kako je
  ranije stajalo. Enumeracija ~1,5 min, parse ~25 s (zanemarivo).
- raw cache raste ~65 KB po aktu → **~150 MB po godini** (2025.: 156 MB)
- cijeli backfill 1990→2024: red veličine 18–26 h čistog dohvata (starije godine su manje)

## Redoslijed rada (preporuka)

1. **2025 → 2020** — moderna era, parser bi trebao raditi bez izmjena. Nakon svake godine
   pogledaj `06_stats.py` izlaz (orkestrator ga zove automatski).
2. **2019 → 2010** — isto, uz pozornost na eventualne `greska` statuse.
3. **2009 → 2000** — mogući prvi HTML fallbackovi.
4. **1999 → 1990** — najstariji sloj: RDF možda nepotpun/nepostojeći, HTML drugačiji.
   Očekuj rad na parseru (vidi prompts/03-backfill.md §"Očekivani problemi").

## Dijagnostika po tipu problema

| Simptom | Uzrok / lijek |
|---|---|
| `06_stats` prijavi rupe u sekvenci clanaka | enumeracija propustila izdanje → obriši `data/raw/nn/{G}/search/` za sporne brojeve i ponovi `01_enumerate --godina G` (prazne stranice se ionako ne cachiraju) |
| pojedinačni `status=greska` | pogledaj stderr log; mrežni timeout → resetiraj status i ponovi fazu: `UPDATE akti SET status='rdf_ok' WHERE eli='...'` pa `03_fetch_html --godina G` (vidi §Reset statusa) |
| RDF 404 za stare godine | očekivano za najstarije akte — parser mora podnijeti nepostojeći RDF (naslov iz `<title>`, tip heuristički; vidi prompts/03-backfill.md) |
| prazan/čudan tekst akta | provjeri `div.sl-content` selektor na tom aktu; dodaj fallback selektor u `04_parse.py::parse_html` i **dokumentiraj u docs/01** |
| >=200 akata u izdanju (upozorenje 01_enumerate) | implementiraj paginaciju search.aspx prije nastavka |

### Reset statusa (recepti)

```bash
# ponovi HTML dohvat za akte koji su pali:
uv run python -c "
from src.db import connect; c=connect()
c.execute(\"UPDATE akti SET status='rdf_ok' WHERE status='greska' AND godina=2025\"); c.commit()"
uv run python scripts/03_fetch_html.py --godina 2025

# ponovi parsiranje (npr. nakon izmjene parsera) — raw ostaje, samo se reparsira:
uv run python -c "
from src.db import connect; c=connect()
c.execute(\"UPDATE akti SET status='html_ok' WHERE status='parsiran' AND godina=1998\"); c.commit()"
uv run python scripts/04_parse.py --godina 1998
```

## Kontrola kvalitete nakon svake godine

1. `uv run python scripts/06_stats.py --godina G` — exit 0, bez rupa, bez `greska`
2. nasumično otvori 2 akta na `https://narodne-novine.nn.hr/eli/sluzbeni/{G}/{broj}/{clanak}`
   i usporedi naslov/tip/datum s bazom
3. udio akata bez naslova ili bez teksta < 1 % (`SELECT COUNT(*) FROM akti a LEFT JOIN akt_tekst t
   ON t.akt_id=a.id WHERE a.godina=G AND (a.naslov IS NULL OR t.tekst IS NULL)`)

## Deploy nakon backfilla

`./frontend/scripts/deploy.sh` radi sve (export → build → wrangler). Napomene za ovu mašinu:
- mreža nema IPv6 rutu → `NODE_OPTIONS=--dns-result-order=ipv4first` (već u deploy.sh)
- wrangler OAuth refresh ne prolazi kroz Claude Code sandbox → pokreni deploy iz običnog
  terminala, ili u Claude Codeu dopusti komandu izvan sandboxa
- Pages projekt `zakoni-domovina` postoji na D.O.M. accountu; custom domena se kači ručno

## Poznata ograničenja teksta

`akt_tekst` je plain text (bez tablica/strukture). Za RAG chunking po "Članak N." to je
dovoljno; ako zatreba struktura (tablice, stavci), reparsirati iz raw HTML-a — raw se čuva
upravo zato.
