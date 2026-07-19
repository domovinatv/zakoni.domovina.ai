# Narodne novine — izvor podataka (verificirano 2026-07-19)

Ovaj dokument opisuje **stvarno provjerene** endpointe službenog lista RH (narodne-novine.nn.hr).
Sve navedeno je testirano `curl`-om.

> **Revizija 2026-07-20.** Ranija verzija je tvrdila „nema službenog JSON API-ja". **Netočno.**
> NN ima službenu dokumentaciju pristupa podacima i **javni REST API**:
> - `https://narodne-novine.nn.hr/data_access_hr.aspx` — pristup podacima (sitemapovi, kazala, formati)
> - `https://narodne-novine.nn.hr/nn_api_hr.aspx` — **NN API**, dokument v1.0 od 18. 4. 2023.
>
> Prvi prolaz (Faze 0–2) izgrađen je reverse-engineeringom `search.aspx`-a prije nego što je ta
> dokumentacija pročitana. Radi, ali **API je bolji put** — vidi §9 i §10.

## 0. Matrica dostupnosti po godinama (izmjereno 2026-07-20)

Ovo je najvažnija tablica u dokumentu — određuje što je uopće moguće po godini.

| Izvor | Raspon | Posljedica |
|---|---|---|
| **HTML** (`clanci/…/full/…`) | **1990/91 → danas** | jedini izvor koji pokriva cijeli backfill |
| **ELI / RDF metapodaci** | **2015 → danas** (`/api/index` to potvrđuje) | za 1990–2014 **nema** tipa akta, donositelja, EuroVoca ni grafa veza |
| **PDF po aktu** i **PDF cijelog izdanja** | **2023 → danas** | prije 2023. samo iznimno (veliki akti, npr. državni proračun) |
| **NN API** (`/api/*`) | prati ELI, dakle 2015 → danas | enumeracija bez struganja HTML-a |

Provjereno: `/eli/sluzbeni/2015/1/1/rdf` → 200, `2014/1/1/rdf` → 404; `full/1991_01_1_1.html` → 200;
`/eli/sluzbeni/2023/1/pdf` → 200, `2022/1/pdf` → 404.

⚠️ **Za 25 od 37 godina backfilla (1990–2014) RDF ne postoji.** Te godine daju samo naslov i tekst
iz HTML-a; `tip_akta` i donositelj moraju se izvoditi heuristički (vidi `prompts/03-backfill.md`).
To nije rubni slučaj nego dvije trećine posla.

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

## 9. NN API (službeni, dokumentiran) — PREPORUČENI put enumeracije

Dokumentacija: `https://narodne-novine.nn.hr/nn_api_hr.aspx` (v1.0, 18. 4. 2023.).
Sve provjereno uživo 2026-07-20.

| # | Endpoint | Metoda | Ulaz | Izlaz |
|---|---|---|---|---|
| I | `/api/act` | POST | `{part,year,number,act_num,format}` | metapodaci (JSON-LD ili RDF/XML) |
| II | `/api/index` | GET | — | popis godina s ELI metapodacima |
| III | `/api/editions` | POST | `{part,year}` | popis brojeva izdanja |
| IV | `/api/acts` | POST | `{part,year,number}` | popis brojeva akata u izdanju |

- `part` = `"SL"` (službeni) ili `"MU"` (**međunarodni** — rješava i §7 elegantno). Oglasi (OG) nisu podržani.
- `format` = `"JSON-LD"` ili `"RDF/XML"`.
- **`act_num` je STRING** — dokumentacija izričito kaže „vrlo rijetko sadrži slovo".
- **Službeni rate limit: 3 zahtjeva/s** (mi vozimo 1,5 — smijemo dvostruko brže).

Stvarni odgovori:

```
GET /api/index          -> [2015,…,2026]
POST /api/editions {"part":"SL","year":2024}          -> [1,2,…,155]
POST /api/acts {"part":"SL","year":2024,"number":102} -> ["1782","0000","1783",…]
```

**Zašto je bolji od `search.aspx`:** daje autoritativan popis izdanja i akata bez regexa nad HTML-om,
bez heuristike „3 prazna broja zaredom = kraj", i bez rizika od paginacije. Primjer iz dokumentacije
pokazuje da popis izdanja **može imati rupe** (2023: nedostaju 2 i 18) — naša stop-heuristika bi na
takvoj godini mogla stati prerano.

⚠️ Vrijedi samo za 2015+. Za 1990–2014 ostaje enumeracija preko `search.aspx`.

## 10. Sitemapovi i kazala (još neiskorišteno)

- **Kaskadni sitemapovi**: `https://narodne-novine.nn.hr/sitemap.xml` grana se na po jedan XML po
  izdanju, npr. `sitemap_1_2023_28.xml`, koji sadrži URL-ove svih propisa tog izdanja u NN i ELI
  obliku. Službeno namijenjeno crawlerima → **legitiman put enumeracije i za godine bez API-ja**.
- **Kazala**: „dohvat pojmovnih i kronoloških kazala za odabrane godine, kao i dohvat svih propisa
  za odabranu godinu u **XLSX ili CSV** obliku (vidi »Kazalo«)" — masovni dohvat metapodataka za
  cijelu godinu u jednom zahtjevu. **Nije istraženo, a djeluje kao najveći prečac za backfill.**

## 11. Brojevi akata nisu cijeli brojevi

Akt `sluzbeni/2024/102/0000` je stvarna **Odluka Ustavnog suda RH** (U-IIIA-1422/2024), objavljena
pod brojem `0000`. ELI URL radi samo s punim paddingom:

```
/eli/sluzbeni/2024/102/0000/rdf -> 200
/eli/sluzbeni/2024/102/0/rdf    -> 404
```

Naša shema ima `clanak INTEGER`, pa se `0000` sprema kao `0` i URL se razbije → `status=greska`.
API dokumentacija potvrđuje da je `act_num` string koji „vrlo rijetko sadrži slovo".
**Ispravak: čuvati izvorni string oblik broja akta za konstrukciju URL-ova i ELI ključa.**
