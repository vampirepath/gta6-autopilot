"""Last-resort visuals: free AI images (Pollinations – no key, no cost).
Prompts are kept generic (no real game characters, logos or real people) to avoid copyright problems."""
import random
import urllib.parse
from pathlib import Path

import requests
from PIL import Image

from .common import log

STYLE = ("cinematic photo, vertical 9:16, dramatic neon lighting, hyper-detailed, Miami / Florida vibe, "
         "no text, no logos, no watermark")


def ai_image(prompt: str, out: Path) -> Path | None:
    safe = prompt.replace("GTA", "").replace("Grand Theft Auto", "").strip()
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(f"{safe}, {STYLE}") +
           f"?width=1080&height=1920&nologo=true&seed={random.randint(1, 10**6)}&model=flux")
    for _ in range(2):
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                out.write_bytes(r.content)
                im = Image.open(out).convert("RGB")
                k = max(1080 / im.width, 1920 / im.height) * 1.0
                im.resize((round(im.width * k), round(im.height * k))).save(out, quality=90)
                return out
        except Exception as e:
            log.warning("AI image failed: %s", e)
    return None
