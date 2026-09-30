"""Export a public report without private catalog product-name examples.

The pipeline's raw output stays local. This only prepares publication artifacts;
scores, ordering and recommendations are preserved.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scout.report import render


def public_results(value):
    if isinstance(value, dict):
        return {key: public_results(item) for key, item in value.items()
                if key != "vitalabo_examples"}
    if isinstance(value, list):
        return [public_results(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="output/vitalabo/results.json")
    parser.add_argument("--output", default="docs")
    args = parser.parse_args()
    data = public_results(json.loads(Path(args.input).read_text(encoding="utf-8")))
    destination = Path(args.output)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "results.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    html = render(data)
    links = ('<p class="muted"><a href="pipeline.html">Pipeline im Detail</a> · '
             '<a href="PIPELINE.md">Markdown</a> · '
             '<a href="https://github.com/Lukas244654/vitalabo-sortiments-scout" '
             'target="_blank" rel="noopener noreferrer">Code auf GitHub</a> · '
             '<a href="REVIEW.md">Review und Grenzen</a></p>')
    marker = '<div class="facts" id="h-facts"></div>'
    if marker not in html:
        raise SystemExit("Report navigation anchor missing; export not written.")
    (destination / "index.html").write_text(html.replace(marker, marker + links, 1), encoding="utf-8")
    print(f"Public report: {destination.resolve() / 'index.html'}")


if __name__ == "__main__":
    main()
