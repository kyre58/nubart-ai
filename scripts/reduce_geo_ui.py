# scripts/reduce_geo_ui.py
"""
GEO UI reduction script.

Reads manually captured UI answers from geo_raw_ui.md
and applies the same deterministic reduction logic as reduce_geo.py.

No AI usage.
No interpretation.
Pure mechanical reduction.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

# Import config
# -------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402

REPO_ROOT = config.REPO_ROOT

# -------------------------
# Output files & constants
# -------------------------

SUMMARY_DIR = Path(config.SUMMARY_DATA_PATH)
MENTIONS_FILE = SUMMARY_DIR / "geo_mentions_ui.csv"
CHANGES_FILE = SUMMARY_DIR / "geo_changes_ui.csv"
STABILITY_FILE = SUMMARY_DIR / "geo_stability_ui.csv"

PROMPT_PATH = REPO_ROOT / config.PROMPT_PATH
RAW_UI_PATH = REPO_ROOT / "data" / "raw" / "geo_raw_ui.md"

BRAND = config.BRAND_KEYWORD
LANGUAGE = "en"

# -------------------------


# -------------------------
# Helpers (same logic as reduce_geo.py)
# -------------------------

def detect_brand_mention(text: str) -> bool:
	return BRAND.lower() in text.lower() if text else False


def detect_early_mention(text: str, limit: int = 200) -> bool:
	return BRAND.lower() in text[:limit].lower() if text else False


def count_brand_mentions(text: str) -> str:
	if not text:
		return "0"
	count = text.lower().count(BRAND.lower())
	if count == 0:
		return "0"
	if count == 1:
		return "1"
	return "2+"


def utc_now() -> str:
	return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def group_by_key(rows: List[Dict[str, str]], keys: Tuple[str, ...]):
	grouped = defaultdict(list)
	for r in rows:
		grouped[tuple(r[k] for k in keys)].append(r)
	return grouped


def detect_early_mention(text: str, limit: int = 200) -> bool:
	return BRAND.lower() in text[:limit].lower() if text else False


def count_brand_mentions(text: str) -> str:
	if not text:
		return "0"
	count = text.lower().count(BRAND.lower())
	if count == 0:
		return "0"
	if count == 1:
		return "1"
	return "2+"


def utc_now() -> str:
	return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def group_by_key(rows: List[Dict[str, str]], keys: Tuple[str, ...]):
	grouped = defaultdict(list)
	for r in rows:
		grouped[tuple(r[k] for k in keys)].append(r)
	return grouped


# -------------------------
# Parsing geo_raw_ui.md
# -------------------------

def parse_ui_md(md_text: str) -> List[Dict[str, str]]:
	blocks = md_text.split("{separator}")
	records = []

	for block in blocks:
		block = block.strip()
		if not block:
			continue

		prompt_id_match = re.search(r"prompt_id:\s*(.+)", block)
		if not prompt_id_match:
			continue

		prompt_id = prompt_id_match.group(1).strip()

		model_chunks = re.split(r"\nmodel:\s*", block)[1:]

		for chunk in model_chunks:
			lines = chunk.strip().splitlines()
			model = lines[0].strip()

			# Find the answer line and get everything until the next "model:" or end of chunk
			answer_match = re.search(r"answer:\s*(.*)", chunk, re.DOTALL)
			if answer_match:
				answer = answer_match.group(1).strip()
				# Remove any trailing "model:" sections that might have been captured
				answer = re.split(r"\nmodel:\s*", answer)[0].strip()
				# Defensive assertion to prevent parser bleed
				if "prompt_id:" in answer:
					raise ValueError(f"Parser bleed detected in {prompt_id} / {model}")
			else:
				answer = ""

			records.append({
				"prompt_id": prompt_id,
				"model": model,
				"response_text": answer,
			})

	return records


# -------------------------
# Reduction pipeline
# -------------------------

def main() -> None:
	global SUMMARY_DIR, MENTIONS_FILE, CHANGES_FILE, STABILITY_FILE, BRAND, LANGUAGE, PROMPT_PATH, RAW_UI_PATH
	
	SUMMARY_DIR = Path(config.SUMMARY_DATA_PATH)
	MENTIONS_FILE = SUMMARY_DIR / "geo_mentions_ui.csv"
	CHANGES_FILE = SUMMARY_DIR / "geo_changes_ui.csv"
	STABILITY_FILE = SUMMARY_DIR / "geo_stability_ui.csv"
	
	BRAND = "nubart"
	LANGUAGE = "en"
	PROMPT_PATH = REPO_ROOT / "prompts" / "geo_prompts.yaml"
	RAW_UI_PATH = REPO_ROOT / "data" / "raw" / "geo_raw_ui.md"
	SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

	run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
	run_date = datetime.now().strftime("%Y-%m-%d")
	timestamp = utc_now()

	# Load prompts metadata
	prompts = yaml.safe_load(PROMPT_PATH.read_text(encoding="utf-8"))
	prompt_index = {p["prompt_id"]: p for p in prompts}

	# Parse UI markdown
	md_text = RAW_UI_PATH.read_text(encoding="utf-8")
	ui_rows = parse_ui_md(md_text)

	# Build mention rows
	mentions = []
	for r in ui_rows:
		pid = r["prompt_id"]
		meta = prompt_index.get(pid, {})

		text = r["response_text"]

		mentions.append({
			"run_id": run_id,
			"run_date": run_date,
			"model": r["model"],
			"language": LANGUAGE,
			"product": meta.get("product", ""),
			"prompt_id": pid,
			"prompt_set": meta.get("prompt_set", ""),
			"intent": meta.get("intent", ""),
			"mentioned": "yes" if detect_brand_mention(text) else "no",
			"early_mentioned": "yes" if detect_early_mention(text) else "no",
			"mention_count": count_brand_mentions(text),
			"has_error": "no",
			"error_type": "no_error",
		})

	# -------------------------
	# Changes
	# -------------------------

	changes = []
	grouped = group_by_key(mentions, ("model", "language", "prompt_id"))

	for _, rows in grouped.items():
		rows_sorted = sorted(rows, key=lambda r: (r["run_date"], r["run_id"]))
		prev = None
		for cur in rows_sorted:
			if prev is None:
				changes.append({**cur, "previous_mentioned": "", "change": "baseline"})
			else:
				change = "changed" if cur["mentioned"] != prev["mentioned"] else "no_change"
				changes.append({**cur, "previous_mentioned": prev["mentioned"], "change": change})
			prev = cur

	# -------------------------
	# Stability
	# -------------------------

	stability = []
	grouped = group_by_key(changes, ("model", "language", "prompt_id"))

	for _, rows in grouped.items():
		values = [r["mentioned"] for r in rows if r["change"] != "baseline"]
		unique = set(values)

		if not values:
			state = "unknown"
		elif len(unique) == 1:
			state = "stable"
		else:
			state = "unstable"

		sample = rows[-1]
		stability.append({
			"model": sample["model"],
			"language": sample["language"],
			"product": sample["product"],
			"prompt_id": sample["prompt_id"],
			"prompt_set": sample["prompt_set"],
			"intent": sample["intent"],
			"stability": state,
			"runs_observed": str(len(rows)),
		})

	# -------------------------
	# Write CSVs
	# -------------------------

	def write_csv(path: Path, rows: List[Dict[str, str]]):
		if not rows:
			return
		with path.open("w", newline="", encoding="utf-8") as f:
			writer = csv.DictWriter(f, fieldnames=rows[0].keys())
			writer.writeheader()
			writer.writerows(rows)

	write_csv(MENTIONS_FILE, mentions)
	write_csv(CHANGES_FILE, changes)
	write_csv(STABILITY_FILE, stability)

	print("UI reduction complete:")
	print(f"- {MENTIONS_FILE}")
	print(f"- {CHANGES_FILE}")
	print(f"- {STABILITY_FILE}")


if __name__ == "__main__":
	main()
