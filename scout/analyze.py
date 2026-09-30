"""Wöchentliche Auswertung: Signale normalisieren, verdichten, mit dem Bestand abgleichen, priorisieren."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

LIST_WEIGHT = {"bestsellers": 1.0, "topsellers": 1.0, "new-releases": 0.8}
LIST_SIZE = {"bestsellers": 100, "new-releases": 100, "topsellers": 10}

# ------------------------------------------------------------------ 1. Normalisieren (LLM)

NORM_SYSTEM = (
    "Du normalisierst Produkttitel von Amazon und iHerb für einen Händler von Nahrungsergänzungsmitteln. "
    "Pro Titel: (1) brand = der echte Markenname in seiner Originalschreibweise – Amazon übersetzt Marken teils "
    "(\"Double Heart\" = \"Doppelherz\"); ist keine Marke erkennbar (No-Name/Generika), dann \"\". "
    "(2) wirkstoff = zentraler Wirkstoff bzw. Produktkonzept als kurzer deutscher Begriff, wie ein Wikipedia-Artikel "
    "(z. B. \"Magnesium\", \"Kollagen\", \"Lymphdrainage\", \"Berberin\", \"TUDCA\"). "
    "(3) begriffe = 2–4 Suchbegriffe (deutsch/englisch, Kleinschreibung), mit denen man denselben Wirkstoff in "
    "Produktnamen findet. (4) code = Warengruppe aus der Liste. (5) relevant = false für Nicht-Supplements "
    "(Pflaster, Kosmetik, Geräte, Lebensmittel ohne Ergänzungszweck). "
    "Antworte nur mit JSON {\"<id>\": {\"brand\":\"\",\"wirkstoff\":\"\",\"begriffe\":[],\"code\":\"\",\"relevant\":true}}."
)


_KNOWN = ["Magnesium", "Kollagen:collagen", "Kreatin:creatin", "Omega-3:omega", "Vitamin D3", "Vitamin B12", "Vitamin C",
          "Zink:zinc", "Eisen:iron", "Ashwagandha", "Lymphdrainage:lymph", "Berberin:berberin", "Melatonin", "Lithium",
          "Inositol", "Probiotika:bacteria", "Mariendistel:milk thistle", "Flohsamen:psyllium", "Q10", "Oregano"]


def _heuristic(name: str, brand_hint: str = "") -> dict:
    """Fallback ohne LLM (--no-llm): erstes großgeschriebenes Wort als Marke, Wirkstoff per Stichwortliste. Bewusst grob."""
    w = re.split(r"[\s,|®™–-]+", name.strip())
    brand = brand_hint or (w[0] if w and w[0][:1].isupper() and w[0].lower() not in
                           {"vitamin", "magnesium", "collagen", "creatine", "omega", "zinc", "iron", "pack"} else "")
    low, wirk, terms = name.lower(), "", []
    for k in _KNOWN:
        label, _, key = k.partition(":")
        key = key or label.lower()
        if key in low:
            wirk, terms = label, [key]
            break
    return {"brand": brand, "wirkstoff": wirk, "begriffe": terms, "code": "SONST", "relevant": True}


def normalize(items: list[dict], cfg: dict, llm, cache_path: Path, log=print) -> dict:
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    uniq = {i["id"]: i["name"] for i in items}
    hints = {i["id"]: i.get("brand_hint") or "" for i in items}
    todo = [k for k in uniq if k not in cache]
    log(f"  {len(uniq)} Produkte, davon {len(todo)} neu zu normalisieren")
    if llm is None:
        for k in todo:
            cache[k] = _heuristic(uniq[k], hints[k])
    else:
        tax = "\n".join(f"{t['code']} – {t['name']}" for t in cfg["taxonomy"])
        codes = {t["code"] for t in cfg["taxonomy"]}
        for s in range(0, len(todo), 60):
            batch = todo[s : s + 60]
            lines = "\n".join(f"{j}|{uniq[k][:220]}" for j, k in enumerate(batch))
            try:
                data, _ = llm.chat_json("classify", NORM_SYSTEM, f"Warengruppen:\n{tax}\n\nTitel (id|Titel):\n{lines}",
                                        max_tokens=7000, temperature=0)
            except Exception as e:
                log(f"  Normalisierung fehlgeschlagen ({e}) – Heuristik für diesen Block")
                data = {}
            for j, k in enumerate(batch):
                d = data.get(str(j)) or _heuristic(uniq[k], hints[k])
                d["code"] = d.get("code") if d.get("code") in codes else "SONST"
                cache[k] = d
            log(f"  normalisiert: {min(s + 60, len(todo))}/{len(todo)}")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return cache


# ------------------------------------------------------------------ 2. Verdichten

def aggregate(items: list[dict], norm: dict, meta: dict, cfg: dict, catalog) -> dict:
    days_total = max(len(m["dates"]) for m in meta.values()) or 1
    names = {t["code"]: t["name"] for t in cfg["taxonomy"]}

    # pro Produkt über die Tage
    prod = {}
    for it in items:
        p = prod.setdefault(it["id"], {**{k: it[k] for k in ("source", "name", "url", "id")},
                                       "lists": set(), "days": set(), "best": {}, "reviews": it["reviews"],
                                       "rating": it["rating"], "price": it["price"]})
        p["lists"].add(it["list"])
        p["days"].add(it["date"])
        p["best"][it["list"]] = min(p["best"].get(it["list"], 999), it["rank"])
        if it["reviews"] is not None:
            p["reviews"] = it["reviews"]

    for p in prod.values():
        n = norm.get(p["id"], {})
        p.update(brand=n.get("brand", ""), wirkstoff=n.get("wirkstoff", ""), begriffe=n.get("begriffe", []),
                 code=n.get("code", "SONST"), relevant=n.get("relevant", True))
        # Signalpunkte: Rang relativ zur Listenlänge, gewichtet nach Liste, mal Beständigkeit
        p["points"] = round(sum(LIST_WEIGHT.get(l, 1) * (LIST_SIZE.get(l, 100) + 1 - r) / LIST_SIZE.get(l, 100)
                                for l, r in p["best"].items()) * len(p["days"]) / days_total, 3)
        p["lists"], p["days_present"] = sorted(p["lists"]), len(p["days"])
        del p["days"]

    relevant = [p for p in prod.values() if p["relevant"]]

    # pro Marke
    brands = {}
    for p in relevant:
        if not p["brand"]:
            continue
        g = brands.setdefault(p["brand"].lower(), {"brand": p["brand"], "products": [], "signal": 0.0,
                                                   "sources": set(), "lists": set(), "reviews": 0, "codes": defaultdict(int)})
        g["products"].append(p)
        g["signal"] += p["points"]
        g["sources"].add(p["source"])
        g["lists"].update(p["lists"])
        g["reviews"] += int(p["reviews"] or 0)
        g["codes"][p["code"]] += 1
    brand_rows = []
    for g in brands.values():
        g["products"].sort(key=lambda x: -x["points"])
        code = max(g["codes"], key=g["codes"].get)
        carried = catalog.match_brand(g["brand"])
        brand_rows.append({
            "brand": g["brand"], "signal": round(g["signal"], 2), "n_products": len(g["products"]),
            "n_new": sum("new-releases" in p["lists"] for p in g["products"]),
            "sources": sorted(g["sources"]), "lists": sorted(g["lists"]), "reviews": g["reviews"],
            "best_rank": min(min(p["best"].values()) for p in g["products"]),
            "category": names.get(code, code), "carried_as": carried,
            "products": [_slim(p) for p in g["products"][:5]],
        })
    brand_rows.sort(key=lambda x: -x["signal"])

    # pro Wirkstoff / Konzept – Varianten zusammenführen ("Kreatin Monohydrat" -> "Kreatin")
    canon = _canonical_terms({(p["wirkstoff"] or "").strip() for p in relevant if (p["wirkstoff"] or "").strip()})
    ingr = {}
    for p in relevant:
        w = canon.get((p["wirkstoff"] or "").strip())
        if not w:
            continue
        e = ingr.setdefault(w.lower(), {"term": w, "products": [], "begriffe": set([w.lower()]), "sources": set()})
        e["products"].append(p)
        e["begriffe"].update(b.lower() for b in p["begriffe"])
        e["sources"].add(p["source"])
    trend_rows = []
    for e in ingr.values():
        n_new = sum("new-releases" in p["lists"] for p in e["products"])
        hits, examples = catalog.coverage(sorted(e["begriffe"]))
        trend_rows.append({
            "term": e["term"], "n_products": len(e["products"]), "n_new": n_new,
            "n_bestseller": sum(any(l in ("bestsellers", "topsellers") for l in p["lists"]) for p in e["products"]),
            "sources": sorted(e["sources"]), "begriffe": sorted(e["begriffe"])[:6],
            "no_name_share": round(sum(not p["brand"] for p in e["products"]) / len(e["products"]), 2),
            "vitalabo_hits": hits, "vitalabo_examples": examples,
            "coverage": "Lücke" if hits == 0 else "dünn" if hits <= 9 else "abgedeckt",
            "products": [_slim(p) for p in sorted(e["products"], key=lambda x: -x["points"])[:4]],
        })
    # Frühsignal vor Volumen: Neuerscheinungen doppelt, Lücken im Sortiment bevorzugt
    bonus = {"Lücke": 3, "dünn": 1, "abgedeckt": 0}
    trend_rows.sort(key=lambda x: -(x["n_new"] * 2 + x["n_products"] + bonus[x["coverage"]] + 2 * ("iherb" in x["sources"])))

    carried = [b for b in brand_rows if b["carried_as"]]
    return {
        "days": days_total, "n_products": len(prod), "n_relevant": len(relevant),
        "brands": brand_rows, "trends": trend_rows,
        "share_signal_carried": round(sum(b["signal"] for b in carried) / (sum(b["signal"] for b in brand_rows) or 1) * 100),
        "n_brands": len(brand_rows), "n_brands_carried": len(carried),
    }


_GENERIC = {"vitamin", "vitamine", "mineral", "mineralstoffe", "komplex", "extrakt", "öl", "pulver"}


def _canonical_terms(terms: set[str]) -> dict:
    """Ordnet Varianten dem kürzesten gemeinsamen Begriff zu: "Magnesium Komplex" -> "Magnesium",
    "Kreatin Monohydrat" -> "Kreatin", "Lithiumorotat" -> "Lithium" (falls beide vorkommen)."""
    by_len = sorted(terms, key=len)
    out = {}
    for t in by_len:
        tl = t.lower()
        base = next((b for b in by_len if len(b) < len(t) and b.lower() not in _GENERIC and len(b) >= 5
                     and (tl.startswith(b.lower() + " ") or tl.startswith(b.lower() + "-")
                          or (len(b) >= 6 and tl.startswith(b.lower())))), None)
        out[t] = out.get(base, base) if base else t
    return out


def _slim(p):
    return {k: p[k] for k in ("source", "name", "url", "best", "days_present", "reviews", "rating", "price", "lists")}


# ------------------------------------------------------------------ 3. Fit bewerten (LLM mit Websuche)

FIT_SYSTEM = (
    "Du bist Category Manager:in eines Onlinehändlers für Nahrungsergänzung im DACH-Raum. Du recherchierst im Web, "
    "stützt Aussagen auf Belege und bist ehrlich, wenn Belege fehlen. Antworte ausschließlich mit JSON."
)
RUBRIC = """Bewerte von 1 (schwach) bis 5 (sehr stark):
- ecommerce_fit: versandfähig, nicht apotheken-/verschreibungspflichtig, Wiederkauf bzw. Abo-Eignung, Warenkorbwert, lagerfähig, wenig Beratungs-/Retourenaufwand
- niceshops_fit: Premium/Nische statt Massenmarkt, ergänzt statt kannibalisiert, Bezug über Hersteller/Distributor realistisch (reine Direktvertriebs- oder Amazon-only-Marken abwerten), passt zur Zielgruppe"""


def _shop(cfg):
    s = cfg["shop"]
    return f"Shop: {s['name']} ({s['url']}). {s['positioning'].strip()}"


def assess_brands(gaps: list[dict], cfg: dict, llm, log=print) -> None:
    if llm is None or not gaps:
        return
    lines = "\n".join(f"- {b['brand']} ({b['category']}): {b['n_products']} Produkte in den Listen, "
                      f"bester Rang {b['best_rank']}, {b['reviews']} Bewertungen; z. B. {b['products'][0]['name'][:110]}"
                      for b in gaps)
    user = f"""{_shop(cfg)}

Diese Marken verkaufen sich auf Amazon.de bzw. iHerb nachweislich gut (Bestseller-/Neuheitenlisten), der Shop führt sie nicht:
{lines}

Die Nachfrage ist gemessen. Recherchiere je Marke kurz: Hersteller/Herkunft, Positionierung, Vertriebsweg
(eigener Shop, Amazon, Apotheke, Händler?) und ob ein Bezug durch einen Onlinehändler realistisch ist.
{RUBRIC}

JSON: {{"brands":[{{"brand":"","herkunft":"","beschreibung":"1 Satz","vertrieb":"z. B. D2C + Amazon, auch Händler",
"beziehbar":"ja|unklar|eher nein","begruendung":"1–2 Sätze",
"scores":{{"ecommerce_fit":{{"score":0,"grund":""}},"niceshops_fit":{{"score":0,"grund":""}}}},"quellen":["https://..."]}}]}}"""
    try:
        data, raw = llm.chat_json("research", FIT_SYSTEM, user, web=True, web_results=10, max_tokens=16000)
    except Exception as e:
        log(f"  Fit-Bewertung fehlgeschlagen: {e}")
        return
    by = {x.get("brand", "").lower(): x for x in data.get("brands", [])}
    for b in gaps:
        x = by.get(b["brand"].lower())
        if x:
            b["fit"] = x
            b["fit"]["quellen"] = (x.get("quellen") or [])[:4] or [s["url"] for s in raw["sources"][:3]]
    log(f"  Fit bewertet: {sum('fit' in b for b in gaps)}/{len(gaps)} Marken")


def assess_trends(trends: list[dict], cfg: dict, llm, log=print) -> None:
    if llm is None or not trends:
        return
    lines = "\n".join(f"- {t['term']}: {t['n_products']} Produkte ({t['n_new']} Neuerscheinungen), No-Name-Anteil "
                      f"{int(t['no_name_share'] * 100)} %, im Shop bereits {t['vitalabo_hits']} Produkte ({t['coverage']})"
                      for t in trends)
    user = f"""{_shop(cfg)}

Wirkstoffe/Konzepte aus den aktuellen Amazon.de- und iHerb-Bestseller- und Neuheitenlisten:
{lines}

Schätze je Eintrag per Websuche ein: echter Trend mit wachsender Nachfrage oder kurzfristiger Hype (z. B. Social Media)?
Gibt es regulatorische Risiken in der EU (Novel Food, Health Claims, Höchstmengen)? Passt es zum Shop?
Berücksichtige, wie viele Produkte der Shop dazu schon führt (Lücke = 0, dünn = 1–9, abgedeckt = ab 10), und wähle die Empfehlung so:
neu aufnehmen (Lücke, echter Trend, regulatorisch unkritisch) · ausbauen (dünn besetzt, Nachfrage wächst) ·
bereits abgedeckt (Shop gut sortiert) · beobachten (unklar) · ignorieren (Hype oder regulatorisch riskant).
JSON: {{"trends":[{{"term":"","einschaetzung":"Trend|Hype|etabliert","begruendung":"1–2 Sätze",
"regulatorik":"kurz oder \\"–\\"","empfehlung":"neu aufnehmen|ausbauen|bereits abgedeckt|beobachten|ignorieren","quellen":["https://..."]}}]}}"""
    try:
        data, raw = llm.chat_json("research", FIT_SYSTEM, user, web=True, web_results=10, max_tokens=16000)
    except Exception as e:
        log(f"  Trend-Einschätzung fehlgeschlagen: {e}")
        return
    by = {x.get("term", "").lower(): x for x in data.get("trends", [])}
    for t in trends:
        x = by.get(t["term"].lower())
        if x:
            t["assessment"] = x
    log(f"  Trends eingeschätzt: {sum('assessment' in t for t in trends)}/{len(trends)}")


# ------------------------------------------------------------------ 4. Priorisieren

def prioritize_brands(gaps: list[dict], cfg: dict) -> None:
    w = cfg["scoring"]
    top = max((b["signal"] for b in gaps), default=1) or 1
    for b in gaps:
        d = 1 + round(4 * b["signal"] / top)                         # gemessen, relativ zur stärksten Lücke
        sc = (b.get("fit") or {}).get("scores") or {}
        e = int((sc.get("ecommerce_fit") or {}).get("score") or 3)
        n = int((sc.get("niceshops_fit") or {}).get("score") or 3)
        b["score_demand"], b["score_ecommerce"], b["score_niceshops"] = d, max(1, min(5, e)), max(1, min(5, n))
        b["priority"] = round((w["demand"] * d + w["ecommerce_fit"] * b["score_ecommerce"]
                               + w["niceshops_fit"] * b["score_niceshops"] - 1) / 4 * 100)
        b["fit_estimated"] = not bool(sc)
    gaps.sort(key=lambda x: -x["priority"])
    for i, b in enumerate(gaps, 1):
        b["rank"] = i
