# models/gemini.py

import os
from typing import Dict

import requests

MODEL_NAME = "gemini-2.5-pro"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"


def run(prompt: str, language: str) -> Dict[str, str]:
	api_key = os.environ.get("GEMINI_API_KEY")
	if not api_key:
		raise RuntimeError("GEMINI_API_KEY is not set")

	headers = {"Content-Type": "application/json"}
	payload = {
		"contents": [
			{
				"role": "user",
				"parts": [
					{"text": prompt},
				],
			}
		]
	}

	response = requests.post(f"{API_URL}?key={api_key}", headers=headers, json=payload, timeout=30)
	response.raise_for_status()

	data = response.json()
	response_text = ""
	candidates = data.get("candidates") or []
	if candidates:
		content = candidates[0].get("content") or {}
		parts = content.get("parts") or []
		texts = [part.get("text", "") for part in parts if "text" in part]
		response_text = "".join(texts).strip()

	return {"response_text": response_text, "model_version": MODEL_NAME}
