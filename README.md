# dict-to-benchmark

A small pipeline that turns a Lakota pronunciation glossary into an
MMLU-style multiple-choice benchmark and scores local language models on it.

The benchmark direction is **English → Lakota**: *"What is the Lakota word
for X?"*, with one correct word and three random distractor words drawn from
the same glossary.

> **Scope.** This is a baseline harness built from a public web glossary in a
> folk-phonetic (non-standard) orthography. Scores measure recognition of
> *this source's* spellings and may reflect prior model exposure to the page.
> Treat it as a development baseline, not a governed evaluation set.

## Pipeline

Each step is an independent script; run them in order.

| Step | Script | Output |
|------|--------|--------|
| 1. Download | `scripts/fetch_glossary.py` | `raw/glossary.html` |
| 2. Parse | `scripts/parse_glossary.py` | `data/glossary.jsonl` |
| 3. Build questions | `scripts/build_questions.py` | `data/mmlu_lexical.jsonl` |
| 4. Evaluate | `scripts/eval_models.py` | `results/<model>.json` |

```bash
python3 scripts/fetch_glossary.py            # one-time; --force to refresh
python3 scripts/parse_glossary.py            # parses both page formats, dedups
python3 scripts/build_questions.py --seed 0  # 4-choice items, reproducible
python3 scripts/eval_models.py --model qwen2.5:7b   # needs a running Ollama
```

## Requirements

- Python 3.10+ with `requests`
- [Ollama](https://ollama.com/) running locally with the target model pulled,
  for step 4.

## Data format

`data/mmlu_lexical.jsonl` — one question per line:

```json
{
  "id": "lexical_baseline_0001",
  "direction": "en2lk",
  "prompt_english": "Surround",
  "question": "What is the Lakota word for \"Surround\"?",
  "choices": ["...", "...", "...", "..."],
  "answer": 2,
  "answer_text": "a ogluteya"
}
```

Distractors never reuse the target's English gloss, so a "wrong" option is
never secretly also correct.

## Source

Glossary: the Wolakota Project Lakota Pronunciation Glossary
(`wolakotaproject.org`). Glossary content belongs to its authors; this repo
contains only the processing code, not the data.
