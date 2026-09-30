# Finaler Review – 30.09.2026

## Ergebnis und geprüfte Kriterien

- Alle 209 eindeutigen externen Produkte wurden bereits in einem vorherigen Lauf mit `anthropic/claude-sonnet-5.5` normalisiert; 202 sind relevant. Die finale Nachberechnung verwendete diese Sonnet-Normalisierung.
- 12/12 Marken haben beide Fit-Scores im Bereich 1–5; kein Fit musste durch die Standardbewertung ersetzt werden. 15/15 Konzepte haben eine Empfehlung. Vollständigkeit ist kein Nachweis fachlicher Richtigkeit.
- Keine identischen Trendnamen; Kreatin und Kreatin Monohydrat sind zu einem Eintrag „Kreatin“ zusammengefasst.
- Kollagen: 96 Titel-Treffer, `abgedeckt`, Empfehlung `bereits abgedeckt`.
- Lymphdrainage: 5 Titel-Treffer, `dünn`, Empfehlung `beobachten`.
- Lithium: 0 Treffer, `Lücke`, Empfehlung `ignorieren`. TUDCA: 0 Treffer, Empfehlung `beobachten`. Keine automatische Listungsentscheidung.
- Letzte Nachberechnung: 2 OpenRouter-Aufrufe, 160 Sekunden, 1,013844 USD. Frühere Aufrufe und Apify sind nicht mitgerechnet.

## Top-5-Marken im finalen Prioritätsranking

| Marke | Priorität | Beziehbarkeit laut KI |
|---|---:|---|
| natural elements | 75 | unklar |
| SUNDAY NATURAL | 69 | eher nein |
| Life Extension | 50 | ja |
| Naturtreu | 44 | unklar |
| Swanson Vitamins | 31 | ja |

„Marken-Lücke“ bedeutet: im gelieferten Export und der verwendeten öffentlichen Markenliste kein Treffer. Das ist eine prüfbare Kandidatenliste, keine Garantie, dass der gesamte aktuelle Shop diese Marke nicht führt. Hohe Priorität hebt die Einschränkung „unklar“ oder „eher nein“ bei Beziehbarkeit nicht auf.

## Top-5-Konzepte in der heuristischen Signalreihenfolge

| Konzept | Titel-Treffer | Empfehlung |
|---|---:|---|
| Magnesium | 133 | bereits abgedeckt |
| Grünpulver | 39 | bereits abgedeckt |
| Vitamin D3 | 127 | bereits abgedeckt |
| Omega-3 | 85 | bereits abgedeckt |
| Kreatin | 30 | bereits abgedeckt |

Die Reihenfolge ist kein Ranking des gemessenen Marktwachstums. Diese fünf Konzepte sind im Titelabgleich bereits abgedeckt; die interessante Aufgabe ist deren Einordnung, nicht automatisch neue Produkte aufzunehmen.

## Aussagegrenzen und nächste Schritte

1. **Ein Tagesstand:** Amazon 200 und iHerb 10 Einträge vom 30.09.2026. Es gibt noch keine sieben Tage Beständigkeit und kein nachgewiesenes Nachfragewachstum. Kundenbedürfnisse werden aus externen Signalen vermutet; interne Suchen ohne Treffer, Warenkorbabbrüche und Kundenanfragen wären direkte Ergänzungen.
2. **Ränge statt Verkäufe:** Bestseller und Neuerscheinungen sind unterschiedliche Signale. Neuheiten und kumulierte Bewertungen beweisen keinen aktuellen Absatz. Markt, Land, Kategorie und Beobachtungszeitpunkt müssen über Läufe konstant gehalten werden.
3. **Titel statt Inhaltsstoffe:** Eine Suche ohne Treffer beweist keine Abwesenheit eines Wirkstoffs. Zudem schlägt die KI teilweise zu breite Begriffe vor: Die Kollagen-Suche enthält auch „biotin“ und „hyaluron“. Die 96 Treffer sind daher kein exakter Kollagen-Produktbestand. Für die Abdeckung sind kuratierte Suchbegriffe und die Produktdatenbank mit Inhaltsstoffen nötig. Diese Logik wurde im Abschlussreview nicht verändert.
4. **Webbelege:** Alle 12 Markenbewertungen haben Quellenlisten, aber nur 9 von 15 Trendbewertungen. Das Modell erklärt teilweise ausdrücklich, keine eigene Websuche gemacht zu haben. Quellenlisten sind keine geprüften Beweise. Beziehbarkeit und regulatorische Aussagen vor einer Entscheidung anhand aktueller Primärquellen bestätigen. Im Text können rohe `<cite ...>`-Markierungen des Modells vorkommen.
5. **Kein Interesseverlauf:** Wikipedia war aktiviert, lieferte aber 0/15 Reihen; es gibt daraus kein unabhängiges Wachstumssignal. Wikipedia wäre ohnehin ein Aufmerksamkeitsindikator, kein Absatznachweis.
6. **Annahmen:** Gewichtung 50 % Nachfrageindikator, 25 % E-Commerce-Fit, 25 % niceshops-Fit sowie Grenzen 0/1–9/10+ sind bewusst gesetzte Heuristiken. Mit Feedback des Einkaufs kalibrieren. Der Nachfrage-Score ist relativ zur stärksten Marke dieses Laufs, daher nicht direkt zwischen Wochen vergleichbar.
7. **Betrieb noch offen:** Kein aktiver Zeitplan, keine GitHub Actions, kein automatischer iHerb-Abruf. Der Entwurf unter `automation/` benötigt sichere Exportbereitstellung, persistente Tageshistorie, Fehleralarme, Kostenbegrenzung und bereinigte Veröffentlichung. OpenRouter ist der Modellzugang, nicht der Scheduler.

## Technischer Abschluss

Beim vorangegangenen Lauf war die Antwortgrenze für die beiden Recherche-Aufrufe zu klein: Die JSON-Antworten wurden abgeschnitten. Sie wurde auf 16.000 Ausgabetokens pro Aufruf erhöht und nur Fit/Trends wurden nachberechnet. Ranking, Gewichtung, Matching und Empfehlungen wurden nicht manuell überschrieben. Kleine vorhandene Schutzmaßnahmen markieren fehlende Fit-Scores und behandeln leere Score-Objekte.

Die Roh-Ausgaben enthalten private CSV-Produktbeispiele. Sie bleiben lokal. `publish_report.py` entfernt `vitalabo_examples` rekursiv und erzeugt die öffentlichen Dateien. Das öffentliche Repo enthält Code, öffentliche Markenliste, bereinigten Bericht und synthetische Demo; weder API-Key noch vertraulichen Export oder LLM-Cache.

Die Demo läuft ohne Netzwerk und ohne Schlüssel mit Python 3.11+. Der synthetische Stichtag 2000-01-01 trennt Testdaten von echten Tagesständen.
