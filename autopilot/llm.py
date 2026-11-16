"""Free AI brain: Google Gemini API (free tier, no card needed).

Uses plain HTTPS so there's nothing extra to install. Tries the models in
config `gemini_models` in order, and waits + retries when the free tier says "slow down".
"""
import time

import requests

from .common import config, env, log

URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"


def _call(model: str, prompt: str, system: str, image_jpeg_b64, json_out: bool, max_tokens: int):
    gemma = model.startswith("gemma")
    parts = []
    if image_jpeg_b64:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_jpeg_b64}})
    text = prompt
    if gemma and system:                     # Gemma has no system instruction / JSON mode
        text = f"{system}\n\n---\n\n{prompt}\n\nReply with the JSON only."
    parts.append({"text": text})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.9}}
    if system and not gemma:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if json_out and not gemma:
        body["generationConfig"]["responseMimeType"] = "application/json"
    return requests.post(URL.format(m=model), json=body, timeout=180,
                         headers={"x-goog-api-key": env("GEMINI_API_KEY")})


def ask(prompt: str, system: str = "", image_jpeg_b64: str | None = None, json_out=True,
        max_tokens=8192, retries: int = 6) -> str:
    """Try each model; on free-tier limits move to the next one. If all are limited, wait and go round again."""
    models = config().get("gemini_models") or ["gemini-flash-latest"]
    last = None
    rounds = 3 if retries > 2 else 1
    for rnd in range(rounds):
        for model in models:
            for attempt in range(2):
                try:
                    r = _call(model, prompt, system, image_jpeg_b64, json_out, max_tokens)
                except requests.RequestException as e:
                    last = e
                    time.sleep(5)
                    continue
                if r.status_code in (404, 400) and model.startswith("gemma") and image_jpeg_b64:
                    last = f"{model} can't see images"
                    break
                if r.status_code == 404:
                    last = f"{model} not found"
                    break
                if r.status_code == 429 or r.status_code >= 500:
                    last = f"{model} limited/busy ({r.status_code})"
                    log.info("gemini %s %s – trying next", model, r.status_code)
                    time.sleep(6)
                    break                         # next model
                if r.status_code >= 400:
                    last = f"{model} error {r.status_code}: {r.text[:200]}"
                    break
                data = r.json()
                try:
                    text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]
                                   if not p.get("thought"))
                except (KeyError, IndexError):
                    last = str(data)[:300]
                    break
                if text.strip():
                    if model != models[0]:
                        log.info("used backup model %s", model)
                    return text
                last = f"{model} returned empty text"
                break
        if rnd < rounds - 1:
            log.info("all models busy – waiting 60 s (round %d)", rnd + 1)
            time.sleep(60)
    raise RuntimeError(f"Gemini failed: {last}")
