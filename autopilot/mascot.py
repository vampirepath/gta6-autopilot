"""Channel mascot – ONE original cartoon character (consistent across videos), generated once with free AI
(Pollinations), background removed with rembg. Emotions are shown with a 3D emoji bubble next to it,
so the character always looks the same.

  python -m autopilot.mascot             make 4 candidates (debug/mascot_sheet.jpg) if none exist
  python -m autopilot.mascot --redo      make 4 new candidates
Pick the best one with  mascot_pick: <0-3>  in config.yaml.
"""
import sys
import time
import urllib.parse
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter

from .common import ROOT, config, log
from .library import STILLS_DIR

POSE_ICON = {"shocked": "shocked", "pointing": "exclamation", "laughing": "party", "thinking": "thinking",
             "money": "money_wings", "thumbsup": "check", "angry": "angry"}
PROMPT = ("cute 3D cartoon mascot character, a cool pink flamingo wearing big neon purple sunglasses and an open "
          "teal Hawaiian shirt with palm tree print and a gold chain, confident pose, Pixar style render, full body, "
          "centered, plain pure white background, no text")
SEEDS = [101, 202, 303, 404]
ICON_DIR = ROOT / "assets" / "icons"


def cand_path(i: int) -> Path:
    return STILLS_DIR / f"mascot_cand{i}.png"


def _remove_bg(img: Image.Image) -> Image.Image:
    try:
        from rembg import remove
        return remove(img)
    except Exception as e:
        log.warning("rembg unavailable (%s) – simple white key", e)
        img = img.convert("RGBA")
        px = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = px[x, y]
                if r > 235 and g > 235 and b > 235:
                    px[x, y] = (r, g, b, 0)
        return img


def generate(redo=False):
    for i, seed in enumerate(SEEDS):
        p = cand_path(i)
        if p.exists() and not redo:
            continue
        url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(PROMPT) +
               f"?width=1024&height=1024&nologo=true&seed={seed}&model=flux")
        for attempt in range(4):
            try:
                r = requests.get(url, timeout=180)
                if r.status_code in (402, 429, 503):
                    log.info("image service busy (%s) – waiting", r.status_code)
                    time.sleep(40 * (attempt + 1))
                    continue
                r.raise_for_status()
                img = Image.open(BytesIO(r.content)).convert("RGB")
                img = img.crop((0, 0, img.width, int(img.height * 0.94)))
                cut = _remove_bg(img)
                if cut.getbbox():
                    cut = cut.crop(cut.getbbox())
                cut.thumbnail((900, 900))
                cut.save(p)
                log.info("mascot candidate %d ready", i)
                break
            except Exception as e:
                log.warning("mascot candidate %d failed: %s", i, e)
                time.sleep(20)
        time.sleep(25)            # be gentle with the free service
    cands = [cand_path(i) for i in range(len(SEEDS)) if cand_path(i).exists()]
    if cands:
        sheet = Image.new("RGBA", (300 * len(cands), 340), (30, 20, 50, 255))
        d = ImageDraw.Draw(sheet)
        for k, pp in enumerate(cands):
            im = Image.open(pp).convert("RGBA"); im.thumbnail((280, 300))
            sheet.alpha_composite(im, (k * 300 + (300 - im.width) // 2, 320 - im.height))
            d.text((k * 300 + 8, 6), str(int(pp.stem[-1])), fill=(255, 255, 0, 255))
        (ROOT / "debug").mkdir(exist_ok=True)
        sheet.convert("RGB").save(ROOT / "debug" / "mascot_sheet.jpg", quality=85)


def base_path() -> Path | None:
    pick = int(config().get("mascot_pick", 0))
    for i in [pick] + list(range(len(SEEDS))):
        if cand_path(i).exists():
            return cand_path(i)
    return None


def available() -> list[str]:
    return list(POSE_ICON) if base_path() else []


def pose_path(pose: str, work: Path | None = None) -> Path:
    """Mascot + emotion bubble with a 3D emoji (built on the fly, cached)."""
    out = (work or STILLS_DIR) / f"mascot_pose_{pose}.png"
    if out.exists():
        return out
    base = Image.open(base_path()).convert("RGBA")
    base.thumbnail((700, 900))
    bub = 260
    W, H = base.width + bub // 2, base.height + bub // 2
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.alpha_composite(base, (0, H - base.height))
    # bubble
    bx, by = W - bub - 10, 10
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    gd.ellipse((bx - 10, by - 10, bx + bub + 10, by + bub + 10), fill=(214, 80, 255, 160))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(img)
    d.ellipse((bx, by, bx + bub, by + bub), fill=(255, 255, 255, 255), outline=(150, 26, 190, 255), width=8)
    d.polygon([(bx + bub * 0.25, by + bub * 0.85), (bx + bub * 0.05, by + bub * 1.15), (bx + bub * 0.45, by + bub * 0.95)],
              fill=(255, 255, 255, 255))
    ic = Image.open(ICON_DIR / f"{POSE_ICON.get(pose, 'exclamation')}.png").convert("RGBA").resize((int(bub * 0.72),) * 2)
    img.alpha_composite(ic, (bx + (bub - ic.width) // 2, by + (bub - ic.height) // 2))
    img.save(out)
    return out


if __name__ == "__main__":
    generate(redo="--redo" in sys.argv)
