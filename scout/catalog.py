"""Vitalabo-Bestand: Produktexport + Markenliste der Website, Markenabgleich."""
from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

_LEGAL = {"gmbh", "ag", "inc", "ltd", "llc", "co", "kg", "aps", "sa", "srl", "bv", "germany"}


def norm_brand(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[®™©´'`’]", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(w for w in s.split() if w not in _LEGAL)


def load_products(cfg: dict, root: Path) -> list[dict]:
    ex = cfg["export"]
    with open(root / ex["path"], encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    header = rows[ex.get("skip_rows", 0)]
    idx = {h.strip(): i for i, h in enumerate(header)}
    i_ean, i_name, i_brand = idx[ex["col_ean"]], idx[ex["col_name"]], idx[ex["col_brand"]]
    seen, out = set(), []
    for r in rows[ex.get("skip_rows", 0) + 1 :]:
        if len(r) <= max(i_ean, i_name, i_brand) or not r[i_name].strip():
            continue
        key = r[i_ean].strip() or r[i_name].strip()
        if key in seen:
            continue
        seen.add(key)
        out.append({"ean": r[i_ean].strip(), "name": " ".join(r[i_name].split()), "brand": r[i_brand].strip()})
    return out


def load_site_brands(cfg: dict, root: Path) -> list[str]:
    p = cfg["shop"].get("brands_file")
    if not p or not (root / p).exists():
        return []
    return [l.strip() for l in (root / p).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]


class Catalog:
    """Was führt der Shop? Marken (Export + Website) und Produktnamen für Wirkstoff-Abdeckung."""

    def __init__(self, products: list[dict], site_brands: list[str]):
        self.products = products
        self.names = [p["name"].lower() for p in products]
        self.brands = sorted({p["brand"] for p in products if p["brand"]} | set(site_brands))
        self.norms = {norm_brand(b): b for b in self.brands if norm_brand(b)}

    def match_brand(self, brand: str) -> str | None:
        n = norm_brand(brand)
        if not n:
            return None
        if n in self.norms:
            return self.norms[n]
        for k, orig in self.norms.items():
            if len(k) >= 4 and len(n) >= 4 and (f" {n} " in f" {k} " or f" {k} " in f" {n} "):
                return orig
        return None

    def coverage(self, terms: list[str]) -> tuple[int, list[str]]:
        terms = [t.lower() for t in terms if t and len(t) >= 4]
        hits = [self.products[i]["name"] for i, n in enumerate(self.names) if any(t in n for t in terms)]
        return len(hits), hits[:3]
