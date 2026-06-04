#!/usr/bin/env python3
"""Download the Wolakota pronunciation glossary HTML.

Fetches once into raw/ so the parser can be re-run freely without
re-hitting the site. Re-run with --force to refresh.
"""
import argparse
import sys
from pathlib import Path

import requests

URL = "https://www.wolakotaproject.org/lakota-pronunciation-glossary/"
OUT = Path(__file__).resolve().parent.parent / "raw" / "glossary.html"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="re-download even if cached")
    args = ap.parse_args()

    if OUT.exists() and not args.force:
        print(f"{OUT} already exists ({OUT.stat().st_size} bytes). Use --force to refresh.")
        return 0

    print(f"Fetching {URL} ...")
    resp = requests.get(URL, headers={"User-Agent": "lakotabench/0.1 (research prototype)"}, timeout=30)
    resp.raise_for_status()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(resp.text, encoding="utf-8")
    print(f"Wrote {len(resp.text)} chars to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
