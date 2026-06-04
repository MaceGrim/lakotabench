#!/usr/bin/env python3
"""Build an MMLU-style multiple-choice set from data/glossary.jsonl.

Direction: English -> Lakota ("What is the Lakota word for X?").
Each item has 4 choices: the correct Lakota word plus 3 random distractor
Lakota words drawn from the glossary.

Distractor guard: a distractor is never allowed to share the target's
English gloss (93 glosses map to >1 Lakota word in this source), which
would otherwise make a "wrong" option arguably correct. Distractor option
strings are also kept distinct from each other and the answer.

Output: data/mmlu_lexical.jsonl, one item per line:
  {"id","category","direction","prompt_english","question",
   "choices":[4],"answer":int,"answer_text","source"}
"""
import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "glossary.jsonl"
OUT = ROOT / "data" / "mmlu_lexical.jsonl"
SOURCE = "wolakotaproject pronunciation glossary"
CATEGORY = "lexical_baseline"
N_CHOICES = 4


def load_pairs(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def pick_distractors(target: dict, pool: list[dict], rng: random.Random, n: int):
    """Sample n distractor Lakota strings, distinct and not gloss-colliding."""
    target_eng = target["english"].lower()
    target_lak = target["lakota"]
    candidates = [r for r in pool if r["lakota"] != target_lak and r["english"].lower() != target_eng]
    rng.shuffle(candidates)
    chosen: list[str] = []
    seen = {target_lak}
    for r in candidates:
        if r["lakota"] in seen:
            continue
        seen.add(r["lakota"])
        chosen.append(r["lakota"])
        if len(chosen) == n:
            return chosen
    return None  # not enough distinct distractors (only near tiny pools)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=SRC)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--seed", type=int, default=0, help="RNG seed for reproducibility")
    ap.add_argument("--n", type=int, default=0, help="max questions (0 = all pairs)")
    args = ap.parse_args()

    if not args.src.exists():
        print(f"Missing {args.src}. Run parse_glossary.py first.", file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    pairs = load_pairs(args.src)
    targets = list(pairs)
    rng.shuffle(targets)
    if args.n > 0:
        targets = targets[: args.n]

    items, dropped = [], 0
    for target in targets:
        distractors = pick_distractors(target, pairs, rng, N_CHOICES - 1)
        if distractors is None:
            dropped += 1
            continue
        choices = distractors + [target["lakota"]]
        rng.shuffle(choices)
        answer = choices.index(target["lakota"])
        items.append({
            "id": f"{CATEGORY}_{len(items):04d}",
            "category": CATEGORY,
            "direction": "en2lk",
            "prompt_english": target["english"],
            "question": f'What is the Lakota word for "{target["english"]}"?',
            "choices": choices,
            "answer": answer,
            "answer_text": target["lakota"],
            "source": SOURCE,
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    print(f"Wrote {len(items)} questions to {args.out} (dropped {dropped}, seed={args.seed}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
