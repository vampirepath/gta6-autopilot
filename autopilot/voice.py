"""Step 3 – free AI voiceover (Microsoft Edge voices) with exact word timings for captions."""
import asyncio
import json
import subprocess

import edge_tts

from .common import config


async def _speak(text: str, mp3: str) -> list[dict]:
    cfg = config()
    com = edge_tts.Communicate(text, cfg["voice"], rate=cfg["voice_rate"],
                               pitch=cfg["voice_pitch"], boundary="WordBoundary")
    words = []
    with open(mp3, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({"w": chunk["text"],
                              "start": chunk["offset"] / 1e7,
                              "end": (chunk["offset"] + chunk["duration"]) / 1e7})
    return words


def duration(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def make_voice(lines: list[dict], mp3: str) -> tuple[list[dict], float]:
    """Speak the whole script in one go (natural flow) and map words back to lines."""
    text = " ".join(l["text"].strip() for l in lines)
    words = asyncio.run(_speak(text, mp3))
    total = duration(mp3)
    if not words:
        raise RuntimeError("voice returned no word timings")
    # map lines to words by counting letters (robust to how the voice splits words)
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
