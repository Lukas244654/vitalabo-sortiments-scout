# KI Sortiments Scout – Vitalabo

Praxisprototyp für die Bewerbung als KI Enabler bei niceshops. Externe Bestseller- und Neuerscheinungslisten liefern Kandidaten; eine Python-Pipeline gleicht Marken und Produktkonzepte mit dem Sortiment ab und erzeugt einen Bericht für den Einkauf.

**[Öffentlichen Bericht öffnen](https://vitalabo-sortiments-scout-lukas.cetarius.chatgpt.site)** · [Pipeline und Prompts](PIPELINE.md) · [Review und Grenzen](REVIEW.md)

## Was tatsächlich läuft

Der veröffentlichte Bericht basiert auf einer echten Momentaufnahme vom **30.09.2026**: 200 Amazon-Einträge über Apify und 10 manuell erfasste iHerb-Einträge. 209 eindeutige externe Produkte wurden mit **`anthropic/claude-sonnet-5.5` über OpenRouter** normalisiert. 202 davon sind relevant; 12 Marken und 15 Produktkonzepte wurden bewertet. Der lokale, vertrauliche Sortimentsabgleich umfasst 4.520 Produkte und 333 Marken aus Export und öffentlicher Markenliste.

Es liegt **ein Tagesstand** vor, noch keine gemessene Wochenentwicklung. Bestseller-Ränge sind Nachfrageindikatoren, keine Verkaufszahlen. KI-Urteile, Regelwerk und beobachtete Daten werden in [PIPELINE.md](PIPELINE.md) erklärt.

**Es läuft derzeit kein automatischer Zeitplan und kein GitHub Action.** Die Site zeigt den veröffentlichten Bericht, sie führt die Pipeline nicht aus. `automation/scout.yml.example` ist ein nicht aktiver Entwurf. Für den Betrieb fehlen die sichere Bereitstellung des Exports, die persistente Tageshistorie, ein automatischer iHerb-Abruf und der automatisierte Veröffentlichungsschritt.

## Lokal ausprobieren – ohne Schlüssel und ohne vertrauliche Daten

Python **3.11 oder neuer**, keine zusätzlichen Pakete nötig:

```bash
git clone https://github.com/Lukas244654/vitalabo-sortiments-scout.git
cd vitalabo-sortiments-scout
python run_scout.py --step weekly --config config/demo.toml --date 2000-01-01 --no-llm
```

Dann `output/demo/report.html` im Browser öffnen. Alle Demo-Produkte, Rankings, Bewertungen und URLs sind **frei erfundene Testdaten**, die keine Marktanalyse darstellen. Der Bericht kennzeichnet den Lauf ohne KI; seine Überschrift ist derzeit auf Vitalabo festgelegt.

## Echten Wochenlauf reproduzieren

1. Den vertraulichen Export ausschließlich lokal unter `data/vitalabo-produktdaten.csv` bereitstellen; der Export ist nicht Teil des Repos.
2. Reale Tagesdateien unter `data/signals/amazon/YYYY-MM-DD.json` bzw. `data/signals/iherb/YYYY-MM-DD.json` bereitstellen. Der öffentliche Demo-Datensatz ist dafür ungeeignet.
3. `OPENROUTER_API_KEY` als Umgebungsvariable setzen, alternativ eine lokale `.env` nach `.env.example`. Für den Amazon-Sammler zusätzlich `APIFY_TOKEN`.
4. Mit dem tatsächlich verwendeten Sonnet-Profil starten:

```bash
python run_scout.py --step weekly --config config/vitalabo-sonnet55.toml --date 2026-09-30
```

`config/vitalabo.toml` enthält die ursprünglichen Modell-Fallbacks; es war nicht das Profil des finalen Sonnet-Laufs. Normalisierungen werden produktweise zwischengespeichert. Für einen Modellwechsel müssen bestehende `normalized.json` und passende Caches bewusst getrennt werden; ein Konfigurationswechsel allein berechnet bekannte Produkte nicht neu.

Die ursprünglichen Ausgaben `output/vitalabo/results.json` und `report.html` enthalten Beispiele aus privaten CSV-Produkttiteln. **Diese Rohdateien bleiben lokal.** Für die öffentliche Ausgabe:

```bash
python publish_report.py --input output/vitalabo/results.json --output docs
```

Der Export entfernt `vitalabo_examples` rekursiv; Scores, Reihenfolge und Empfehlungen bleiben gleich. Vor einer Veröffentlichung weitere private Felder prüfen, falls das Datenmodell erweitert wurde. `docs/` enthält die bereinigte Momentaufnahme und die begleitenden Dokumente. Das Hosting erfolgt über Sites; GitHub Pages ist nicht eingerichtet.

## Code und Datenfluss

| Datei | Zweck |
|---|---|
| `run_scout.py` | Einstieg: `collect`, `weekly`, `all` |
| `scout/signals.py` | Apify-Sammlung, Einlesen täglicher Amazon-/iHerb-Dateien |
| `scout/catalog.py` | CSV und Markenliste, Markenabgleich, Titel-Treffer |
| `scout/analyze.py` | KI-Normalisierung, Aggregation, Fit-/Trendbewertung, Priorisierung |
| `scout/llm.py` | OpenRouter, Modellwahl, Wiederholungen, JSON-Reparatur, Cache, Kosten |
| `scout/trends.py` | Optionale Wikipedia-Seitenaufrufe; im finalen Lauf nicht verfügbar |
| `scout/report.py`, `report.css` | Eigenständiger HTML-Bericht |
| `publish_report.py` | Bereinigte öffentliche Ausgabe |
| `config/` | Shop, Modellprofile, Regeln und synthetische Demo |
| `automation/scout.yml.example` | Zeitplan-Entwurf, bewusst außerhalb aktiver Workflows |

Im Repo sind keine API-Schlüssel, kein vertraulicher Export, keine LLM-Caches und keine Rohdaten der echten Scraper-Läufe. `.gitignore` schützt diese Pfade. An OpenRouter gehen externe Kandidaten und abgeleitete Trefferzahlen, keine privaten CSV-Produkttitel. Der Einkauf prüft Beziehbarkeit, regulatorische Aussagen und fachliche Empfehlungen vor einer Sortimentsentscheidung.
