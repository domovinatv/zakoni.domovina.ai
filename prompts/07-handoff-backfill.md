# Handoff prompt — nastavak: backfill 2025 → 1990

Ovaj prompt zalijepi u novi chat (radni direktorij: `/Users/ms/git/domovinatv/zakoni.domovina.ai`).

---

Radiš na projektu **zakoni.domovina.ai** — otvoreni katalog svih akata službenog dijela
Narodnih novina. Stanje: Faze 0, 1 i 3 su gotove i verificirane — cijela 2026. je u bazi
(78 izdanja, 937 akata, svi parsirani), FTS radi, statički export radi, frontend je deployan
na https://zakoni-domovina.pages.dev (Cloudflare Pages projekt `zakoni-domovina`).

**Tvoj zadatak: Faza 2 — backfill godina 2025 → 1990, godinu po godinu unatrag.**

Prije početka OBAVEZNO pročitaj (redom):
1. `prompts/00-kontekst.md` — konvencije i pravila ponašanja
2. `docs/04-backfill-runbook.md` — operativni vodič: naredbe, dijagnostika, reset recepti, QA
3. `prompts/03-backfill.md` — očekivani problemi kod starijih godina i kako ih rješavati

Postupak:
- Kreni s `uv run python scripts/10_backfill.py --samo-godina 2025` (traje ~1.5–2 h;
  pokreni u pozadini i prati). Orkestrator sam staje ako kontrola (`06_stats`) padne.
- Nakon svake dovršene godine: pregledaj stats izlaz, napravi QA iz runbooka §"Kontrola
  kvalitete", pa nastavi na sljedeću stariju godinu.
- Nakon svake 1–2 dovršene godine: `05_build_fts.py` + `07_export_static.py` + deploy
  (`./frontend/scripts/deploy.sh` — pazi: wrangler OAuth ne radi kroz sandbox, vidi runbook).
- Ako naiđeš na problem koji runbook ne pokriva (promijenjen HTML, novi format), prvo
  ažuriraj `docs/01-izvor-podataka-nn.md`, onda kod, pa nastavi.
- Commitaj nakon svake smislene cjeline (dovršena godina / popravak parsera), hrvatske
  commit poruke, push na origin.

Kriterij uspjeha sesije: bar 2–3 nove godine potpuno parsirane (stats exit 0, QA prošao),
stanje commitano i pushano, README status ažuriran, live stranica osvježena.
