"""OpenRouter-Client ohne Zusatzpakete (nur Standardbibliothek).

- wählt pro Rolle das erste verfügbare Modell aus der Config
- optional Websuche über das OpenRouter-Web-Plugin (liefert Quellen als url_citation)
- Disk-Cache: identische Anfragen kosten beim zweiten Lauf nichts
- zählt Tokens und Kosten mit
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://openrouter.ai/api/v1"


def load_env(path: Path) -> None:
    """Minimaler .env-Loader (KEY=VALUE pro Zeile)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def extract_json(text: str):
    """Holt das erste JSON-Objekt/-Array aus einer Modellantwort (auch in ```json-Blöcken)."""
    if not text:
        raise ValueError("leere Antwort")
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if not starts:
        raise ValueError("kein JSON gefunden")
    start = min(starts)
    closer = "}" if text[start] == "{" else "]"
    end = text.rfind(closer)
    return json.loads(text[start : end + 1])


class LLM:
    def __init__(self, cfg: dict, cache_dir: Path, log=print):
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise SystemExit("OPENROUTER_API_KEY fehlt (in .env eintragen oder als Umgebungsvariable setzen).")
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log = log
        self.lock = threading.Lock()
        self.stats = {"calls": 0, "cached": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0}
        self.models = self._resolve_models(cfg["models"])

    # ---------- Modellwahl ----------
    def _resolve_models(self, wanted: dict) -> dict:
        try:
            req = urllib.request.Request(f"{API}/models", headers={"User-Agent": "sortiments-scout"})
            with urllib.request.urlopen(req, timeout=30) as r:
                available = {m["id"] for m in json.load(r)["data"]}
        except Exception as e:  # Modellliste nicht erreichbar -> erste Wahl nehmen
            self.log(f"  Modellliste nicht abrufbar ({e}); nehme jeweils die erste Modell-ID.")
            return {role: ids[0] for role, ids in wanted.items()}
        chosen = {}
        for role, ids in wanted.items():
            pick = next((i for i in ids if i in available or i == "openrouter/auto"), ids[-1])
            chosen[role] = pick
        return chosen

    # ---------- Aufruf ----------
    def chat(self, role: str, system: str, user: str, web: bool = False, web_results: int = 6,
             max_tokens: int = 4000, temperature: float = 0.2) -> dict:
        model = self.models[role]
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "usage": {"include": True},
        }
        if web:
            body["plugins"] = [{"id": "web", "max_results": web_results}]

        key = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:24]
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            with self.lock:
                self.stats["cached"] += 1
            return json.loads(cache_file.read_text(encoding="utf-8"))

        data = json.dumps(body).encode()
        last_err = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(
                    f"{API}/chat/completions", data=data, method="POST",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/sortiments-scout",
                        "X-Title": "KI Sortiments Scout (Prototyp)",
                    },
                )
                with urllib.request.urlopen(req, timeout=240) as r:
                    resp = json.load(r)
                if "error" in resp:
                    raise RuntimeError(resp["error"])
                msg = resp["choices"][0]["message"]
                sources = []
                for a in msg.get("annotations") or []:
                    if a.get("type") == "url_citation":
                        c = a.get("url_citation", {})
                        if c.get("url") and c["url"] not in [s["url"] for s in sources]:
                            sources.append({"url": c["url"], "title": c.get("title", "")})
                usage = resp.get("usage") or {}
                out = {"text": msg.get("content") or "", "sources": sources, "model": resp.get("model", model)}
                with self.lock:
                    self.stats["calls"] += 1
                    self.stats["prompt_tokens"] += usage.get("prompt_tokens", 0) or 0
                    self.stats["completion_tokens"] += usage.get("completion_tokens", 0) or 0
                    self.stats["cost_usd"] += float(usage.get("cost", 0) or 0)
                cache_file.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
                return out
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="ignore")[:300]
                last_err = f"HTTP {e.code}: {detail}"
                if e.code in (400, 401, 402, 403):  # nicht wiederholbar
                    break
            except Exception as e:
                last_err = str(e)
            time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"OpenRouter-Aufruf fehlgeschlagen ({model}): {last_err}")

    def chat_json(self, role: str, system: str, user: str, **kw):
        """chat() + JSON-Parsing; bei kaputtem JSON ein Reparaturversuch ohne Websuche."""
        res = self.chat(role, system, user, **kw)
        try:
            return extract_json(res["text"]), res
        except Exception:
            fix = self.chat(role, "Gib ausschließlich gültiges JSON zurück, ohne Kommentar.",
                            "Repariere dieses JSON bzw. extrahiere die Daten als gültiges JSON:\n\n" + res["text"][:12000],
                            max_tokens=kw.get("max_tokens", 4000))
            return extract_json(fix["text"]), res
