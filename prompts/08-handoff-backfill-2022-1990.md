Radiš na projektu zakoni.domovina.ai — katalog svih akata Narodnih novina.
Zadatak: sustavni backfill 2022 → 1990, uz MINIMALNU potrošnju tokena.

PROČITAJ PRVO (i ništa više dok ne zatreba):
1. docs/05-plan-punog-backfilla.md — plan, izmjerene brojke, redoslijed
2. docs/06-nalazi-i-otvorena-pitanja.md — zamke i otvorena pitanja
3. docs/04-backfill-runbook.md — dijagnostika i reset recepti

STANJE: 2026, 2025, 2024 gotove i verificirane. 2023 je enumerirana
(2.531 akt, ima naslov+tip, status='enumeriran') ali NIJE dohvaćena.
Katalog cijelog arhiva (97.561 propis, 1990–2026) već je u bazi.

PIPELINE (katalog-first, ne diraj ga bez razloga):
  00_katalog  -> već napunjen za sve godine, ne treba ponavljati
  01_sitemap  -> izdanja+akti iz sitemapova, naslov/tip iz kataloga
  02_fetch_rdf-> SAMO 2015+ (orkestrator to sam preskače)
  03_fetch_html -> 04_parse -> 06_stats

KAKO RADITI — pokreni u petlji i NE prati ispis akt po akt:

  # 2023 je već enumerirana, samo je dovrši:
  uv run python scripts/10_backfill.py --samo-godina 2023

  # zatim petlja unatrag, svaka godina staje na grešci:
  for g in $(seq 2022 -1 1990); do
    uv run python scripts/10_backfill.py --samo-godina $g || break
  done

Pokreni to u pozadini s preusmjerenim logom i provjeravaj SAMO sažetke:
  uv run python scripts/10_backfill.py --samo-godina $g > /tmp/bf_$g.log 2>&1

Za status koristi bazu, ne log:
  uv run python scripts/06_stats.py --godina G     # exit 0 = godina je gotova

OČEKIVANO: ~35–60 min po godini, ~3,3 GB diska ukupno, ~23 h za sve.
Godine < 2015 nemaju RDF — nema EuroVoca, veza ni datuma; naslov i tip
dolaze iz kataloga i to je ispravno, nije greška.

NAKON SVAKE 2–3 GODINE (ne češće, štedi tokene):
  uv run python scripts/05_build_fts.py
  uv run python scripts/07_export_static.py
  ./frontend/scripts/deploy.sh      # traži sandbox isključen (wrangler OAuth)
  git add -A && git commit && git push

KONTROLA KVALITETE (katalog je neovisan izvor — koristi ga):
  SELECT COUNT(*) FROM katalog WHERE godina=G AND serija='sluzbeni';
  SELECT COUNT(*) FROM akti WHERE godina=G;
  -- moraju biti jednaki

AKO NEŠTO PUKNE:
- 06_stats javlja nedostajuće akte prema katalogu (ne prema neprekinutom nizu)
- stariji HTML može tražiti novi fallback selektor u 04_parse.py::parse_html —
  tada PRVO ažuriraj docs/01, pa kod
- mreža je nestabilna: ponovi neuspjeli zahtjev prije nego zaključiš da
  endpoint ne postoji (prolazni 000/timeout se lako krivo protumači)
- broj akta je STRING i može imati padding ('0000') ili slovo — ne castaj u int

PRAVILA: hrvatske commit poruke, commit nakon svake dovršene godine,
ne commitaj data/. Ne mijenjaj shemu bez razloga — migracija je već napravljena
(clanak je TEXT, nema UNIQUE(godina, clanak)).

NE RADI U OVOJ SESIJI: PDF import (zaseban prolaz, samo 2023+) i međunarodne
ugovore — oboje je dokumentirano ali izvan opsega.
