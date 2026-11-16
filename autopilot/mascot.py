"""Channel mascot – an original cartoon flamingo with a Vice City vibe, generated once with free AI
(Pollinations), background removed (rembg), saved as transparent PNG poses in the library.

  python -m autopilot.mascot          generate missing poses
  python -m autopilot.mascot --redo   regenerate all poses
"""
import random
import sys
import urllib.parse
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

from .common import ROOT, log
from .library import STILLS_DIR

POSES = {
    "shocked": "shocked face, eyes wide, both wings on cheeks, beak wide open",
    "pointing": "confidently pointing to the side with one wing, smirking",
    "laughing": "laughing hard, eyes closed, holding belly with wing",
    "thinking": "thinking, one wing on chin, one eyebrow raised, looking up",
    "money": "holding a fan of dollar bills in one wing, sly grin",
    "thumbsup": "giving a big thumbs up with a wing, winking",
    "angry": "angry, frowning, wings crossed, steam puffs",
}
BASE = ("cute 3D cartoon mascot character, a cool pink flamingo wearing neon purple sunglasses, an open "
        "teal Hawaiian shirt with palm trees, a gold chain, Pixar style render, full body, standing, "
        "centered, thick white outline, plain pure white background, no text")
SEED = 4242


def pose_path(pose: str) -> Path:
    return STILLS_DIR / f"mascot_{pose}.png"


def _remove_bg(img: Image.Image) -> Image.Image:
    try:
        from rembg import remove
        return remove(img)
    except Exception as e:                       # fallback: knock out near-white background
        log.warning("rembg unavailable (%s) – simple white key", e)
        img = img.convert("RGBA")
        px = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = px[x, y]
                if r > 235 and g > 235 and b > 235:
                    px[x, y] = (r, g, b, 0)
        return img


def generate(redo=False) -> list[Path]:
    made = []
    for pose, desc in POSES.items():
        p = pose_path(pose)
        if p.exists() and not redo:
            continue
        prompt = f"{BASE}, {desc}"
        url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) +
               f"?width=1024&height=1024&nologo=true&seed={SEED}&model=flux")
        try:
            r = requests.get(url, timeout=180)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content)).convert("RGB")
            img = img.crop((0, 0, img.width, int(img.height * 0.94)))     # drop watermark strip
            cut = _remove_bg(img)
            box = cut.getbbox()
            if box:
                cut = cut.crop(box)
            cut.thumbnail((900, 900))
            cut.save(p)
            made.append(p)
            log.info("mascot pose ready: %s", pose)
        except Exception as e:
            log.warning("mascot %s failed: %s", pose, e)
    # preview sheet for checking
    poses = [pose_path(x) for x in POSES if pose_path(x).exists()]
    if poses:
        sheet = Image.new("RGBA", (300 * len(poses), 320), (30, 20, 50, 255))
        for i, pp in enumerate(poses):
            im = Image.open(pp).convert("RGBA"); im.thumbnail((290, 300))
            sheet.alpha_composite(im, (i * 300 + (300 - im.width) // 2, 310 - im.height))
        (ROOT / "debug").mkdir(exist_ok=True)
        sheet.convert("RGB").save(ROOT / "debug" / "mascot_sheet.jpg", quality=85)
    return made


def available() -> list[str]:
    return [p for p in POSES if pose_path(p).exists()]


if __name__ == "__main__":
    generate(redo="--redo" in sys.argv)
