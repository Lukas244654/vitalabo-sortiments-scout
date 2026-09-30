# Pipeline im Detail

Dieses Dokument beschreibt genau, was der Code tut: jede Datei, jeden Schritt, die wörtlichen Prompts und die konkreten Zwischenergebnisse mit den Daten vom 30.09.2026.

> **Finaler Stand, 30.09.2026:** 210 Listeneinträge, 209 eindeutige Produkte, 202 relevante Supplements, 71 externe Marken, davon 9 bei Vitalabo geführt; 12 Marken-Lücken und 15 Produktkonzepte vollständig bewertet. Alle KI-Schritte wurden über OpenRouter mit `anthropic/claude-sonnet-5.5` durchgeführt. Das Profil ist `config/vitalabo-sonnet55.toml`. Die Beispiele unten erläutern Aufbau und Prompts; verbindlich sind der Code und die bereinigten Ergebnisse in `docs/results.json`.
>
> **Betriebsstatus:** Ein Tagesstand pro Quelle, noch keine Wochenzeitreihe. iHerb wurde manuell erfasst. Wikipedia lieferte in diesem Lauf keine Daten. Der Bericht ist eine statische Momentaufnahme; kein Scheduler und kein GitHub Action sind aktiviert.
>
> **Interpretation:** Ränge und Listenpräsenz sind beobachtete Marktsignale, keine gemessenen Verkaufszahlen oder Kundenbedürfnisse. Die Bezeichnung „Nachfrage“ im Code und in den wörtlichen Prompts meint diesen Proxy. Fit, Trend und Beziehbarkeit sind KI-Einschätzungen, die geprüft werden müssen. Sechs Trendbewertungen haben keine Webquellen. Gewichte 50/25/25 und Abdeckungsgrenzen 0/1–9/10+ sind konfigurierbare Annahmen, nicht aus Geschäftsdaten gelernt.
>
> **Vertraulichkeit:** Rohes `results.json` und `report.html` enthalten CSV-Produkttitel unter `vitalabo_examples` und bleiben lokal. `publish_report.py` entfernt diese Beispiele für die öffentlichen Artefakte. Siehe [Review](REVIEW.md) für die konkreten Grenzen.

---

## Überblick

```
                          run_scout.py --step collect   (täglich)
                          ────────────────────────────
  Amazon.de via Apify ──▶ data/signals/amazon/2026-09-30.json
  iHerb (manuell)     ──▶ data/signals/iherb/2026-09-30.json

                          run_scout.py --step weekly    (wöchentlich)
                          ────────────────────────────
  1  Signale laden             signals.py   load_window()         Code
  2  Vitalabo-Bestand laden    catalog.py   Catalog               Code
  3  Titel normalisieren       analyze.py   normalize()           KI  (Sonnet 5.5 im finalen Lauf)
  4  Verdichten + Abgleich     analyze.py   aggregate()           Code
  5  Fit + Trends bewerten     analyze.py   assess_brands()       KI  (starkes Modell + Websuche)
                                            assess_trends()       KI  (starkes Modell + Websuche)
                               trends.py    measure_many()        Code (Wikipedia-Aufrufe)
  6  Priorisieren + Bericht    analyze.py   prioritize_brands()   Code
                               report.py    render()              Code
                          ──▶ output/vitalabo/results.json + report.html
```

**Grundsatz:** Die KI liest und bewertet. Gezählt, abgeglichen und gewichtet wird im Code. Dadurch ist jedes Ergebnis nachprüfbar.

---

## Eingaben

| Datei | Inhalt | Stand 30.09.2026 |
|---|---|---|
| `data/signals/amazon/2026-09-30.json` | Rohdaten des Apify-Scrapers: Amazon.de „Vitamine, Mineralien & Ergänzungsmittel“, Bestseller + Neuerscheinungen | 200 Einträge (100 + 100) |
| `data/signals/iherb/2026-09-30.json` | iHerb Top-Seller „Supplements & Nährstoffe“, manuell erfasst | 10 Einträge |
| `data/vitalabo-produktdaten.csv` | Vitalabo-Export (EAN, Bezeichnung, Marke), vertraulich | 4.520 Produkte, 133 Marken |
| `data/marken_vitalabo_at.txt` | Markenliste von vitalabo.at/marken | ca. 330 Marken |
| `config/vitalabo.toml` | alles Shop-Spezifische | – |

---

## Täglicher Sammler — `signals.py: collect_amazon()`

Ruft den Apify-Scraper `junglee/amazon-bestsellers` synchron auf und speichert die Antwort unverändert als Tagesdatei.

Anfrage an `https://api.apify.com/v2/acts/junglee~amazon-bestsellers/run-sync-get-dataset-items`:

```json
{"categoryUrls": ["https://www.amazon.de/gp/bestsellers/drugstore/64374031/",
                  "https://www.amazon.de/gp/new-releases/drugstore/64374031/"],
 "maxItemsPerStartUrl": 100, "depthOfCrawl": 1}
```

Ein Rohdatensatz (echt):

```json
{"position": 2,
 "name": "natural elements Magnesium Bisglycinat - Premium: Chelatiertes Magnesium - 180 Kapseln - 300mg ...",
 "asin": "B07NS14648", "price": {"value": 17.99, "currency": "€"},
 "stars": 4.6, "reviewsCount": 11193,
 "input": "https://www.amazon.de/gp/bestsellers/drugstore/64374031/"}
```

Kosten: 1,18 $ pro Lauf (200 Produkte, Apify-Gratisplan). iHerb wird im Prototyp nicht automatisch gesammelt.

---

## Schritt 1 — Signale laden · `signals.py: load_window()`

Liest alle Tagesdateien der letzten 7 Tage (`window_days`) je Quelle und bringt sie in ein einheitliches Format. Dabei:
- Fehlerzeilen des Scrapers werden verworfen.
- Doppelte Einträge (gleiche Liste, gleicher Rang) werden entfernt; der Scraper liefert Seiten teils doppelt.
- Die Liste (Bestseller/Neuerscheinung) wird aus der Start-URL abgeleitet.

Ergebnis für den Datensatz oben:

```json
{"source": "amazon", "list": "bestsellers", "rank": 2,
 "name": "natural elements Magnesium Bisglycinat - Premium: ...",
 "url": "https://www.amazon.de/dp/B07NS14648", "id": "amazon:B07NS14648",
 "reviews": 11193, "rating": 4.6, "price": 17.99, "date": "2026-09-30"}
```

iHerb-Eintrag im selben Format (Marke ist hier schon bekannt und wird als Hinweis mitgegeben):

```json
{"source": "iherb", "list": "topsellers", "rank": 1,
 "name": "Swanson Vitamins Lithiumorotat, 5 mg, 60 pflanzliche Kapseln",
 "id": "iherb:Swanson Vitamins Lithiumorotat, ...", "brand_hint": "Swanson Vitamins", "date": "2026-09-30"}
```

**Stand:** 210 Einträge, 209 eindeutige Produkte.

---

## Schritt 2 — Vitalabo-Bestand laden · `catalog.py`

- `load_products()` liest den Export (EAN, Bezeichnung, Marke), dedupliziert nach EAN.
- `load_site_brands()` liest die Markenliste der Website.
- `Catalog` vereint beides: **333 Marken** gelten als „geführt“.

Zwei Prüfungen, beide reiner Code:

**Marke geführt?** `match_brand()`: Name normalisieren (Kleinschreibung, ® und ™ entfernen, Rechtsformen wie GmbH streichen), dann exakter Treffer oder Enthaltensein als ganze Wortfolge (mindestens 4 Zeichen).
- „Doppelherz“ → Treffer „Doppelherz“
- „natural elements“ → kein Treffer (auch nicht „Natural Point“, weil nur ganze Wortfolgen zählen)

**Wirkstoff abgedeckt?** `coverage()`: zählt Export-Produkte, deren Name einen der Suchbegriffe enthält.
- 0 Treffer → **Lücke**, 1–9 → **dünn**, ab 10 → **abgedeckt**

---

## Schritt 3 — Titel normalisieren · `analyze.py: normalize()` · KI

**Warum KI:** Amazon übersetzt Markennamen („Double Heart“ ist Doppelherz), Titel haben keine feste Struktur, und die Marke steht nicht immer am Anfang. Mit Regeln scheitert das; der Testlauf ohne KI hat genau diese Fehler produziert.

**Modell im finalen Lauf:** Rolle `classify`, ausschließlich `anthropic/claude-sonnet-5.5` aus `config/vitalabo-sonnet55.toml`. Die ursprüngliche Konfiguration `config/vitalabo.toml` hat andere Fallbacks.
**Aufruf:** 60 Titel pro Anfrage, Temperatur 0, also 4 Aufrufe für 209 Titel. Ergebnisse werden je Produkt in `output/vitalabo/normalized.json` gespeichert; in der nächsten Woche werden nur neue Produkte normalisiert.

**System-Prompt (wörtlich):**

```
Du normalisierst Produkttitel von Amazon und iHerb für einen Händler von Nahrungsergänzungsmitteln.
Pro Titel: (1) brand = der echte Markenname in seiner Originalschreibweise – Amazon übersetzt Marken teils
("Double Heart" = "Doppelherz"); ist keine Marke erkennbar (No-Name/Generika), dann "".
(2) wirkstoff = zentraler Wirkstoff bzw. Produktkonzept als kurzer deutscher Begriff, wie ein Wikipedia-Artikel
(z. B. "Magnesium", "Kollagen", "Lymphdrainage", "Berberin", "TUDCA").
(3) begriffe = 2–4 Suchbegriffe (deutsch/englisch, Kleinschreibung), mit denen man denselben Wirkstoff in
Produktnamen findet. (4) code = Warengruppe aus der Liste. (5) relevant = false für Nicht-Supplements
(Pflaster, Kosmetik, Geräte, Lebensmittel ohne Ergänzungszweck).
Antworte nur mit JSON {"<id>": {"brand":"","wirkstoff":"","begriffe":[],"code":"","relevant":true}}.
```

**User-Nachricht (Aufbau):**

```
Warengruppen:
VIT – Vitamine
MIN – Mineralstoffe & Spurenelemente
... (24 Gruppen aus config/vitalabo.toml)

Titel (id|Titel):
0|natural elements Magnesium Bisglycinat - Premium: Chelatiertes Magnesium - 180 Kapseln ...
1|Double Heart Omega-3 1400 | High dose omega-3 concentrate plus vitamin E ...
...
```

**Beispielantwort (Format):**

```json
{"0": {"brand": "natural elements", "wirkstoff": "Magnesium", "begriffe": ["magnesium", "bisglycinat"], "code": "MIN", "relevant": true},
 "1": {"brand": "Doppelherz", "wirkstoff": "Omega-3", "begriffe": ["omega-3", "omega 3", "fischöl"], "code": "OMEGA", "relevant": true}}
```

Ohne KI (`--no-llm`) greift eine bewusst grobe Heuristik: erstes Wort als Marke, Wirkstoff per Stichwortliste. Sie dient nur zum Testen und ist im Bericht als Testlauf markiert.

---

## Schritt 4 — Verdichten und abgleichen · `analyze.py: aggregate()` · Code

**Pro Produkt** über alle Tage des Fensters:
- bester Rang je Liste, Tage in der Liste, letzte Bewertungsanzahl
- **Signalpunkte:**

```
Punkte = Σ über Listen [ Gewicht(Liste) × (Listenlänge + 1 − Rang) / Listenlänge ] × Tage in der Liste / Tage im Fenster
Gewicht: Bestseller 1,0 · Top-Seller (iHerb) 1,0 · Neuerscheinung 0,8
Listenlänge: Amazon 100 · iHerb 10
```

Beispiel natural elements Magnesium (Bestseller #2, 1 von 1 Tag): 1,0 × (101 − 2) / 100 × 1 = **0,99**.
Beispiel iHerb #1 Swanson Lithiumorotat: 1,0 × (11 − 1) / 10 × 1 = **1,0**.

**Pro Marke:** Summe der Punkte = **Signalstärke**, dazu Anzahl Produkte, davon neu, Quellen, bester Rang, Summe der Bewertungen, häufigste Warengruppe, und **`carried_as`** (Treffer aus Schritt 2 oder leer).

**Pro Wirkstoff:** Varianten werden zusammengefasst („Kreatin Monohydrat“ → „Kreatin“, „Magnesium Komplex“ → „Magnesium“). Dann: Anzahl Produkte, davon Neuerscheinungen, davon Bestseller, Quellen, **No-Name-Anteil** (viele Produkte ohne Marke deuten auf Hype-Ware), Treffer im Vitalabo-Export und Einstufung Lücke/dünn/abgedeckt.

Sortierung der Wirkstoffe (Frühsignal vor Volumen):

```
2 × Neuerscheinungen + Produkte + (3 bei Lücke, 1 bei dünn) + (2 wenn auch auf iHerb)
```

**Auswahl für Schritt 5:** die 12 stärksten Marken ohne `carried_as` (`top_brand_gaps`) und die 15 ersten Wirkstoffe (`top_trends`).

**Zwischenstand vor dem KI-Lauf (echte Daten, Marken von Hand geprüft):**

| Marke | Produkte in den Top 100 | Bester Rang | Bewertungen | geführt |
|---|---|---|---|---|
| natural elements | 18 | #2 | ca. 221.000 | nein |
| Sunday Natural | 9 + 4 Neuerscheinungen | #3 | ca. 9.700 | nein |
| Naturtreu | 5 + 1 | #34 | ca. 17.700 | nein |
| Wehle | 1 | #4 | ca. 20.000 | nein |
| Kijimea | 1 | #9 | ca. 12.300 | nein |
| ESN | 10 + 1 | #12 | ca. 45.600 | ja |
| Doppelherz (auch als „Double Heart“) | 5 + 1 | #30 | ca. 16.900 | ja |
| Glow25 | 2 | #1 | ca. 8.500 | ja |

---

## Schritt 5a — Fit der Marken-Lücken · `analyze.py: assess_brands()` · KI mit Websuche

**Warum KI:** Die Listen zeigen Nachfrageindikatoren, nicht Beziehbarkeit oder tatsächliche Verkaufszahlen. Ob eine Marke an Händler liefert oder nur direkt verkauft, muss recherchiert werden.

**Modell im finalen Lauf:** Rolle `research`, ausschließlich `anthropic/claude-sonnet-5.5`, mit OpenRouter-Websuche (10 Treffer). **Ein Aufruf** für alle 12 Marken.

**System-Prompt (wörtlich, auch für 5b):**

```
Du bist Category Manager:in eines Onlinehändlers für Nahrungsergänzung im DACH-Raum. Du recherchierst im Web,
stützt Aussagen auf Belege und bist ehrlich, wenn Belege fehlen. Antworte ausschließlich mit JSON.
```

**User-Nachricht (wörtlich, Platzhalter in spitzen Klammern):**

```
Shop: Vitalabo (https://www.vitalabo.at). <Positionierung aus der Konfiguration>

Diese Marken verkaufen sich auf Amazon.de bzw. iHerb nachweislich gut (Bestseller-/Neuheitenlisten), der Shop führt sie nicht:
- natural elements (Mineralstoffe & Spurenelemente): 18 Produkte in den Listen, bester Rang 2, 221000 Bewertungen; z. B. natural elements Magnesium Bisglycinat ...
- ...

Die Nachfrage ist gemessen. Recherchiere je Marke kurz: Hersteller/Herkunft, Positionierung, Vertriebsweg
(eigener Shop, Amazon, Apotheke, Händler?) und ob ein Bezug durch einen Onlinehändler realistisch ist.
Bewerte von 1 (schwach) bis 5 (sehr stark):
- ecommerce_fit: versandfähig, nicht apotheken-/verschreibungspflichtig, Wiederkauf bzw. Abo-Eignung, Warenkorbwert, lagerfähig, wenig Beratungs-/Retourenaufwand
- niceshops_fit: Premium/Nische statt Massenmarkt, ergänzt statt kannibalisiert, Bezug über Hersteller/Distributor realistisch (reine Direktvertriebs- oder Amazon-only-Marken abwerten), passt zur Zielgruppe

JSON: {"brands":[{"brand":"","herkunft":"","beschreibung":"1 Satz","vertrieb":"z. B. D2C + Amazon, auch Händler",
"beziehbar":"ja|unklar|eher nein","begruendung":"1–2 Sätze",
"scores":{"ecommerce_fit":{"score":0,"grund":""},"niceshops_fit":{"score":0,"grund":""}},"quellen":["https://..."]}]}
```

Die Nachfrage bewertet das Modell bewusst **nicht**, sie kommt aus Schritt 4.

---

## Schritt 5b — Trend-Einschätzung · `analyze.py: assess_trends()` · KI mit Websuche

**Ein Aufruf** für die 15 Wirkstoffe.

**User-Nachricht (wörtlich):**

```
Shop: Vitalabo (...). <Positionierung>

Wirkstoffe/Konzepte aus den aktuellen Amazon.de- und iHerb-Bestseller- und Neuheitenlisten:
- Lithium: 2 Produkte (0 Neuerscheinungen), No-Name-Anteil 0 %, im Shop bereits 0 Produkte (Lücke)
- Lymphdrainage: 6 Produkte (6 Neuerscheinungen), No-Name-Anteil 33 %, im Shop bereits 5 Produkte (dünn)
- ...

Schätze je Eintrag per Websuche ein: echter Trend mit wachsender Nachfrage oder kurzfristiger Hype (z. B. Social Media)?
Gibt es regulatorische Risiken in der EU (Novel Food, Health Claims, Höchstmengen)? Passt es zum Shop?
Berücksichtige, wie viele Produkte der Shop dazu schon führt (Lücke = 0, dünn = 1–9, abgedeckt = ab 10), und wähle die Empfehlung so:
neu aufnehmen (Lücke, echter Trend, regulatorisch unkritisch) · ausbauen (dünn besetzt, Nachfrage wächst) ·
bereits abgedeckt (Shop gut sortiert) · beobachten (unklar) · ignorieren (Hype oder regulatorisch riskant).
JSON: {"trends":[{"term":"","einschaetzung":"Trend|Hype|etabliert","begruendung":"1–2 Sätze",
"regulatorik":"kurz oder \"–\"","empfehlung":"neu aufnehmen|ausbauen|bereits abgedeckt|beobachten|ignorieren","quellen":["https://..."]}]}
```

## Schritt 5c — Interesse-Verlauf · `trends.py` · Code

Für jeden der 15 Wirkstoffe: passenden Wikipedia-Artikel suchen (Deutsch und Englisch), monatliche Seitenaufrufe der letzten 24 Monate abrufen und addieren.
- **Wachstum** = letzte 3 Monate gegenüber denselben 3 Monaten im Vorjahr (saisonbereinigt)
- **Momentum** = letzte 3 Monate gegenüber den 3 Monaten davor

Kostenlos, kein Schlüssel. Im Bericht als Verlaufskurve. Ist Wikipedia aus der Laufumgebung nicht erreichbar, blendet der Bericht die Spalte aus.

---

## Schritt 6 — Priorisieren und berichten · `analyze.py: prioritize_brands()`, `report.py`

```
Nachfrage (1–5)  = 1 + round(4 × Signalstärke / stärkste Signalstärke unter den Lücken)     gemessen
E-Commerce-Fit   = Score aus 5a (fehlt er: 3)
niceshops-Fit    = Score aus 5a (fehlt er: 3)
Priorität (0–100) = (0,5 × Nachfrage + 0,25 × E-Commerce-Fit + 0,25 × niceshops-Fit − 1) / 4 × 100
```

Die Gewichte stehen in `config/vitalabo.toml` unter `[scoring]`.

**Ausgabe:**
- `output/vitalabo/results.json`: `meta`, `summary`, `brand_gaps` (mit Fit, Belegen, Quellen), `brands_carried` (Gegenprobe), `trends` (mit Einschätzung und Verlauf)
- `output/vitalabo/report.html`: eine eigenständige Seite mit den Reitern Marken-Lücken, Trends, Bereits geführt, So funktioniert's, Annahmen & Fragen
- Kopie beider Dateien unter `output/vitalabo/runs/<Datum>/` als Verlauf

---

## Wie die Werte entstehen

Drei Werte bestimmen die Priorität einer Marken-Lücke. Einer davon wird aus beobachteten Rängen berechnet, zwei sind Einschätzungen der KI. Die Verrechnung passiert immer im Code.

### Nachfrageindikator (1–5): aus beobachteten Rängen, reiner Code

1. **Pro Produkt Signalpunkte:** Rang relativ zur Listenlänge, gewichtet nach Liste, mal Anteil der Tage, an denen das Produkt in der Liste stand.

   ```
   Punkte = Gewicht × (Listenlänge + 1 − Rang) / Listenlänge × Tage in der Liste / Tage im Fenster
   Gewicht:     Bestseller 1,0 · iHerb-Top-Seller 1,0 · Neuerscheinung 0,8
   Listenlänge: Amazon 100 · iHerb 10
   ```

2. **Pro Marke:** Summe der Punkte aller Produkte der Marke, das ist die **Signalstärke**.
3. **Skala 1 bis 5:**

   ```
   Nachfrage = 1 + round(4 × Signalstärke der Marke / stärkste Signalstärke unter den Lücken der Woche)
   ```

Die Skala ist **relativ**: Die stärkste Lücke der Woche bekommt immer eine 5, die anderen werden daran gemessen. Das macht Wochen untereinander nicht direkt vergleichbar; eine absolute Skala (z. B. über Keepa-Kaufzähler) ist ein nächster Schritt.

### E-Commerce-Fit und niceshops-Fit (1–5): Einschätzung der KI nach fester Rubrik

Diese beiden Werte werden **nicht berechnet**. Das Recherche-Modell vergibt sie mit Websuche nach der Rubrik, die wörtlich im Prompt steht (Schritt 5a):

- **E-Commerce-Fit:** versandfähig, nicht apotheken- oder verschreibungspflichtig, Wiederkauf bzw. Abo-Eignung, Warenkorbwert, lagerfähig, wenig Beratungs- und Retourenaufwand
- **niceshops-Fit:** Premium oder Nische statt Massenmarkt, ergänzt statt kannibalisiert, über Hersteller oder Distributor beziehbar (reine Direktvertriebs- oder Amazon-Marken werden abgewertet), passt zur Zielgruppe

Zu jedem Score liefert das Modell eine Begründung, eine Einschätzung der Beziehbarkeit (ja / unklar / eher nein) und Quellen. Fehlt eine Bewertung, setzt der Code den Wert 3 ein und markiert die Marke im Bericht als „Fit nicht bewertet“.

### Priorität (0–100): Code

```
Priorität = (0,5 × Nachfrage + 0,25 × E-Commerce-Fit + 0,25 × niceshops-Fit − 1) / 4 × 100
```

Der Nachfrageindikator zählt doppelt als bewusst gewählte Prototyp-Annahme. Dass diese Gewichtung das Umsatzpotenzial am besten vorhersagt, ist nicht belegt. Die Gewichte stehen in `config/vitalabo.toml` unter `[scoring]` und lassen sich ohne Codeänderung anpassen.

### Nachgerechnet am finalen Sonnet-Lauf vom 30.09.2026

| Marke | Nachfrageindikator | E-Commerce-Fit | niceshops-Fit | Rechnung | Priorität |
|---|---|---|---|---|---|
| natural elements | 5 | 4 | 2 | (0,5 × 5 + 0,25 × 4 + 0,25 × 2 − 1) / 4 × 100 | **75** |
| SUNDAY NATURAL | 4 | 5 | 2 | (0,5 × 4 + 0,25 × 5 + 0,25 × 2 − 1) / 4 × 100 | **69** |

Das Ranking priorisiert Prüfungskandidaten. Hohe Listenpräsenz beweist weder Beziehbarkeit noch wirtschaftlichen Nutzen für Vitalabo.

### Stärken und Grenzen dieser Bewertung

- **Stärke:** Die Listenpräsenz ist beobachtet und die Berechnung nachvollziehbar. Die Gewichtung liegt im Code und ist konfigurierbar. Die KI liefert nur Einzelurteile, jeweils mit Begründung und Quellen.
- **Grenze:** Die Fit-Scores bleiben KI-Urteile und können danebenliegen, besonders bei der Beziehbarkeit. Sie sind ein Hinweis zur Prüfung, keine Entscheidung.
- **Nächster Schritt:** Die Fit-Werte in prüfbare Einzelkriterien zerlegen (Apothekenpflicht ja/nein, Abo-fähig ja/nein, Händlervertrieb ja/nein, Preis über einer Schwelle) und über das Feedback des Einkaufs (gelistet / abgelehnt / beobachten) kalibrieren.

---

## Dateien

| Datei | Zeilen | Aufgabe |
|---|---|---|
| `run_scout.py` | 121 | Einstieg; `--step collect` (täglich) oder `--step weekly` (wöchentlich); ruft die Schritte 1–6 der Reihe nach auf |
| `config/vitalabo.toml` | – | Shop-Beschreibung, Amazon-Kategorie, Quellen, Fenster, Modelle, Gewichte, Warengruppen |
| `scout/signals.py` | 115 | Tagesdateien laden und vereinheitlichen; Amazon-Sammler über Apify |
| `scout/catalog.py` | 69 | Vitalabo-Export und Markenliste; Markenabgleich; Wirkstoff-Abdeckung |
| `scout/analyze.py` | 267 | Normalisieren (KI), Verdichten, Fit und Trends (KI + Websuche), Priorisierung |
| `scout/trends.py` | 87 | Wikipedia-Aufrufe je Wirkstoff, Wachstum und Momentum |
| `scout/llm.py` | 151 | OpenRouter-Client: Modellwahl, Websuche, Wiederholung bei Fehlern, Cache, Kostenzählung, JSON-Reparatur |
| `scout/report.py`, `report.css` | 261 | HTML-Bericht aus `results.json` |
| `automation/scout.yml.example` | – | Nicht aktiver Zeitplan-Entwurf; Betrieb und sichere Veröffentlichung noch einzurichten |
| `publish_report.py` | – | Öffentlicher Export ohne private CSV-Produkttitel-Beispiele |

## Aufwand je Wochenlauf

| Schritt | Aufrufe | Modell |
|---|---|---|
| 3 Normalisieren | 4 (je 60 Titel), danach nur neue Produkte | Sonnet 5.5 |
| 5a Fit | 1 | Sonnet 5.5 + Websuche |
| 5b Trends | 1 | Sonnet 5.5 + Websuche |
| 5c Wikipedia | 15–30 HTTP-Abrufe | kein LLM |

Die finale Nachberechnung von Fit und Trends kostete laut OpenRouter-Antworten **1,013844 USD** (2 neue Aufrufe, 160 Sekunden). Die bereits mit Sonnet berechnete Normalisierung wurde dabei wiederverwendet. Frühere Läufe und die Apify-Sammlung sind darin nicht enthalten; das ist keine Gesamtbudget-Abrechnung. Kosten variieren mit neuen Titeln, Websuche, Modell und Wiederholungen. Ein täglicher Sammler würde zusätzlich Apify-Kosten verursachen.
