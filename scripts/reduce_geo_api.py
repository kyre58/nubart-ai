# scripts/reduce_geo.py

"""
GEO reduction script.

Responsibilities (ONLY):
- Read raw append-only CSV
- Detect simple, explicit facts (no interpretation)
- Compare current run vs previous run per prompt/language/model
- Write deterministic summary CSVs

NOT responsible for:
- AI calls
- explanations
- recommendations
- dashboards
"""

from __future__ import annotations

import csv
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import sys

# Import config
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402

REPO_ROOT = config.REPO_ROOT


# -------------------------
# Output files
# -------------------------

MENTIONS_FILE = Path(config.SUMMARY_DATA_PATH) / "geo_mentions_api.csv"
CHANGES_FILE = Path(config.SUMMARY_DATA_PATH) / "geo_changes_api.csv"
STABILITY_FILE = Path(config.SUMMARY_DATA_PATH) / "geo_stability_api.csv"


# -------------------------
# Helpers
# -------------------------

def read_raw_rows(raw_path: Path) -> List[Dict[str, str]]:
	if not raw_path.exists():
		raise FileNotFoundError(f"Raw data file not found: {raw_path}")

	with raw_path.open("r", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		return list(reader)


def detect_brand_mention(text: str, brand: str) -> bool:
	if not text:
		return False
	return brand.lower() in text.lower()


def detect_early_mention(text: str, brand: str, limit: int = 200) -> bool:
	if not text:
		return False
	return brand.lower() in text[:limit].lower()


def count_brand_mentions(text: str, brand: str) -> str:
	if not text:
		return "0"
	count = text.lower().count(brand.lower())
	if count == 0:
		return "0"
	if count == 1:
		return "1"
	return "2+"


def classify_error(error: str) -> str:
	if not error:
		return "no_error"
	e = error.lower()
	if "timeout" in e:
		return "timeout"
	if "auth" in e or "key" in e:
		return "auth"
	return "other"


def ensure_dir(path: Path) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)


# -------------------------
# Reduction logic
# -------------------------

def build_mentions_table(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
	"""
	One row per:
	run_id × model × language × prompt_id
	"""
	output = []

	for r in rows:
		response_text = r.get("response_text", "")
		error_raw = r.get("error", "")

		mentioned = detect_brand_mention(response_text, config.BRAND_KEYWORD)
		early_mentioned = detect_early_mention(response_text, config.BRAND_KEYWORD)
		mention_count = count_brand_mentions(response_text, config.BRAND_KEYWORD)
		error_type = classify_error(error_raw)

		output.append({
			"run_id": r["run_id"],
			"run_date": r["run_date"],
			"model": r["model"],
			"language": r["language"],
			"product": r["product"],
			"prompt_id": r["prompt_id"],
			"prompt_set": r["prompt_set"],
			"intent": r["intent"],

			# A + B
			"mentioned": "yes" if mentioned else "no",
			"early_mentioned": "yes" if early_mentioned else "no",
			"mention_count": mention_count,

			# C
			"has_error": "yes" if error_raw else "no",
			"error_type": error_type,
		})

	return output


def group_by_key(rows: List[Dict[str, str]], keys: Tuple[str, ...]) -> Dict[Tuple[str, ...], List[Dict[str, str]]]:
	grouped: Dict[Tuple[str, ...], List[Dict[str, str]]] = defaultdict(list)
	for r in rows:
		grouped[tuple(r[k] for k in keys)].append(r)
	return grouped


def build_change_table(mentions: List[Dict[str, str]]) -> List[Dict[str, str]]:
	"""
	Compare each run to the immediately previous run
	for the same model × language × prompt_id.
	"""
	output = []

	grouped = group_by_key(
		mentions,
		keys=("model", "language", "prompt_id"),
	)

	for (_, _, _), rows in grouped.items():
		rows_sorted = sorted(rows, key=lambda r: (r["run_date"], r["run_id"]))

		previous = None
		for current in rows_sorted:
			if previous is None:
				output.append({
					**current,
					"previous_mentioned": "",
					"change": "baseline",
				})
			else:
				change = "no_change"
				if current["mentioned"] != previous["mentioned"]:
					change = "changed"

				output.append({
					**current,
					"previous_mentioned": previous["mentioned"],
					"change": change,
				})

			previous = current

	return output


def build_stability_table(changes: List[Dict[str, str]]) -> List[Dict[str, str]]:
	"""
	Summarise stability per model × language × prompt_id.
	"""
	output = []

	grouped = group_by_key(
		changes,
		keys=("model", "language", "prompt_id"),
	)

	for _, rows in grouped.items():
		mention_values = [
			r["mentioned"]
			for r in rows
			if r["change"] != "baseline" and r.get("has_error") == "no"
		]

		unique_states = set(mention_values)

		if not mention_values:
			stability = "unknown"
		elif len(unique_states) == 1:
			stability = "stable"
		else:
			stability = "unstable"

		sample = rows[-1]

		output.append({
			"model": sample["model"],
			"language": sample["language"],
			"product": sample["product"],
			"prompt_id": sample["prompt_id"],
			"prompt_set": sample["prompt_set"],
			"intent": sample["intent"],
			"stability": stability,
			"runs_observed": str(len(rows)),
		})

	return output


# -------------------------
# Writers
# -------------------------

def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
	if not rows:
		return

	ensure_dir(path)

	with path.open("w", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=rows[0].keys())
		writer.writeheader()
		writer.writerows(rows)


# -------------------------
# Main
# -------------------------

def main() -> None:
	start_time = time.time()
	raw_path = Path(config.RAW_DATA_PATH)

	print(f"Reading raw data from: {raw_path}")
	rows = read_raw_rows(raw_path)

	print("Building mention table...")
	mentions = build_mentions_table(rows)

	print("Building change table...")
	changes = build_change_table(mentions)

	print("Building stability table...")
	stability = build_stability_table(changes)

	print("Writing summary files...")
	write_csv(MENTIONS_FILE, mentions)
	write_csv(CHANGES_FILE, changes)
	write_csv(STABILITY_FILE, stability)

	mins, secs = divmod(int(time.time() - start_time), 60)
	print("Reduction complete.")
	print(f"- {MENTIONS_FILE}")
	print(f"- {CHANGES_FILE}")
	print(f"- {STABILITY_FILE}")
	print(f"[TIME] Total elapsed: {mins}m {secs}s")


if __name__ == "__main__":
	main()
