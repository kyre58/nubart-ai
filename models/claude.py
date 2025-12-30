# models/claude.py

import os
from typing import Dict

import requests

API_URL = "https://api.anthropic.com/v1/messages"
MODEL_NAME = "claude-sonnet-4-5-20250929"
ANTHROPIC_VERSION = "2023-06-01"


def run(prompt: str, language: str) -> Dict[str, str]:
	api_key = os.environ.get("CLAUDE_API_KEY")
	if not api_key:
		raise RuntimeError("CLAUDE_API_KEY is not set")

	headers = {
		"x-api-key": api_key,
		"anthropic-version": ANTHROPIC_VERSION,
		"content-type": "application/json",
	}
	payload = {
		"model": MODEL_NAME,
		"max_tokens": 1024,
		"messages": [
			{
				"role": "user",
				"content": [
					{"type": "text", "text": prompt},
				],
			}
		],
	}

	response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
	if response.status_code != 200:
		raise RuntimeError(f"Claude API error {response.status_code}: {response.text}")

	data = response.json()
	response_text = ""
	content = data.get("content") or []
	if content:
		texts = [item.get("text", "") for item in content if item.get("type") == "text"]
		response_text = "".join(texts).strip()

	return {"response_text": response_text, "model_version": MODEL_NAME}
