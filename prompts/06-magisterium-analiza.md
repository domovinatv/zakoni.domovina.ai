# Prompt: Faza 5 — Teološka analiza s Magisterium AI (smoke test)

Učitaj `prompts/00-kontekst.md`. Preduvjet: akti ciljanih područja parsirani u bazi.
Alat: **Magisterium AI MCP** (`mcp__claude_ai_Magisterium_AI__search` za izvore,
`…__chat` za citirani odgovor). Ako MCP nije spojen, stani i javi korisniku.

## Cilj

Za odabrane akte utvrditi odnos hrvatskog civilnog prava prema nauku Katoličke Crkve
(Magisterium: KKC, enciklike, dokumenti kongregacija, kanonsko pravo) — s **citatima izvora**,
bez vlastitih tvrdnji bez pokrića.

## Smoke test — odabir akata (5–10 komada)

FTS pretragom u bazi nađi važeće akte iz etički osjetljivih područja, npr.:
- pobačaj / "prekid trudnoće" (Zakon o zdravstvenim mjerama o pravu na slobodno odlučivanje o rađanju djece)
- medicinski pomognuta oplodnja
- brak i obitelj (Obiteljski zakon, životno partnerstvo)
- eutanazija / skrb na kraju života
- nedjelja kao neradni dan (trgovina)
- vjeronauk / odnos države i vjerskih zajednica

Prednost daj aktima tipa `ZAKON` koji su na snazi (nemaju `repealed_by` vezu).

## Postupak po aktu

1. Iz baze uzmi naslov + ključne članke teksta (ne cijeli tekst — sažmi relevantne odredbe).
2. `Magisterium search`: nađi relevantne dokumente nauka za temu odredbe.
3. `Magisterium chat`: postavi konkretno pitanje ("Što Magisterium naučava o X? Navedi izvore.")
   — po potrebi više upita za više spornih odredbi.
4. Napiši analizu (markdown) sa strukturom:
   - **Sažetak akta** (što regulira, ključne odredbe s brojevima članaka)
   - **Nauk Crkve** (citati s referencama: dokument, broj/paragraf)
   - **Usporedba po odredbama** (tablica: članak zakona ↔ nauk ↔ ocjena)
   - **Ukupna ocjena**: `uskladjen` | `napetost` | `sukob` | `nije_primjenjivo`
   - **Ograničenja analize** (što AI nije mogao provjeriti; analiza je informativna, ne autoritativna)
5. Spremi u `analize` (akt_eli, vrsta='magisterium', model, ocjena, sazetak, analiza_md)
   preko `scripts/30_analiza_magisterium.py --eli sluzbeni/GGGG/B/C --file analiza.md`
   (skripta samo upisuje/čita bazu; sam LLM korak radi agent interaktivno u ovoj fazi).
6. Kopiju markdowna spremi i u `data/analize/{godina}_{broj}_{clanak}.md` (git-ignored zasad).

## Pravila kvalitete

- **Svaka tvrdnja o nauku Crkve mora imati citat** iz Magisterium AI odgovora (dokument + broj).
- Razlikuj razine autoritativnosti (dogma / redoviti nauk / disciplinske norme).
- Ne izmišljaj brojeve članaka zakona — citiraj iz `akt_tekst`.
- Piši hrvatski, trijezno i precizno; ovo je istraživačko-informativni sadržaj.

## Verifikacija ("Gotovo kad")

- ≥ 5 redaka u `analize` s popunjenim svim poljima
- nasumična analiza pročitana naglas "drži vodu": svaki citat ima referencu, tablica usporedbe
  referencira stvarne članke zakona
- kratki izvještaj korisniku: koje ocjene su dodijeljene i zašto (po aktu jedna rečenica)
