"""Signale: täglich gesammelte Momentaufnahmen externer Bestsellerlisten.

Jede Quelle legt pro Tag eine Datei unter data/signals/<quelle>/<YYYY-MM-DD>.json ab.
- amazon: Apify-Scraper "junglee/amazon-bestsellers" (Rohformat des Scrapers, wird hier normalisiert)
- iherb:  Top-Seller-Liste; im Prototyp manuell erfasst (automatischer Abruf noch nicht nachgewiesen)

Einheitliches Format je Eintrag:
  {source, list, rank, name, url, id, reviews, rating, price, date}
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LIST_LABEL = {"new-releases": "Neuerscheinungen", "bestsellers": "Bestseller", "topsellers": "Top-Seller"}


def _num(v):
    if v is None:
        return None
    if isinstance(v, dict):
        v = v.get("value")
    if isinstance(v, (int, float)):
        return v
    m = re.search(r"[\d.,]+", str(v))
    if not m:
        return None
    s = m.group(0)
    s = s.replace(".", "").replace(",", ".") if "," in s else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _amazon_items(raw: list, date: str) -> list[dict]:
    out, seen = [], set()
    for r in raw:
        if not r.get("name"):
            continue  # Fehlerzeilen des Scrapers (z. B. ungültige Kategorie)
        lt = "new-releases" if "new-releases" in (r.get("input") or r.get("categoryUrl") or "") else "bestsellers"
        key = (lt, r.get("position"))
        if key in seen:
            continue  # der Scraper liefert Seiten teils doppelt
        seen.add(key)
        asin = r.get("asin") or (re.search(r"/dp/([A-Z0-9]{10})", r.get("url", "")) or [None, None])[1]
        out.append({"source": "amazon", "list": lt, "rank": int(r.get("position") or 999),
                    "name": " ".join(str(r["name"]).split()), "url": (r.get("url") or "").split("/ref=")[0],
                    "id": f"amazon:{asin}", "reviews": _num(r.get("reviewsCount")), "rating": _num(r.get("stars")),
                    "price": _num(r.get("price")), "date": date})
    return out


def _iherb_items(raw, date: str) -> list[dict]:
    items = raw.get("items", raw) if isinstance(raw, dict) else raw
    return [{"source": "iherb", "list": "topsellers", "rank": int(r.get("rank") or i + 1),
             "name": " ".join(str(r.get("name", "")).split()), "url": r.get("url", ""),
             "id": "iherb:" + str(r.get("name", ""))[:80], "reviews": _num(r.get("reviews")),
             "rating": _num(r.get("rating")), "price": _num(r.get("price")), "date": date, "brand_hint": r.get("brand")}
            for i, r in enumerate(items) if r.get("name")]


PARSERS = {"amazon": _amazon_items, "iherb": _iherb_items}


def load_window(root: Path, sources: list[str], end: dt.date, days: int, log=print) -> tuple[list[dict], dict]:
    start = end - dt.timedelta(days=days - 1)
    items, meta = [], {}
    for src in sources:
        dates = []
        for p in sorted((root / "data" / "signals" / src).glob("*.json")):
            try:
                d = dt.date.fromisoformat(p.stem)
            except ValueError:
                continue
            if start <= d <= end:
                got = PARSERS[src](json.loads(p.read_text(encoding="utf-8")), p.stem)
                items.extend(got)
                dates.append(p.stem)
        meta[src] = {"dates": dates, "items": sum(1 for i in items if i["source"] == src)}
        log(f"  {src}: {len(dates)} Tagesstände, {meta[src]['items']} Einträge")
    return items, meta


# ------------------------------------------------------------------ täglicher Sammler

def collect_amazon(cfg: dict, root: Path, log=print, date: str | None = None) -> Path | None:
    token = os.environ.get("APIFY_TOKEN", "")
    if not token:
        log("  APIFY_TOKEN fehlt – Amazon-Sammler übersprungen.")
        return None
    ac = cfg["signals"]["amazon"]
    urls = [f"https://www.amazon.de/gp/{lt}/{ac['category_path']}/" for lt in ac["lists"]]
    q = urllib.parse.urlencode({"token": token})
    url = f"https://api.apify.com/v2/acts/{ac['actor'].replace('/', '~')}/run-sync-get-dataset-items?{q}"
    body = json.dumps({"categoryUrls": urls, "maxItemsPerStartUrl": ac.get("max_items", 100), "depthOfCrawl": 1}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = json.load(r)
    except urllib.error.HTTPError as e:
        log(f"  Apify-Fehler HTTP {e.code}: {e.read().decode(errors='ignore')[:200]}")
        return None
    date = date or dt.date.today().isoformat()
    path = root / "data" / "signals" / "amazon" / f"{date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    log(f"  Amazon-Momentaufnahme gespeichert: {path.name} ({len(raw)} Einträge)")
    return path
