# Plan punog backfilla 1990–2026 (na temelju izmjerenog kataloga)

Sastavljeno 2026-07-20, nakon što je izgrađen katalog cijelog arhiva iz službenog Kazala NN.
**Sve brojke su izmjerene, ne procijenjene** — opseg iz kataloga (`scripts/00_katalog.py`),
brzine i veličine iz stvarnih dohvata 2025. i 2026.

> Ovaj dokument zamjenjuje procjene iz `docs/03-plan-faza.md` §Faza 2.
> Izvorišni nalazi (endpointi, matrica dostupnosti) su u `docs/01-izvor-podataka-nn.md`.

## 1. Stvarni opseg arhiva

`uv run python scripts/00_katalog.py --procjena`

| Desetljeće | Akata | Izdanja |
|---|---:|---:|
| 1990-e | 19.611 | 1.117 |
| 2000-e | 31.892 | 1.549 |
| 2010-e | 29.581 | 1.411 |
| 2020-e (do 7/2026) | 16.477 | 1.000 |
| **UKUPNO** | **97.561** | **5.077** |

Vršne godine: 2008. (4.275), 2009. (3.960), 2007. (3.859). Najmanja: 1990. (1.200).
Najviše izdanja: 2003. (204) i 2004. (189) — više nego danas (~155).

Sastav (cijeli arhiv): odluka 38.222, rješenje 23.434, pravilnik 14.758, ostalo 6.547,
zakon 4.604, uredba 4.277, naredba 1.679, presuda 1.252.
Donositelji: Vlada 24.799, Sabor 7.447, Predsjednik 5.630, HANFA 4.927, Ustavni sud 4.491.

## 2. Trošak punog backfilla

Izmjereno na 2025.: **HTML 0,71 s/akt, RDF 0,62 s/akt**; **HTML 73 KB/akt, RDF 4,5 KB/akt**
(uz `MIN_INTERVAL = 0.6 s`).

| Stavka | Vrijeme | Disk |
|---|---:|---:|
| HTML svih 97.561 akata | 19,2 h | 6,8 GB |
| RDF za 2015–2026 (30.017 akata) | 5,2 h | 0,13 GB |
| Kazalo (37 zahtjeva) | < 1 min | 20 MB |
| **UKUPNO** | **≈ 24,4 h** | **≈ 6,9 GB** |

Već dohvaćeno: 2026, 2025, 2024 (u tijeku) ≈ 5.900 akata → **preostaje ~22 h**.

### Ubrzanja koja su na stolu

- **Rate limit**: NN službeno dopušta **3 req/s**, mi vozimo 1,5 (`MIN_INTERVAL=0.6`).
  Spuštanje na `0.34` prepolovljuje vrijeme → **~12 h**. Preporuka: `0.4` (2,5 req/s),
  ostavlja rezervu, daje ~14 h.
- **Kazalo umjesto `search.aspx`**: štedi 94 MB kesa i ~160 zahtjeva **po godini**
  (5.077 zahtjeva ukupno → 37). Već implementirano u `00_katalog.py`.
- Paralelizam se **ne** preporučuje — rate limit je po klijentu, ne po konekciji.

## 3. Arhitektura: katalog-first

Redoslijed se mijenja u odnosu na Fazu 1/2:

```
00_katalog   Kazalo CSV po godini  -> tablica `katalog`   (37 zahtjeva, autoritativan popis)
   ↓         iz kataloga se pune `izdanja` i `akti` (naslov, vrsta, donositelj)
03_fetch_html  HTML po aktu        -> raw cache          (jedini dohvat koji skalira)
04_parse       tekst               -> `akt_tekst`
02_fetch_rdf   samo 2015+          -> EuroVoc, graf veza (obogaćivanje, nije nužno)
05_build_fts / 07_export_static
```

`01_enumerate` (struganje `search.aspx`-a) postaje **suvišan** — katalog daje isto,
točnije i 137× jeftinije. Zadržati ga samo kao rezervu ako Kazalo ikad zakaže.

### Što katalog NE daje

`datum_akta`, `datum_objave`, EuroVoc oznake i graf veza (`based_on`, `repeals`, …)
dolaze isključivo iz RDF-a → **postoje samo za 2015–2026**. Za 1990–2014 katalog daje
naslov, vrstu i donositelja, a datum se može izvesti iz datuma izdanja.

## 4. Redoslijed izvođenja

| Korak | Godine | Trajanje | Napomena |
|---|---|---|---|
| 1 | 2024 | ~1 h | u tijeku, dovršiti postojećim putem |
| 2 | migracija sheme | minute | ukloniti `UNIQUE(godina, clanak)` iz `akti` (§5) |
| 3 | 2023–2015 | ~9 h | ima RDF; puni metapodaci |
| 4 | 2014–2000 | ~8 h | **bez RDF-a** — katalog je jedini izvor metapodataka |
| 5 | 1999–1990 | ~4 h | najstariji HTML, očekivati rad na parseru |
| 6 | međunarodni ugovori | < 1 h | `--serija medunarodni`, cijeli raspon |
| 7 | PDF izdanja 2023–2026 | ~2 h, 1,5 GB | 100 % vjeran tekst za 4 godine (§6) |

Nakon svake godine: QA iz `docs/04-backfill-runbook.md`, pa commit.

## 5. Otkriveni problemi koje treba riješiti prije nastavka

1. **`UNIQUE (godina, clanak)` u `akti` je neispravan.** Broj akta nije jedinstven unutar
   godine: 2008. ima **57** brojeva koji se ponavljaju u dva izdanja
   (`NN 100/2008 br. 3042` ≠ `NN 101/2008 br. 3042`), 2011. ih ima 5, ukupno 69 kroz arhiv.
   Backfill bi na 2008. pukao na `IntegrityError`. Shema je ispravljena, ali **postojeća
   tablica treba migraciju** (`CREATE TABLE IF NOT EXISTS` ne mijenja zatečenu).
2. **`clanak INTEGER` je neispravan.** `sluzbeni/2024/102/0000` je stvarna Odluka Ustavnog
   suda; ELI radi samo s punim paddingom (`/0000/rdf` → 200, `/0/rdf` → 404). API
   dokumentacija kaže da `act_num` „vrlo rijetko sadrži slovo". Treba `TEXT`, kao u `katalog`.
3. **QA upit u runbooku ne hvata prazan tekst** — provjerava `tekst IS NULL`, a parser upisuje
   prazan string. Pravi udio praznih za 2025. je 4,74 % (114 akata), ne 0 %.
4. **Prazan HTML za zadnje izdanje.** NN objavi PDF prije HTML-a; `fetch_cached` trajno
   kešira prazan omot i nikad ga ne osvježi. Treba ne-kesirati odgovore bez sadržaja.

## 6. PDF: vrijedi samo za 2023+

PDF cijelog izdanja (`/eli/sluzbeni/{G}/{B}/pdf`) postoji **od 2023.** i ima pravi tekstualni
sloj (nije skenirano). Akti su unutar njega razgraničeni brojem akta u vlastitom retku, a
brojeve već imamo iz kataloga → rezanje je determinističko.

Za 4 godine (2023–2026, ~8.400 akata) to je ~630 zahtjeva i ~1,5 GB, i daje **100 % pokrivenost
teksta** uključujući akte kojima HTML nedostaje. Prije 2023. PDF-a nema, pa ta strategija
ne skalira na arhiv.

⚠️ Kod rezanja tražiti markere **rastućim redoslijedom pozicije**, ne samo vrijednosti —
brojevi iz tablica inače daju lažne pogotke (provjereno na NN 78/2026).

## 7. Provjera ispravnosti dosadašnjeg rada

Katalog je neovisan izvor pa služi i kao kontrola. Za 2025. se poklapa **do zadnjeg akta**:
2.404 ukupno; odluka 1.245, rješenje 359, pravilnik 332, uredba 113, zakon 102.

Nakon svake dovršene godine vrijedi pokrenuti istu usporedbu:

```sql
SELECT k.godina, COUNT(DISTINCT k.eli) AS u_katalogu, COUNT(DISTINCT a.eli) AS u_bazi
FROM katalog k LEFT JOIN akti a ON a.eli = 'sluzbeni/'||k.godina||'/'||k.broj||'/'||k.clanak
WHERE k.godina = :g GROUP BY k.godina;
```
