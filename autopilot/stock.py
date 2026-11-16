"""Real-life stock footage from Pexels (free licence – allowed in monetised videos, no credit required).
Needs the free PEXELS_API_KEY secret. Without it, this visual falls back to gameplay."""
import random
import subprocess
from pathlib import Path

import requests

from .common import env, log


def stock_clip(query: str, min_dur: float, out: Path) -> dict | None:
    key = env("PEXELS_API_KEY")
    if not key or not query.strip():
        return None
    try:
        r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key},
                         params={"query": query, "orientation": "portrait", "per_page": 15, "size": "medium"},
                         timeout=30)
        vids = [v for v in r.json().get("videos", []) if v.get("duration", 0) >= max(3, min_dur)]
        if not vids:
            r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key},
                             params={"query": query, "per_page": 15}, timeout=30)
            vids = [v for v in r.json().get("videos", []) if v.get("duration", 0) >= max(3, min_dur)]
        if not vids:
            return None
        v = random.choice(vids[:6])
        files = sorted([f for f in v["video_files"] if f.get("height") and f["height"] >= 720 and f.get("file_type") == "video/mp4"],
                       key=lambda f: f["height"])
        if not files:
            return None
        raw = out.with_suffix(".src.mp4")
        with requests.get(files[0]["link"], stream=True, timeout=120) as resp:
            resp.raise_for_status()
            with open(raw, "wb") as f:
                for chunk in resp.iter_content(1 << 20):
                    f.write(chunk)
        dur = min(v["duration"], 8)
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-t", f"{dur}", "-vf", vf, "-an",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)], check=True)
        raw.unlink(missing_ok=True)
        log.info("stock footage: '%s' (pexels %s)", query, v.get("id"))
        return {"file": str(out), "dur": float(dur), "abs": True}
    except Exception as e:
        log.warning("stock footage failed for '%s': %s", query, e)
        return None
