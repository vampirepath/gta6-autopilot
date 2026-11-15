"""Clip library – turns official videos into short 9:16 background clips, tagged by AI.

  python -m autopilot.library            download sources + cut + tag
  python -m autopilot.library --retag    re-tag existing clips only

You can also drop your own .mp4 files (e.g. your own gameplay later) into
library/inbox/ – they get cut and tagged on the next run.
"""
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

import time

from .common import CLIPS_DIR, LIB_DIR, LIB_INDEX, ROOT, log
from .llm import ask

TAGS = ["jason", "lucia", "jason_and_lucia", "city_skyline", "beach", "car_driving",
        "police_chase", "robbery_action", "boat_water", "nightlife_party", "swamp_wildlife",
        "crowd_people", "social_media", "interior_home", "aerial_view", "sunset", "any"]

SRC_DIR = LIB_DIR / "sources"
INBOX = LIB_DIR / "inbox"
for d in (SRC_DIR, INBOX):
    d.mkdir(parents=True, exist_ok=True)


def load_index() -> list[dict]:
    if LIB_INDEX.exists():
        return json.loads(LIB_INDEX.read_text())
    return []


def save_index(idx: list[dict]):
    LIB_INDEX.write_text(json.dumps(idx, indent=1))


# ---------------- 1. download --------------------------------------------
def download_sources():
    import yt_dlp
    lines = [l.strip() for l in (ROOT / "library_sources.txt").read_text().splitlines()
             if l.strip() and not l.startswith("#")]
    opts = {"format": "bv*[height<=1080][ext=mp4]/bv*[height<=1080]", "quiet": True,
            "outtmpl": str(SRC_DIR / "%(id)s.%(ext)s"), "noplaylist": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        for line in lines:
            try:
                if line.lower().split("?")[0].endswith(".mp4"):      # direct file (e.g. Rockstar CDN)
                    import requests
                    name = "rockstar_" + re.sub(r"[^A-Za-z0-9]", "_", line.split("/v4/")[-1])[:60]
                    dst = SRC_DIR / (name.removesuffix("_mp4") + ".mp4")
                    if dst.exists():
                        continue
                    log.info("downloading %s", line)
                    with requests.get(line, stream=True, timeout=60,
                                      headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.rockstargames.com/"}) as r:
                        r.raise_for_status()
                        with open(dst, "wb") as f:
                            for chunk in r.iter_content(1 << 20):
                                f.write(chunk)
                    continue
                if line.lower().startswith("search:"):
                    q = line.split(":", 1)[1].strip()
                    res = ydl.extract_info(f"ytsearch8:{q}", download=False)
                    hits = [e for e in res["entries"] if (e.get("channel") or "") == "Rockstar Games"]
                    if not hits:
                        log.warning("no official Rockstar video found for: %s", q)
                        continue
                    url = hits[0]["webpage_url"]
                else:
                    url = line
                vid = ydl.extract_info(url, download=False)["id"]
                if any(SRC_DIR.glob(f"{vid}.*")):
                    continue
                log.info("downloading %s", url)
                ydl.download([url])
            except Exception as e:
                log.warning("download failed for %s: %s", line, e)


# ---------------- 2. cut into scenes -------------------------------------
def scenes(path: Path) -> list[tuple[float, float]]:
    from scenedetect import ContentDetector, detect
    found = detect(str(path), ContentDetector(threshold=27))
    out = []
    for a, b in found:
        s, e = a.get_seconds(), b.get_seconds()
        while e - s >= 1.6:                      # split long shots into ≤5 s pieces
            out.append((s + 0.1, min(s + 5, e) - 0.1))
            s += 5
    return out


def cut(src: Path, start: float, end: float, dst: Path):
    """Center-crop to 9:16, 1080x1920, 30 fps, no audio (trailer music is copyrighted)."""
    vf = ("crop='min(iw,ih*9/16)':ih,scale=1080:1920:flags=lanczos,"
          "setsar=1,fps=30,eq=contrast=1.05:saturation=1.1")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.2f}", "-to", f"{end:.2f}",
                    "-i", str(src), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-pix_fmt", "yuv420p", str(dst)], check=True)


def process_new_sources(idx: list[dict]) -> list[dict]:
    done = {c["source"] for c in idx}
    for src in list(SRC_DIR.glob("*.mp4")) + list(SRC_DIR.glob("*.webm")) + list(INBOX.glob("*.mp4")):
        if src.name in done:
            continue
        log.info("cutting %s", src.name)
        stem = re.sub(r"[^A-Za-z0-9_-]", "_", src.stem)
        for n, (s, e) in enumerate(scenes(src)):
            dst = CLIPS_DIR / f"{stem}_{n:04d}.mp4"
            try:
                cut(src, s, e, dst)
            except subprocess.CalledProcessError:
                continue
            idx.append({"file": dst.name, "source": src.name, "dur": round(e - s, 2),
                        "tags": [], "ok": True})
        save_index(idx)
    return idx


# ---------------- 3. AI tagging -------------------------------------------
def _frame_b64(clip: Path) -> str:
    jpg = subprocess.run(["ffmpeg", "-v", "error", "-ss", "0.6", "-i", str(clip), "-frames:v", "1",
                          "-vf", "scale=360:-1", "-f", "image2", "-c:v", "mjpeg", "-"],
                         capture_output=True, check=True).stdout
    return base64.b64encode(jpg).decode()


def tag_clips(idx: list[dict], retag=False):
    todo = [c for c in idx if retag or not c["tags"]][:400]   # free tier: max 400 per run
    log.info("tagging %d clips", len(todo))
    t0, fails = time.time(), 0
    prompt = ("This is a frame from a GTA 6 video. Reply ONLY JSON: "
              '{"tags": [1-3 tags from ' + json.dumps(TAGS) + "], "
              '"text_card": true if the frame is mostly a logo, title text, black screen or date card, '
              '"graphic": true if it shows blood/gore or a gun pointed at someone up close}')
    for i, c in enumerate(todo, 1):
        if time.time() - t0 > 25 * 60 or fails >= 6:
            log.warning("stopping tagging early (time limit or free-tier limit) – %d left untagged; "
                        "they are still used as general clips. Run the build again tomorrow to tag them.",
                        len(todo) - i + 1)
            break
        try:
            raw = ask(prompt, image_jpeg_b64=_frame_b64(CLIPS_DIR / c["file"]), max_tokens=200, retries=2)
            d = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
            time.sleep(4)   # stay under the free-tier speed limit
            c["tags"] = [t for t in d.get("tags", []) if t in TAGS] or ["any"]
            c["ok"] = not d.get("text_card", False)
            c["graphic"] = bool(d.get("graphic", False))
            fails = 0
        except Exception as e:
            log.warning("tag failed %s: %s", c["file"], e)
            fails += 1
        if i % 20 == 0:
            save_index(idx)
            log.info("  tagged %d/%d", i, len(todo))
    save_index(idx)


def build(retag=False):
    idx = load_index()
    if not retag:
        download_sources()
        idx = process_new_sources(idx)
    tag_clips(idx, retag=retag)
    usable = sum(1 for c in idx if c.get("ok"))
    log.info("library ready: %d usable clips", usable)


if __name__ == "__main__":
    build(retag="--retag" in sys.argv)
