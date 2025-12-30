# models/perplexity.py

import os
from typing import Dict

import requests

API_URL = "https://api.perplexity.ai/chat/completions"
MODEL_NAME = "sonar"


def run(prompt: str, language: str) -> Dict[str, str]:
	api_key = os.environ.get("PERPLEXITY_API_KEY")
	if not api_key:
		raise RuntimeError("PERPLEXITY_API_KEY is not set")

	headers = {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json",
	}
	payload = {
		"model": MODEL_NAME,
		"messages": [
			{
				"role": "user",
				"content": prompt,
			}
		],
	}

	response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
	response.raise_for_status()

	data = response.json()
	response_text = ""
	choices = data.get("choices") or []
	if choices:
		message = choices[0].get("message") or {}
		response_text = str(message.get("content", "")).strip()

	return {"response_text": response_text, "model_version": MODEL_NAME}
