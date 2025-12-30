# models/chatgpt.py

import os
from typing import Dict

import requests

API_URL = "https://api.openai.com/v1/responses"
MODEL_NAME = "gpt-4.1"


def run(prompt: str, language: str) -> Dict[str, str]:
	api_key = os.environ.get("CHATGPT_API_KEY")
	if not api_key:
		raise RuntimeError("CHATGPT_API_KEY is not set")

	headers = {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json",
	}
	payload = {"model": MODEL_NAME, "input": prompt}

	response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
	if response.status_code != 200:
		raise RuntimeError(f"ChatGPT API error {response.status_code}: {response.text}")

	data = response.json()
	response_text = ""
	output = data.get("output") or []
	if output:
		content = output[0].get("content") or []
		segments = [item.get("text", "") for item in content if item.get("type") == "output_text"]
		response_text = "".join(segments).strip()

	return {"response_text": response_text, "model_version": MODEL_NAME}
