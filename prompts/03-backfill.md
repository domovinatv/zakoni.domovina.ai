# Prompt: Faza 2 — Backfill 2026 → 1990

Učitaj `prompts/00-kontekst.md`. Preduvjet: Faza 1 verificirana na 2026.

## Zadatak

### `scripts/10_backfill.py --od 2026 --do 1990 [--samo-godina G]`
Orkestrator koji za svaku godinu (silazno) pokreće faze redom: enumerate → fetch_rdf →
fetch_html → parse → stats. Pravila:
- godina se smatra gotovom tek kad `06_stats.py --godina G` prođe (exit 0)
- ako stats padne → ispiši dijagnostiku, **stani** (ne prelazi na stariju godinu dok se ne riješi)
- sve je idempotentno: ponovno pokretanje preskače preuzeto (raw cache) i obrađeno (anti-join)
- na kraju svake godine ispiši sažetak: N izdanja, N akata, N grešaka, trajanje

### Očekivani problemi kod starijih godina (dokumentiraj rješenja u docs/01!)

1. **Stariji HTML drugačije strukturiran** (posebno ~1990–2005): parser u `04_parse.py` drži
   fallback lance (probaj selektor A, pa B…). Kad dodaš fallback, zabilježi za koje godine vrijedi.
2. **RDF možda ne postoji za najstarije akte** — tada je HTML jedini izvor; naslov uzmi iz
   `<title>`, tip akta heuristički iz prve linije teksta ("ZAKON", "UREDBU", "PRAVILNIK"…),
   status neka ostane `parsiran` uz `oznake(vrsta='bez_rdf')` marker.
3. **Enumeracija**: stariji brojevi izdanja mogu imati drukčiji `MM` u URL-u — regex već hvata
   sve; ne pretpostavljaj ništa o mjesecima.
4. **Prekidi**: proces smije trajati danima; pokretanje u komadima po godinu
   (`--samo-godina 2019`) je normalan način rada.

## Procjena opsega

~3.000–4.000 akata godišnje × 2 zahtjeva (rdf+html) uz ~1.5 req/s ≈ **1.5–2 h po godini**.
Cijeli backfill do 1990.: red veličine tjedan dana kalendarski, uz pokretanje po godinama.

## Verifikacija ("Gotovo kad")

- `uv run python scripts/06_stats.py` (bez `--godina`) ispisuje čistu tablicu svih obrađenih
  godina bez rupa; udio `status='greska'` < 0.5 % po godini (svaku grešku pogledaj i klasificiraj)
- nasumične ručne provjere: po 2 akta iz 3 različita desetljeća usporedi s live sajtom
- nakon svake dovršene godine: `uv run python scripts/05_build_fts.py` (refresh indeksa)
