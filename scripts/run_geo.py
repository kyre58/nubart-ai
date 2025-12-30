# scripts/run_geo.py

"""
GEO collection script ("camera shutter").

Responsibilities (ONLY):
- Load prompts from YAML
- Generate a run_id
- Loop prompt × language × model
- Call model adapters
- Append one row per call to the raw CSV (append-only)

NOT responsible for:
- analysis, filtering, insights
- change detection
- recommendations
- Discord/reporting output
"""

from __future__ import annotations

import argparse
import csv
import importlib
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Import config from repo root (geo/config.py)
# We compute repo root reliably even when run from scripts/ directory.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import config  # noqa: E402

# Use REPO_ROOT from config for consistency
REPO_ROOT = config.REPO_ROOT


RAW_HEADERS = [
	"run_id",
	"run_date",
	"timestamp_utc",
	"model",
	"model_version",
	"language",
	"product",
	"prompt_id",
	"prompt_set",
	"intent",
	"prompt_text",
	"response_text",
	"error",
]


@dataclass(frozen=True)
class Prompt:
	prompt_id: str
	prompt_set: str
	product: str
	intent: str
	text: Dict[str, str]


def _utc_iso(ts: Optional[datetime] = None) -> str:
	if ts is None:
		ts = datetime.now(timezone.utc)
	elif ts.tzinfo is None:
		ts = ts.replace(tzinfo=timezone.utc)
	else:
		ts = ts.astimezone(timezone.utc)
	return ts.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_prompts(prompt_path: Path) -> List[Prompt]:
	with prompt_path.open("r", encoding="utf-8") as f:
		data = yaml.safe_load(f)

	if not isinstance(data, list):
		raise ValueError("Prompt YAML must be a list of prompt objects.")

	prompts: List[Prompt] = []
	for i, item in enumerate(data):
		if not isinstance(item, dict):
			raise ValueError(f"Prompt entry #{i} must be a mapping/object.")

		for field in ("prompt_id", "prompt_set", "product", "intent", "text"):
			if field not in item:
				raise ValueError(f"Prompt entry #{i} missing required field: {field}")

		if not isinstance(item["text"], dict):
			raise ValueError(f"Prompt entry #{i} field 'text' must be a mapping of language->string.")

		prompts.append(
			Prompt(
				prompt_id=str(item["prompt_id"]).strip(),
				prompt_set=str(item["prompt_set"]).strip(),
				product=str(item["product"]).strip(),
				intent=str(item["intent"]).strip(),
				text={str(k).strip(): str(v) for k, v in item["text"].items()},
			)
		)

	# Basic sanity: unique prompt_ids
	ids = [p.prompt_id for p in prompts]
	if len(ids) != len(set(ids)):
		dupes = sorted({x for x in ids if ids.count(x) > 1})
		raise ValueError(f"Duplicate prompt_id(s) found: {dupes}")

	return prompts


def ensure_raw_csv(raw_path: Path) -> None:
	raw_path.parent.mkdir(parents=True, exist_ok=True)
	if not raw_path.exists():
		with raw_path.open("w", newline="", encoding="utf-8") as f:
			writer = csv.DictWriter(f, fieldnames=RAW_HEADERS)
			writer.writeheader()


def append_row(raw_path: Path, row: Dict[str, Any]) -> None:
	# Keep append-only behavior always.
	with raw_path.open("a", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=RAW_HEADERS)
		writer.writerow({h: row.get(h, "") for h in RAW_HEADERS})


def load_adapter(model_name: str):
	"""
	Loads adapter module: models/<model_name>.py
	Adapter must expose: run(prompt: str, language: str) -> dict
	"""
	module_name = f"models.{model_name}"
	try:
		mod = importlib.import_module(module_name)
	except Exception as e:
		raise ImportError(f"Could not import adapter '{module_name}': {e}") from e

	if not hasattr(mod, "run"):
		raise AttributeError(f"Adapter '{module_name}' must define a function: run(prompt: str, language: str) -> dict")

	return mod


def parse_args() -> argparse.Namespace:
	p = argparse.ArgumentParser(description="Collect GEO answers and append them to the raw CSV.")
	p.add_argument("--models", nargs="*", default=None, help="Override models list (e.g. chatgpt gemini).")
	p.add_argument("--languages", nargs="*", default=None, help="Override languages list (e.g. en de fr).")
	p.add_argument("--prompt-set", default=None, help="Run only a specific prompt_set (e.g. core).")
	p.add_argument("--dry-run", action="store_true", help="Print planned calls, do not write CSV or call models.")
	return p.parse_args()


def main() -> int:
	args = parse_args()

	prompt_path = (REPO_ROOT / config.PROMPT_PATH).resolve()
	raw_path = (REPO_ROOT / config.RAW_DATA_PATH).resolve()

	models = args.models if args.models is not None and len(args.models) > 0 else list(config.MODELS)
	languages = args.languages if args.languages is not None and len(args.languages) > 0 else list(config.LANGUAGES)
	prompt_set_filter = args.prompt_set

	run_date = datetime.now().strftime(getattr(config, "RUN_DATE_FORMAT", "%Y-%m-%d"))
	run_id = datetime.now().strftime("%Y%m%d-%H%M%S")  # human-readable, unique enough

	prompts = load_prompts(prompt_path)
	if prompt_set_filter:
		prompts = [p for p in prompts if p.prompt_set == prompt_set_filter]

	if not prompts:
		print("No prompts to run (check --prompt-set filter and YAML).", file=sys.stderr)
		return 2

	# Load adapters once
	adapters = {}
	for m in models:
		try:
			adapters[m] = load_adapter(m)
		except Exception as e:
			# Adapter missing is a hard failure because we can't run that model.
			print(f"[FATAL] {e}", file=sys.stderr)
			return 2

	planned_calls = sum(1 for _ in prompts for __ in languages for ___ in models)
	print(f"Run: run_id={run_id} date={run_date} prompts={len(prompts)} languages={len(languages)} models={len(models)} total_calls={planned_calls}")

	if args.dry_run:
		for p in prompts:
			for lang in languages:
				text = p.text.get(lang)
				if not text:
					print(f"[SKIP] Missing translation: prompt_id={p.prompt_id} language={lang}")
					continue
				for m in models:
					print(f"[DRY] model={m} language={lang} prompt_id={p.prompt_id}")
		return 0

	ensure_raw_csv(raw_path)

	start_time = time.time()
	calls_done = 0
	total_calls = planned_calls

	# Collection loop: always append a row per attempted call.
	for p in prompts:
		for lang in languages:
			prompt_text = p.text.get(lang)
			if not prompt_text:
				# Missing translation is a data fact; we record it as an error row.
				row = {
					"run_id": run_id,
					"run_date": run_date,
					"timestamp_utc": _utc_iso(),
					"model": "",
					"model_version": "",
					"language": lang,
					"product": p.product,
					"prompt_id": p.prompt_id,
					"prompt_set": p.prompt_set,
					"intent": p.intent,
					"prompt_text": "",
					"response_text": "",
					"error": f"missing_translation:{lang}",
				}
				append_row(raw_path, row)
				print(f"[WARN] Missing translation recorded: prompt_id={p.prompt_id} language={lang}")
				calls_done += 1
				continue

			for m in models:
				adapter = adapters[m]
				error = ""
				response_text = ""
				model_version = ""

				try:
					result = adapter.run(prompt=prompt_text, language=lang)  # type: ignore[attr-defined]
					if not isinstance(result, dict):
						raise TypeError("Adapter returned non-dict result.")

					response_text = str(result.get("response_text", "")).strip()
					model_version = str(result.get("model_version", "")).strip()
				except Exception as e:
					# Never crash the run for one failed call. Record and continue.
					error = f"{type(e).__name__}: {e}"

				row = {
					"run_id": run_id,
					"run_date": run_date,
					"timestamp_utc": _utc_iso(),
					"model": m,
					"model_version": model_version,
					"language": lang,
					"product": p.product,
					"prompt_id": p.prompt_id,
					"prompt_set": p.prompt_set,
					"intent": p.intent,
					"prompt_text": prompt_text,
					"response_text": response_text,
					"error": error,
				}
				append_row(raw_path, row)

				calls_done += 1
				elapsed = time.time() - start_time
				if error:
					print(f"[ERR] model={m} lang={lang} prompt_id={p.prompt_id} -> {error}")
				else:
					print(f"[OK]  model={m} lang={lang} prompt_id={p.prompt_id}")

				if calls_done < total_calls:
					mins, secs = divmod(int(elapsed), 60)
					print(f"[TIME] Elapsed: {mins}m {secs}s ({calls_done}/{total_calls})")

	total_elapsed = time.time() - start_time
	mins, secs = divmod(int(total_elapsed), 60)
	print(f"Done. Appended rows to: {raw_path}")
	print(f"[TIME] Total elapsed: {mins}m {secs}s")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
