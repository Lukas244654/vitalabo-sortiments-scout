"""Trend-Radar: misst mit echten Zeitreihen, ob das Interesse an einem Wirkstoff oder Thema wächst.

Quelle: Wikipedia-Seitenaufrufe (Wikimedia REST API) – kostenlos, stabil, ohne Key, monatliche Werte,
Deutsch und Englisch. Ein Proxy für öffentliches Interesse; im Betrieb würde man Google-Trends- bzw.
Suchvolumendaten ergänzen (siehe Roadmap).

Kennzahlen je Begriff:
- growth_12m: letzte 3 Monate vs. dieselben 3 Monate im Vorjahr (saisonbereinigt)
- momentum:   letzte 3 Monate vs. die 3 Monate davor
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "Sortiments-Scout-Prototyp/0.1 (Bewerbungsprojekt; kontakt via niceshops)"}


def _get(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def resolve_title(term: str, lang: str) -> str | None:
    q = urllib.parse.urlencode({"action": "opensearch", "search": term, "limit": 1, "namespace": 0, "format": "json"})
    try:
        res = _get(f"https://{lang}.wikipedia.org/w/api.php?{q}")
        return res[1][0] if res and len(res) > 1 and res[1] else None
    except Exception:
        return None


def monthly_views(title: str, lang: str, months: int = 25) -> dict:
    today = dt.date.today()
    end = today.replace(day=1) - dt.timedelta(days=1)            # letzter vollständiger Monat
    start = (end.replace(day=1) - dt.timedelta(days=31 * (months - 1))).replace(day=1)
    art = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{lang}.wikipedia/all-access/user/"
           f"{art}/monthly/{start:%Y%m%d}00/{end:%Y%m%d}00")
    try:
        items = _get(url).get("items", [])
    except Exception:
        return {}
    return {it["timestamp"][:6]: it["views"] for it in items}


def measure(term: str, titles: dict | None = None) -> dict | None:
    """titles: optional {'de': 'Titel', 'en': 'Title'} (z. B. vom LLM vorgeschlagen)."""
    series, used = {}, {}
    for lang in ("de", "en"):
        t = (titles or {}).get(lang) or resolve_title(term, lang)
        if not t:
            continue
        v = monthly_views(t, lang)
        if not v:
            t2 = resolve_title(term, lang)       # LLM-Titel falsch? Suche als Fallback
            if t2 and t2 != t:
                t, v = t2, monthly_views(t2, lang)
        if v:
            used[lang] = t
            for m, n in v.items():
                series[m] = series.get(m, 0) + n
    months = sorted(series)
    if len(months) < 15:
        return None
    vals = [series[m] for m in months]
    last3, prev3, yago3 = sum(vals[-3:]), sum(vals[-6:-3]), sum(vals[-15:-12])
    growth = round((last3 / yago3 - 1) * 100) if yago3 else None
    momentum = round((last3 / prev3 - 1) * 100) if prev3 else None
    return {"term": term, "titles": used, "months": months[-24:], "values": vals[-24:],
            "growth_12m": growth, "momentum": momentum, "monthly_avg": round(last3 / 3)}


def measure_many(terms: list[tuple[str, dict | None]], workers: int = 6) -> dict:
    with ThreadPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(lambda t: measure(*t), terms))
    return {t[0]: r for t, r in zip(terms, res) if r}


def demand_from_growth(g: int | None) -> int | None:
    if g is None:
        return None
    return 5 if g >= 50 else 4 if g >= 20 else 3 if g >= 0 else 2 if g >= -20 else 1
