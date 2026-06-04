#!/usr/bin/env python3
"""Parse raw/glossary.html into clean {lakota, english} pairs.

The Wolakota glossary mixes two entry formats inside <strong> blocks:

  Format A (~75 entries, lowercase headwords):
      lakota(pronunciation)…. english definition
      hanbleceya…. vision quest          (pronunciation sometimes absent)

  Format B (~3360 entries, UPPERCASE headwords):
      LAKOTA / English / pronunciation
      A OGLUTEYA / Surround / ah-oh-glue-day-yahn
  In B the English gloss sits in the MIDDLE; a few glosses contain a
  slash themselves (e.g. "Father(his/her)"), so we take lakota=first
  part, pronunciation=last part, english=everything between.

Output: data/glossary.jsonl, one object per line:
  {"lakota": "...", "lakota_raw": "...", "english": "...",
   "pronunciation": "...", "format": "A"|"B"}

`lakota` is lowercased/space-normalized for consistent multiple-choice
options; `lakota_raw` preserves the original casing from the page.
"""
import argparse
import html as ihtml
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "raw" / "glossary.html"
OUT = ROOT / "data" / "glossary.jsonl"

ELLIPSIS = chr(0x2026)
# A run of ellipsis/dots/colon that separates headword from gloss in format A.
SEP_A = re.compile(r"[….:]{2,}|…")


def clean(text: str) -> str:
    """Collapse whitespace (incl. non-breaking) in a parsed field."""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def strip_pron_paren(headword: str) -> str:
    """Drop a trailing (pronunciation) parenthetical from a format-A headword."""
    return clean(re.sub(r"\(.*", "", headword))


def extract_blocks(raw: str) -> list[str]:
    """Pull individual entry strings out of the <strong>…</strong> blocks."""
    out = []
    for block in re.findall(r"<strong>(.*?)</strong>", raw, flags=re.S):
        for piece in re.split(r"<br\s*/?>", block):
            piece = ihtml.unescape(re.sub(r"<.*?>", "", piece)).strip()
            if piece:
                out.append(piece)
    return out


def parse_entry(entry: str):
    """Return (lakota_raw, english, pronunciation, fmt) or None if unparseable."""
    if "/" in entry and ELLIPSIS not in entry:
        parts = [clean(p) for p in entry.split("/")]
        if len(parts) >= 3:
            lakota_raw, pron = parts[0], parts[-1]
            english = "/".join(parts[1:-1]).strip()
            return lakota_raw, english, pron, "B"
        return None

    m = SEP_A.search(entry)
    if not m:
        return None
    head, english = entry[: m.start()], entry[m.end():]
    pron_match = re.search(r"\(([^)]*)", head)
    pron = clean(pron_match.group(1)) if pron_match else ""
    return strip_pron_paren(head), clean(english), pron, "A"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=SRC)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.src.exists():
        print(f"Missing {args.src}. Run fetch_glossary.py first.", file=sys.stderr)
        return 1

    raw = args.src.read_text(encoding="utf-8")
    blocks = extract_blocks(raw)

    rows, seen = [], set()
    skipped = 0
    for entry in blocks:
        parsed = parse_entry(entry)
        if parsed is None:
            skipped += 1
            continue
        lakota_raw, english, pron, fmt = parsed
        lakota = clean(lakota_raw).lower()
        # Reject empties and degenerate single-letter alphabet headers.
        if not lakota or not english or len(lakota) < 2 or len(english) < 2:
            skipped += 1
            continue
        key = (lakota, english.lower())
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "lakota": lakota,
            "lakota_raw": clean(lakota_raw),
            "english": english,
            "pronunciation": pron,
            "format": fmt,
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    fa = sum(1 for r in rows if r["format"] == "A")
    fb = sum(1 for r in rows if r["format"] == "B")
    print(f"Parsed {len(rows)} pairs (A={fa}, B={fb}); skipped {skipped} blocks.")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
