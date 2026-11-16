"""Step 3 – voiceover with exact word timings.

ElevenLabs is used when ELEVENLABS_API_KEY is set (best quality). If the key is missing,
the monthly credits run out, or the API fails, it falls back to free Microsoft Edge voices
automatically – so the channel never stops posting.
"""
import asyncio
import base64
import json
import subprocess

import requests

from .common import config, env, log


def duration(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


# ---------------- ElevenLabs ----------------------------------------------------
def _elevenlabs(text: str, mp3: str) -> list[dict] | None:
    key = env("ELEVENLABS_API_KEY")
    if not key:
        return None
    cfg = config()
    el = cfg.get("elevenlabs", {})
    voice_id = el.get("voice_id", "nPczCjzI2devNBz1zQrb")
    try:
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps",
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": key, "Content-Type": "application/json"},
            json={"text": text, "model_id": el.get("model", "eleven_multilingual_v2"),
                  "voice_settings": {"stability": el.get("stability", 0.4),
                                     "similarity_boost": el.get("similarity", 0.8),
                                     "style": el.get("style", 0.35), "use_speaker_boost": True,
                                     "speed": el.get("speed", 1.08)}},
            timeout=180)
    except requests.RequestException as e:
        log.warning("ElevenLabs request failed (%s) – using free voice", e)
        return None
    if r.status_code != 200:
        log.warning("ElevenLabs error %s: %s – using free voice", r.status_code, r.text[:300])
        return None
    data = r.json()
    with open(mp3, "wb") as f:
        f.write(base64.b64decode(data["audio_base64"]))
    al = data.get("alignment") or data.get("normalized_alignment")
    chars, starts, ends = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    words, cur, ws, we, ci0 = [], "", None, None, 0
    for i, (c, s, e) in enumerate(zip(chars, starts, ends)):
        if c.isspace():
            if cur:
                words.append({"w": cur, "start": ws, "end": we, "ci": ci0})
                cur = ""
            continue
        if not cur:
            ws, ci0 = s, i
        cur += c
        we = e
    if cur:
        words.append({"w": cur, "start": ws, "end": we, "ci": ci0})
    log.info("voice: ElevenLabs (%d chars)", len(text))
    return words


# ---------------- Edge TTS (free fallback) -------------------------------------
async def _edge_async(text: str, mp3: str) -> list[dict]:
    import edge_tts
    cfg = config()
    com = edge_tts.Communicate(text, cfg["voice"], rate=cfg["voice_rate"],
                               pitch=cfg["voice_pitch"], boundary="WordBoundary")
    words = []
    with open(mp3, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({"w": chunk["text"], "start": chunk["offset"] / 1e7,
                              "end": (chunk["offset"] + chunk["duration"]) / 1e7})
    log.info("voice: Edge TTS (%s)", cfg["voice"])
    return words


def make_voice(lines: list[dict], mp3: str) -> tuple[list[dict], float]:
    """Speak the whole script in one go and give every line a start/end time."""
    text = " ".join(l["text"].strip() for l in lines)
    words = _elevenlabs(text, mp3)
    exact = words is not None
    if not exact:
        words = asyncio.run(_edge_async(text, mp3))
    if not words:
        raise RuntimeError("voice returned no word timings")
    total = duration(mp3)

    if exact:   # ElevenLabs: map lines by character position (exact)
        pos = 0
        for l in lines:
            a, b = pos, pos + len(l["text"].strip())
            inside = [w for w in words if a <= w["ci"] < b] or [min(words, key=lambda w: abs(w["ci"] - a))]
            l["start"], l["end"] = inside[0]["start"], inside[-1]["end"]
            pos = b + 1
    else:       # Edge: map lines by counting letters
        alnum = lambda s: sum(c.isalnum() for c in s)
        cum, acc = [], 0
        for w in words:
            acc += alnum(w["w"])
            cum.append(acc)
        target, i = 0, 0
        for l in lines:
            target += alnum(l["text"])
            j = i
            while j < len(words) - 1 and cum[j] < target - 1:
                j += 1
            l["start"], l["end"] = words[min(i, len(words) - 1)]["start"], words[j]["end"]
            i = j + 1
    for a, b in zip(lines, lines[1:]):   # no gaps between visuals
        a["end"] = b["start"]
    lines[0]["start"], lines[-1]["end"] = 0.0, total
    return words, total
