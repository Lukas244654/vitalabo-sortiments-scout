"""KI Sortiments Scout – Einstiegspunkt.

    python run_scout.py --step collect      # täglich: Signale sammeln (Amazon über Apify)
    python run_scout.py --step weekly       # wöchentlich: auswerten und Bericht erzeugen
    python run_scout.py --step weekly --no-llm   # Testlauf ohne OpenRouter (grobe Heuristik)

Ergebnis: output/<shop>/results.json und output/<shop>/report.html (+ Kopie unter runs/<datum>/)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        import toml as tomllib

from scout import analyze as A
from scout import signals as S
from scout import trends as T
from scout.catalog import Catalog, load_products, load_site_brands
from scout.llm import LLM, load_env
from scout.report import render

ROOT = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description="KI Sortiments Scout")
    ap.add_argument("--config", default="config/vitalabo.toml")
    ap.add_argument("--step", choices=["collect", "weekly", "all"], default="weekly")
    ap.add_argument("--no-llm", action="store_true", help="ohne OpenRouter (Heuristik, nur zum Testen)")
    ap.add_argument("--date", help="Stichtag (YYYY-MM-DD), Standard: heute")
    args = ap.parse_args()

    t0 = time.time()
    log = lambda m: print(m, flush=True)
    cfg = tomllib.loads((ROOT / args.config).read_text(encoding="utf-8"))
    load_env(ROOT / ".env")
    today = args.date or dt.date.today().isoformat()
    out = ROOT / "output" / cfg["shop"]["id"]

    if args.step in ("collect", "all"):
        log("Täglicher Sammler")
        if "amazon" in cfg["signals"]["sources"]:
            S.collect_amazon(cfg, ROOT, log, today)
        log("  iHerb: im Prototyp manuell erfasst (data/signals/iherb/)")
        if args.step == "collect":
            return

    log(f"Wöchentliche Auswertung {cfg['shop']['name']} – Stichtag {today}")
    llm = None if args.no_llm else LLM(cfg, out / "cache", log)
    if llm:
        log(f"  Modelle: {llm.models}")

    log("1/6 Signale der letzten Tage laden")
    items, meta = S.load_window(ROOT, cfg["signals"]["sources"], dt.date.fromisoformat(today),
                                cfg["signals"].get("window_days", 7), log)
    if not items:
        sys.exit("Keine Signale im Zeitfenster gefunden.")

    log("2/6 Vitalabo-Bestand laden")
    catalog = Catalog(load_products(cfg, ROOT), load_site_brands(cfg, ROOT))
    log(f"  {len(catalog.products)} Produkte im Export, {len(catalog.brands)} Marken (Export + Website)")

    log("3/6 Produkttitel normalisieren (Marke, Wirkstoff, Warengruppe)")
    norm = A.normalize(items, cfg, llm, out / "normalized.json", log)

    log("4/6 Verdichten und mit dem Bestand abgleichen")
    agg = A.aggregate(items, norm, meta, cfg, catalog)
    gaps = [b for b in agg["brands"] if not b["carried_as"]][: cfg["scan"]["top_brand_gaps"]]
    trends = agg["trends"][: cfg["scan"]["top_trends"]]
    log(f"  {agg['n_brands']} Marken, davon {agg['n_brands_carried']} bei Vitalabo; {len(agg['trends'])} Wirkstoffe/Konzepte")

    log("5/6 Fit und Trends einschätzen (LLM mit Websuche)")
    A.assess_brands(gaps, cfg, llm, log)
    A.assess_trends(trends, cfg, llm, log)
    if cfg["scan"].get("wikipedia_check"):
        measured = T.measure_many([(t["term"], None) for t in trends])
        for t in trends:
            t["interest"] = measured.get(t["term"])
        log(f"  Wikipedia-Verlauf gemessen: {len(measured)}/{len(trends)}")
    A.prioritize_brands(gaps, cfg)

    log("6/6 Bericht schreiben")
    results = {
        "meta": {"shop": cfg["shop"]["name"], "shop_url": cfg["shop"]["url"], "date": today,
                 "week": dt.date.fromisoformat(today).isocalendar().week,
                 "window_days": cfg["signals"].get("window_days", 7), "signals": meta,
                 "amazon_category": "Vitamine, Mineralien & Ergänzungsmittel (Amazon.de)",
                 "vitalabo_products": len(catalog.products), "vitalabo_brands": len(catalog.brands),
                 "models": llm.models if llm else None, "llm": bool(llm),
                 "stats": llm.stats if llm else None, "weights": cfg["scoring"],
                 "runtime_s": round(time.time() - t0)},
        "summary": {k: agg[k] for k in ("days", "n_products", "n_relevant", "n_brands", "n_brands_carried",
                                         "share_signal_carried")},
        "brand_gaps": gaps,
        "brands_carried": [b for b in agg["brands"] if b["carried_as"]][:15],
        "trends": trends,
    }
    out.mkdir(parents=True, exist_ok=True)
    run_dir = out / "runs" / today
    run_dir.mkdir(parents=True, exist_ok=True)
    for d in (out, run_dir):
        (d / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        (d / "report.html").write_text(render(results), encoding="utf-8")
    s = llm.stats if llm else {"calls": 0, "cached": 0, "cost_usd": 0}
    log(f"\nFertig in {round(time.time() - t0)} s. {s['calls']} API-Aufrufe ({s['cached']} aus Cache), "
        f"ca. {s['cost_usd']:.2f} USD.\nBericht: {out / 'report.html'}")


if __name__ == "__main__":
    main()
