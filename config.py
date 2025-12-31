# config.py
# Shared configuration for the GEO intelligence system.
# This file contains constants only. No logic.

from __future__ import annotations

import os
from pathlib import Path

# Load .env if it exists
dotenv_path = Path(__file__).resolve().parent / ".env"
if dotenv_path.exists():
	from dotenv import load_dotenv
	load_dotenv(dotenv_path)

# -------------------------
# Languages
# -------------------------
# Languages currently active in GEO runs.
# New languages can be added at any time.
# A language’s first appearance defines its baseline.

LANGUAGES = [
	"en",
	"de",
	"fr",
]

# -------------------------
# Models
# -------------------------
# Model identifiers must match adapter filenames in /models.

MODELS = [
	"chatgpt",
	"claude",
	"gemini",
	"perplexity",
]

# -------------------------
# Paths
# -------------------------

REPO_ROOT = Path(__file__).resolve().parent

PROMPT_PATH = "prompts/geo_prompts.yaml"

RAW_DATA_PATH = str(REPO_ROOT / "data" / "raw" / "geo_raw_api.csv")

SUMMARY_DATA_PATH = str(REPO_ROOT / "data" / "summary" / "")

# -------------------------
# Run configuration
# -------------------------
# Date format used for run_id and run_date.

RUN_DATE_FORMAT = "%Y-%m-%d"

# -------------------------
# Reduction configuration
# -------------------------
# Keyword used for mention detection.
# Detection should be simple and deterministic.

BRAND_KEYWORD = "nubart"

# -------------------------
# Headers
# -------------------------
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
