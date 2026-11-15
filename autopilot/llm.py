"""Free AI brain: Google Gemini API (free tier, no card needed).

Uses plain HTTPS so there's nothing extra to install. Tries the models in
config `gemini_models` in order, and waits + retries when the free tier says "slow down".
"""
import time

import requests

from .common import config, env, log

URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"


def ask(prompt: str, system: str = "", image_jpeg_b64: str | None = None, json_out=True,
        max_tokens=2048, retries: int = 6) -> str:
    models = config().get("gemini_models") or ["gemini-flash-latest"]
    parts = []
    if image_jpeg_b64:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_jpeg_b64}})
    parts.append({"text": prompt})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.9}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if json_out:
        body["generationConfig"]["responseMimeType"] = "application/json"
    last = None
    for model in models:
        for attempt in range(retries):
            try:
                r = requests.post(URL.format(m=model), json=body, timeout=120,
                                  headers={"x-goog-api-key": env("GEMINI_API_KEY")})
            except requests.RequestException as e:
                last = e
                time.sleep(5)
                continue
            if r.status_code == 429 or r.status_code >= 500:   # free-tier speed limit / busy
                wait = 20 * (attempt + 1) if retries > 2 else 8
                log.info("gemini %s busy (%s), waiting %ss", model, r.status_code, wait)
                time.sleep(wait)
                last = r.text[:300]
                continue
            if r.status_code == 404:                           # model name retired -> next one
                last = f"{model} not found"
                break
            if r.status_code >= 400:
                raise RuntimeError(f"Gemini error {r.status_code}: {r.text[:400]}")
            data = r.json()
            try:
                return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
            except (KeyError, IndexError):
                last = str(data)[:300]
                break
    raise RuntimeError(f"Gemini failed: {last}")
