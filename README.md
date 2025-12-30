# Nubart GEO Intelligence

## What this is

A lightweight measurement system that observes how major AI models (ChatGPT, Claude, Gemini, Perplexity) classify Nubart and its products over time.

It asks fixed questions, stores raw answers immutably, reduces them mechanically, and produces decision-level signals.

Most runs are expected to result in “do nothing.”

---

## What this is NOT

- Not a chatbot
- Not an SEO optimisation tool
- Not a copywriting system
- Not a competitor ranking engine
- Not an automated insight generator

This system measures reality.
Humans decide what (if anything) to do.

---

## Core principles

- Fixed prompts → comparable over time
- Append-only raw data → no rewriting history
- Deterministic reduction → no interpretation in code
- AI is a sensor, not a decision-maker
- Silence and stability are valid outcomes

---

## How it works

Prompts (YAML)
→ run_geo.py → raw CSV (append-only)
→ reduce_geo.py → summary CSVs
→ Human review → decision-level CTAs (rare)

Data flows downward only.
Decisions never flow back into the system.

---

## Where AI is used

AI is used only in two places:

1. Generating answers to fixed prompts
2. Rarely, helping explain a pre-selected anomaly

AI is not used for:
- selecting prompts
- detecting changes
- ranking competitors
- recommending actions

---

## How to run

python scripts/run_geo.py
python scripts/reduce_geo.py

- run_geo.py collects data only
- reduce_geo.py reduces data only

No script produces recommendations.

---

## Source of truth

data/raw/geo_raw.csv
Immutable, append-only, never cleaned.

Summary files can be regenerated at any time.
Raw data is never changed.

---

## Languages

Languages can be added at any time.

- A language’s first appearance defines its baseline
- Comparisons are made only within the same language
- No backfilling of historical runs

---

## Output & decisions

Outputs are:
- presence / absence
- stability / change
- structural patterns

CTAs are decision-level only (focus, deprioritise, monitor, do nothing).

Implementation work lives outside this system.

---

## Success criteria

This system is successful if:
- most runs show no meaningful change
- review takes minutes, not hours
- it reduces pressure to act
- “do nothing” is a defensible outcome
