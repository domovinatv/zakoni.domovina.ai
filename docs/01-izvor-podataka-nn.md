# Narodne novine — izvor podataka (verificirano 2026-07-19)

Ovaj dokument opisuje **stvarno provjerene** endpointe službenog lista RH (narodne-novine.nn.hr).
Sve navedeno je testirano `curl`-om na datum u naslovu. Nema službenog JSON API-ja, ali postoji
**ELI (European Legislation Identifier)** implementacija s RDF metapodacima — to je naš primarni
strukturirani izvor.

## 1. Identifikacija akta

Svaki akt službenog dijela ima ELI URI:

```
https://narodne-novine.nn.hr/eli/sluzbeni/{godina}/{broj}/{clanak}
```

- `godina` — godina izdanja (npr. 2024)
- `broj` — redni broj izdanja Narodnih novina unutar godine (npr. 1)
- `clanak` — redni broj akta/članka, **sekvencijalan unutar cijele godine** (ne unutar izdanja!)
  - primjer: NN 2024/6 sadrži članak 107 → `eli/sluzbeni/2024/6/107`

HTML stranice članaka imaju oblik (redirect cilja ELI URI-ja):

```
https://narodne-novine.nn.hr/clanci/sluzbeni/{YYYY}_{MM}_{BROJ}_{CLANAK}.html
```

`MM` je mjesec objave izdanja — treba nam za konstrukciju URL-a, dobivamo ga iz rezultata pretrage.

## 2. Formati po aktu (svi vraćaju 200)

| URL | Sadržaj |
|---|---|
| `…/eli/sluzbeni/2024/1/1/rdf` | RDF/XML metapodaci (ELI ontologija) |
| `…/eli/sluzbeni/2024/1/1` + `Accept: application/rdf+xml` | isto (redirect na `article_metadata.aspx?format=rdf`) |
| `…/eli/sluzbeni/2024/1/1/pdf` | službeni PDF (može biti PDF cijelog izdanja, ~2 MB) |
| `…/eli/sluzbeni/2024/1/1/hrv/html` | HTML članka |
| `…/clanci/sluzbeni/full/2024_01_1_1.html` | **čišći HTML** (manje site-chrome, ~39 KB vs ~52 KB) s ugrađenim ELI RDFa meta tagovima |

Ne postoje: `…/1.rdf`, `…/1/xml`, `…/1/html` (404).

## 3. Sadržaj RDF metapodataka (primjer 2024/1/1)

```xml
<eli:type_document rdf:resource=".../resource/authority/document-type/UREDBA"/>
<eli:number>1</eli:number>
<eli:date_document>2024-01-02</eli:date_document>
<eli:date_publication>2024-01-02</eli:date_publication>
<eli:passed_by rdf:resource=".../eli/vocabularies/nn-institutions/19560"/>
<eli:repealed_by rdf:resource=".../eli/sluzbeni/2024/6/107"/>
<eli:based_on rdf:resource=".../eli/sluzbeni/2014/19/360"/>
<eli:is_about rdf:resource="http://eurovoc.europa.eu/1072"/>          <!-- EuroVoc pojmovi -->
<eli:is_about rdf:resource=".../eli/vocabularies/nn-legal-area/20"/>   <!-- pravno područje -->
<eli:is_about rdf:resource=".../eli/vocabularies/nn-index-terms/288"/> <!-- kazalo pojmova -->
<eli:title xml:lang="hrv">Uredba o utvrđivanju najviših maloprodajnih cijena naftnih derivata</eli:title>
```

Ključno za katalog i graf propisa:
- **`type_document`** — tip akta je u samom URI-ju (`UREDBA`, `ZAKON`, `PRAVILNIK`, `ODLUKA`, …)
- **`passed_by`** — donositelj (numerički ID institucije)
- **`repealed_by` / `based_on`** (i srodni ELI predikati poput `changed_by`, `changes`) — veze među
  propisima → gradimo **graf** (što je ukinuto čime, što se temelji na čemu)
- **`is_about`** — EuroVoc + NN klasifikacije za fasetnu pretragu

⚠️ **Rječnici NISU dereferencirabilni**: URI-ji poput `…/vocabularies/nn-institutions/19560` i
`…/resource/authority/document-type/UREDBA` vraćaju 404. Oznake (labele) institucija vadimo iz
HTML-a članka / rezultata pretrage i gradimo **lokalne šifrarnike** koji rastu tijekom backfilla.

## 4. Enumeracija (kako pronaći SVE akte)

Nema sitemap-a ni RDF-a na razini izdanja/godine. Enumeracija ide preko stranice pretrage:

```
https://narodne-novine.nn.hr/search.aspx?sortiraj=4&kategorija=1&godina={G}&broj={B}&rpp=200&qtype=1&pretraga=da
```

- `kategorija=1` = **službeni dio** (`clanci/sluzbeni/…`)
- `kategorija=2` = **međunarodni ugovori** (`clanci/medunarodni/…`) — vidi §7. Ranija verzija ovog
  dokumenta je tvrdila da je to oglasni dio; **netočno**, provjereno 2026-07-19.
- `kategorija=3` i dalje → prazno (ne postoje)
- oglasni dio je na zasebnoj putanji `clanci/oglasi/…` (stečajevi, natječaji, osobni oglasi) —
  nisu pravni akti, **trajno izvan opsega**
- iz HTML-a se izvlače linkovi regexom `clanci/sluzbeni/[0-9_]+\.html` → daje `YYYY_MM_BROJ_CLANAK`
- `rpp=200` je dovoljan (izdanja imaju tipično < 100 akata; provjeriti i paginaciju za sigurnost)
- **Stop-uvjet**: nepostojeći `broj` vraća stranicu s 0 linkova (provjereno za 2026/999).
  Petlja: `broj = 1, 2, 3, …` dok se ne dobiju npr. 3 uzastopna prazna broja.
- Broj izdanja godišnje: ~150–160.

Iz enumeracije dobivamo `(godina, mjesec, broj, clanak)` → iz toga konstruiramo sve ostale URL-ove.

## 5. Pravila pristojnog preuzimanja

- `robots.txt` postoji i eksplicitno zabranjuje tek nekoliko pojedinačnih članaka (ispravljeni/povučeni
  sadržaji) — **te URL-ove preskačemo i bilježimo kao `skipped_robots`**.
- Rate limit: 1–2 zahtjeva/s, jedan worker po godini, `User-Agent` s kontakt e-mailom
  (`zakoni.domovina.ai crawler; stepanic.matija@gmail.com`).
- Sve preuzeto se sprema lokalno (raw sloj) — **nikad ne preuzimati isti URL dvaput** (idempotentnost).

## 6. Opseg podataka (procjena)

- Digitalni arhiv NN-a na webu pokriva ~1990.–danas.
- **Izmjereno** (ne procjena): 2026. (do srpnja) = 78 izdanja / 937 akata; 2025. = 158 izdanja /
  **2.404 akta**, tj. ~15 akata po izdanju. Ranija procjena od 3.000–4.000 akata godišnje i
  120.000+ ukupno bila je previsoka; realnije je **~2.000–2.500 po godini** za moderne godine i
  red veličine **50.000–70.000 akata** za cijeli backfill (starije godine su manje).
- **Izmjerena brzina** uz `MIN_INTERVAL=0.6`: RDF 0,62 s/akt, HTML 0,71 s/akt → **~1,33 s po aktu**.
  2025. (2.404 akta) ≈ 56 min ukupno. Raw cache ~65 KB/akt → ~156 MB za 2025.
- Backfill ide **godinu po godinu, od 2026 prema starijima** (novije = relevantnije, stariji slojevi
  arhive mogu imati drukčiji HTML — parser prilagođavati postupno).

## 7. Međunarodni ugovori (druga serija, zasad NIJE u bazi)

Uz službeni dio, NN objavljuje i seriju **Međunarodni ugovori** — potvrđeni (ratificirani)
međunarodni ugovori. Po čl. 141 Ustava RH oni su po pravnoj snazi **iznad zakona**, pa katalog
bez njih nije pravno potpun.

Provjereno 2026-07-19 (`curl -L`):

| Element | Vrijednost |
|---|---|
| enumeracija | `search.aspx?…&kategorija=2&godina={G}&broj={B}&…` |
| link regex | `clanci/medunarodni/(\d{4})_(\d{2})_(\d+)_(\d+)\.html` |
| ELI URI | `…/eli/medunarodni/{godina}/{broj}/{clanak}` |
| RDF | `…/eli/medunarodni/{G}/{B}/{C}/rdf` → **postoji**, ista ELI struktura kao službeni dio |
| čisti HTML | `…/clanci/medunarodni/full/{YYYY}_{MM}_{BROJ}_{CLANAK}.html` |
| jezici | `is_realized_by` daje **`/hrv` i `/eng`** — dvojezični tekst |

Opseg je malen: **2025. = 11 izdanja / ~47 akata** (usporedbe radi, službeni dio 158/2404).
Cijeli backfill ove serije 1990→2026 je red veličine **< 1 h**.

Primjer 2025/1/1: `type_document=ZAKON`, `passed_by=…/nn-institutions/19505` (Sabor),
`title="Zakon o potvrđivanju Sporazuma između Republike Hrvatske i OECD-a…"`.

⚠️ Za implementaciju treba razlikovati serije — `eli` ključ trenutno ima oblik `sluzbeni/{G}/{B}/{C}`,
pa `medunarodni/{G}/{B}/{C}` prirodno stane u isti prostor ključeva, ali `01_enumerate` i
`nn_client` hardkodiraju `sluzbeni` (vidi `LINK_RE`, `rdf_url`, `full_html_url`).

## 8. Formati koje NAMJERNO ne preuzimamo

- **PDF po aktu** (`…/eli/…/pdf`) — izvorni izgled, ali ~2 MB po aktu (često PDF cijelog izdanja);
  za 120k akata to su TB-i. RDF ionako sadrži URL, pa se može dohvatiti na zahtjev.
- **Oglasni dio** (`clanci/oglasi/…`) — stečajevi, natječaji, osobni oglasi; nisu pravni akti.
