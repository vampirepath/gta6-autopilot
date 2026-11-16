"""The autopilot: news -> script -> voice -> video -> upload.

  python -m autopilot.run                 make videos_per_run videos (cron uses this)
  python -m autopilot.run --publish-ready upload everything waiting in output/ready/ (after review)
  python -m autopilot.run --topic "..."   make one video about a topic you type
"""
import json
import shutil
import sys
import time
import traceback
from pathlib import Path

from . import uploaders
from .common import (ROOT, POSTED_DIR, READY_DIR, WORK_DIR, config, env, log, mark_story, notify,
                     save_video, set_platform)
from .library import TAGS
from .news import pick_story
from .render import render
from .voice import make_voice
from .writer import write_script


def make_one(story: dict) -> Path:
    vid = time.strftime("%Y%m%d_%H%M%S")
    work = WORK_DIR / vid
    work.mkdir(parents=True, exist_ok=True)
    from .library import subjects as lib_subjects
    from .screenshot import article_photo
    photo = article_photo(story.get("url", ""), work)
    data = write_script(story, TAGS, lib_subjects(), has_photo=photo is not None)
    voice_mp3 = str(work / "voice.mp3")
    words, total = make_voice(data["lines"], voice_mp3)
    badge = "GTA 6 RUMOUR" if data.get("is_rumour") else "GTA 6 NEWS"
    article = None
    if any(l["visual"] == "article" for l in data["lines"]):
        from .screenshot import article_shots
        article = article_shots(story.get("url", ""), work)
    out = READY_DIR / f"{vid}.mp4"
    render(data["lines"], words, voice_mp3, total, badge, out, work, article=article, photo=photo)

    tags = [h.lstrip("#") for h in data.get("hashtags", [])]
    hashtags = " ".join(data.get("hashtags", ["#GTA6"]))
    meta = {
        "id": vid, "title": data["title"],
        "yt_title": data["title"] if "#shorts" in data["title"].lower() else f"{data['title']} #shorts",
        "description": f"{data['description']}\n\nSource: {story['source']}\n\n{hashtags}",
        "caption": f"{data['title']}\n\n{data['description']}\n\n{hashtags}",
        "tags": tags + ["GTA 6", "GTA VI", "GTA 6 news"],
        "script": " ".join(l["text"] for l in data["lines"]),
        "story_url": story["url"], "duration": round(total, 1),
    }
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    # preview sheet (every ~1.5 s) so the build can be checked without downloading the video
    try:
        import subprocess as sp
        dbg = ROOT / "debug"; dbg.mkdir(exist_ok=True)
        sp.run(["ffmpeg", "-y", "-v", "error", "-i", str(out), "-vf",
                "fps=2/3,scale=216:-1,tile=10x4", "-frames:v", "1", "-q:v", "5", str(dbg / "latest_sheet.jpg")], check=True)
        (dbg / "latest_script.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
    except Exception as e:
        log.warning("preview sheet failed: %s", e)
    save_video(vid, data["title"], str(out), meta)
    mark_story(story["key"], story["title"], story["url"])
    shutil.rmtree(work, ignore_errors=True)
    log.info("video ready: %s (%.1fs)", out.name, total)
    return out


def publish(video: Path):
    cfg = config()
    meta = json.loads(video.with_suffix(".json").read_text())
    done = []
    for name, enabled, fn in [
        ("youtube", cfg["upload_youtube"], lambda: uploaders.youtube(video, meta["yt_title"], meta["description"], meta["tags"])),
        ("instagram", cfg["upload_instagram"], lambda: uploaders.instagram(video, meta["caption"])),
        ("facebook", cfg["upload_facebook"], lambda: uploaders.facebook(video, meta["caption"])),
    ]:
        if not enabled or meta.get(name):
            continue
        try:
            meta[name] = fn()
            set_platform(meta["id"], name, meta[name])
            done.append(name)
        except Exception as e:
            log.error("%s upload failed: %s", name, e)
            notify(f"⚠️ {name} upload failed for '{meta['title']}': {e}")
        video.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    failed = [n for n, en in [("youtube", cfg["upload_youtube"]), ("instagram", cfg["upload_instagram"]),
                              ("facebook", cfg["upload_facebook"])] if en and not meta.get(n)]
    if not failed:   # everything posted -> move out of the ready folder
        for p in (video, video.with_suffix(".json")):
            shutil.move(str(p), POSTED_DIR / p.name)
    if done:
        yt = f"https://youtube.com/shorts/{meta['youtube']}" if meta.get("youtube") else ""
        notify(f"✅ Posted: {meta['title']}\n{', '.join(done)}\n{yt}")


def main():
    cfg = config()
    args = sys.argv[1:]
    if "--publish-ready" in args:
        for v in sorted(READY_DIR.glob("*.mp4")):
            publish(v)
        return
    if "--topic" in args:
        topic = args[args.index("--topic") + 1]
        stories = [{"title": topic, "summary": topic, "body": topic, "url": "", "source": "channel",
                    "key": f"manual-{time.time()}", "related": []}]
    else:
        stories = []
        for _ in range(cfg["videos_per_run"]):
            s = pick_story()
            if not s:
                break
            mark_story(s["key"], s["title"], s["url"])   # don't pick it twice in one run
            stories.append(s)
    if not stories:
        log.info("no new GTA 6 stories right now – nothing to do")
        return
    for s in stories:
        try:
            out = make_one(s)
            decision = "post"
            if cfg["review_mode"]:
                from .review import review
                decision = review(out, json.loads(out.with_suffix(".json").read_text())["title"])
            if decision == "post":
                publish(out)
            else:
                log.info("skipped by review: %s", out.name)
        except Exception as e:
            log.error("failed on '%s': %s\n%s", s["title"], e, traceback.format_exc())
            notify(f"❌ Autopilot failed on '{s['title']}': {e}")


if __name__ == "__main__":
    main()
