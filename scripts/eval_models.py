#!/usr/bin/env python3
"""Evaluate a local Ollama model on the Lakota lexical MCQ set.

Sends each multiple-choice question to an Ollama model, parses the chosen
letter, and scores against the key. Writes a per-model JSON report to
results/<model>.json with overall accuracy and every wrong answer.

Requires a running Ollama server (default http://localhost:11434) and the
target model pulled locally.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "mmlu_lexical.jsonl"
RESULTS_DIR = ROOT / "results"
LETTERS = "ABCDEFGH"

PROMPT_TEMPLATE = (
    "Answer the following multiple choice question about the Lakota language.\n"
    "Respond with only the single letter of the correct answer.\n\n"
    "{question}\n{options}\n\nAnswer:"
)


def load_items(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def format_prompt(item: dict) -> str:
    options = "\n".join(f"{LETTERS[i]}. {c}" for i, c in enumerate(item["choices"]))
    return PROMPT_TEMPLATE.format(question=item["question"], options=options)


def parse_letter(text: str, n_choices: int) -> int | None:
    """Return the chosen option index, or None if no valid letter found.

    Strips <think>…</think> reasoning blocks (deepseek-r1) before parsing,
    then takes the first A–D letter (upper or lower) that stands alone
    rather than being embedded in a word like "Answer".
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)
    valid = LETTERS[:n_choices]
    m = re.search(rf"(?<![A-Za-z])([{valid}{valid.lower()}])(?![A-Za-z])", text)
    return LETTERS.index(m.group(1).upper()) if m else None


def query_ollama(host: str, model: str, prompt: str, timeout: int) -> str:
    resp = requests.post(
        f"{host}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False,
              "options": {"temperature": 0}},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, help="Ollama model name, e.g. qwen2.5:7b")
    ap.add_argument("--src", type=Path, default=SRC)
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--n", type=int, default=0, help="evaluate first N questions (0 = all)")
    ap.add_argument("--timeout", type=int, default=120, help="per-request timeout (s)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    if not args.src.exists():
        print(f"Missing {args.src}. Run build_questions.py first.", file=sys.stderr)
        return 1

    items = load_items(args.src)
    if args.n > 0:
        items = items[: args.n]

    correct, unparsed, wrong = 0, 0, []
    start = time.time()
    for idx, item in enumerate(items, 1):
        text = query_ollama(args.host, args.model, format_prompt(item), args.timeout)
        choice = parse_letter(text, len(item["choices"]))
        if choice is None:
            unparsed += 1
        if choice == item["answer"]:
            correct += 1
        else:
            wrong.append({
                "id": item["id"],
                "prompt_english": item["prompt_english"],
                "expected": LETTERS[item["answer"]],
                "expected_text": item["answer_text"],
                "got": LETTERS[choice] if choice is not None else None,
                "raw": text.strip()[:200],
            })
        if idx % 50 == 0:
            print(f"  {idx}/{len(items)}  acc={correct/idx:.3f}", file=sys.stderr)

    n = len(items)
    elapsed = time.time() - start
    report = {
        "model": args.model,
        "source": str(args.src),
        "n_questions": n,
        "n_correct": correct,
        "accuracy": round(correct / n, 4) if n else 0.0,
        "n_unparsed": unparsed,
        "random_baseline": round(1 / len(items[0]["choices"]), 4) if n else None,
        "seconds": round(elapsed, 1),
        "wrong": wrong,
    }

    out = args.out or RESULTS_DIR / f"{args.model.replace(':', '_').replace('/', '_')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{args.model}: {correct}/{n} = {report['accuracy']:.1%} "
          f"(random {report['random_baseline']:.1%}, {unparsed} unparsed) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
