# Nalazi iz sesije 2026-07-20 i otvorena pitanja

Zabilježeno da se ne izgubi između sesija. Sve provjereno uživo; gdje nije, izričito piše.
Endpointi i matrica dostupnosti su u `docs/01`, brojke i raspored u `docs/05`.
Ovdje su **stvari koje se nigdje drugdje ne vide iz koda**.

## 1. Kako je pipeline nastao i zašto se mijenja

Faze 0–2 izgrađene su reverse-engineeringom `search.aspx`-a, prije nego što je pročitana
službena stranica `data_access_hr.aspx`. Rezultat radi i **verificirano je točan** (§4), ali:

| | reverse-engineered | službeni put |
|---|---|---|
| enumeracija | 5.077 zahtjeva + 94 MB keša/god | Kazalo: **37 zahtjeva ukupno** |
| metapodaci 1990–2014 | ne postoje (nema RDF-a) | Kazalo daje vrstu i donositelja |
| granica godine | heuristika „3 prazna zaredom" | `/api/editions` ili `getEditionMaxNumber` |
| rate limit | pretpostavljen 1,5 req/s | službeno dopušteno **3 req/s** |

Pouka za sljedeći izvor podataka: **prvo potraži „pristup podacima / API / open data"
stranicu**, pa tek onda reverse-engineeraj.

## 2. Greške u vlastitoj dokumentaciji koje su ispravljene

Sve tri su bile neprovjerene tvrdnje zapisane kao činjenice:

1. „`kategorija=2` je oglasni dio" → zapravo **međunarodni ugovori**.
2. „nema službenog JSON API-ja" → **postoji**, dokumentiran od 2023.
3. „`clanak` je sekvencijalan unutar godine" → **nije jedinstven**; 2008. ima 57 brojeva
   koji se ponavljaju u dva izdanja.

Zaključak: negativne tvrdnje („X ne postoji") zapisivati s datumom i načinom provjere.

## 3. Zamke pri provjeravanju nn.hr

- **`curl` bez `-L`** vraća prazno — sve stranice redirectaju. Sondiranje bez `-L` daje
  lažni zaključak „nema sadržaja".
- **Mreža na ovoj mašini je nestabilna.** Prolazni `000`/timeout dvaput je zamalo protumačen
  kao „RDF ne postoji za međunarodne ugovore"; tek treći pokušaj vratio je 200. Uvijek
  `--retry 3 --retry-delay 5` i `-4` (nema IPv6 rute). Isto vrijedi za `git push`.
- **Sučelje je JS-driven** — Kazalo nije linkano u HTML-u; nađeno je čitanjem
  `js/drop-down-controller.js`. Ako nešto „ne postoji" na stranici, pogledaj JS.

## 4. Neovisna potvrda ispravnosti ingesta

Kazalo ne dijeli nijednu liniju koda s našim pipelineom, pa služi kao kontrola.
Za 2025. poklapanje je **potpuno**: 2.404 akta; odluka 1.245, rješenje 359, pravilnik 332,
uredba 113, zakon 102 — identično u oba izvora. Za 2024. se poklapa ukupan broj (2.576 u oba),
puna usporedba po vrstama pokrenuta je nakon dovršetka godine.

Upit za ponavljanje te provjere je u `docs/05` §7. **Vrijedi je pokrenuti nakon svake godine.**

## 5. Otvorena pitanja (nisu riješena)

1. **Gubi li se struktura u aktima koji IMAJU tekst?** Provjereno je samo koliko akata ima
   prazan tekst (2025: 4,74 %). **Nije** provjereno gube li se tablice i prilozi kod akata
   s naizgled urednim tekstom. Za RAG je to potencijalno veći problem od praznih akata —
   izmjeriti usporedbom HTML vs PDF teksta na uzorku prije gradnje RAG-a.
2. **Kronološko i pojmovno kazalo** (`/files/kazalo_pdf/…`, 1997–2025) nisu istraženi.
   Pojmovno kazalo bi moglo dati temu/ključne riječi za godine bez EuroVoca (prije 2015).
3. **Kazalo za međunarodne ugovore** — `get_index_file.aspx` je testiran samo za službeni
   dio. Treba provjeriti postoji li parametar za `MU`, ili se ide preko `/api/acts` s
   `part=MU` (radi za 2015+).
4. **Zadnje izdanje trajno ostaje bez teksta.** NN objavi PDF prije HTML-a, a `fetch_cached`
   trajno kešira prazan omot i nikad ga ne osvježi. Za NN 78/2026 HTML je i tri dana kasnije
   bio prazan. Treba **ne kesirati odgovore bez sadržaja** — inače se rupa nikad ne zatvori.
5. **Praznih akata u 2025. je 114**, većinom „Odluka o uvođenju strukovnog kurikula" —
   dokumenti s tablicama koji izlaze samo kao PDF prilog. Pravno rubno, ali za potpunost
   kataloga vrijedi ih pokriti PDF importom (2023+ ionako, stariji nemaju PDF).

## 6. Sitnice koje se lako zaborave

- `akt_num` je **string** i „vrlo rijetko sadrži slovo" (službena dokumentacija API-ja).
  `sluzbeni/2024/102/0000` je stvarna Odluka Ustavnog suda; `/0000/rdf` → 200, `/0/rdf` → 404.
- Kolektivni ugovori legitimno **nemaju donositelja** (`passed_by`) — potpisuju ih sindikati
  i poslodavci, ne državno tijelo. Nije greška ingesta.
- Kazalo je **tab-separated** unatoč `type=csv`, i ima **BOM** (`utf-8-sig`).
- U Kazalu prazna vrijednost je `-`, ne prazan string → treba `NULLIF(x, '-')`.
- `sqlite3.connect` bez `busy_timeout` puca na „database is locked" čim dvije skripte rade
  paralelno; dodano u `db.connect()`.
- Rezanje akata iz PDF-a izdanja: markere tražiti **rastućim redoslijedom pozicije**, ne samo
  vrijednosti — brojevi iz tablica inače daju lažne pogotke (provjereno na NN 78/2026).
