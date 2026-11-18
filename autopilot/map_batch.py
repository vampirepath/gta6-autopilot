"""Make many map videos in one go and schedule them on YouTube.

    python -m autopilot.map_batch 20 20      -> 20 videos, one goes live every 20 minutes
"""
import json
import re
import subprocess
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .common import ROOT, env, log
from . import leonida_map as LM
from . import map_writer as MW
from . import mapvideo as MV
from . import uploaders

IST = timezone(timedelta(hours=5, minutes=30))


def tg(text):
    try:
        import requests
        requests.post(f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/sendMessage",
                      data={"chat_id": env("TELEGRAM_CHAT_ID"), "text": text}, timeout=30)
    except Exception as e:
        log.warning("telegram: %s", e)


def commit(msg):
    subprocess.run(f'git add -f state/ scripts/auto/ && git commit -qm "{msg}" && '
                   'git pull -q --rebase --autostash && git push -q', shell=True)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    gap = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    try:
        from .news import fetch_stories
        news = [s["title"] for s in fetch_stories()][:40]
    except Exception as e:
        log.warning("news failed: %s", e)
        news = []
    ideas = MW.topics(n + 3, news)
    log.info("topics:\n%s", "\n".join(ideas))
    themes = list(LM.THEMES)
    start = datetime.now(timezone.utc) + timedelta(minutes=2)
    made = 0
    out_dir = ROOT / "output" / "batch"
    out_dir.mkdir(parents=True, exist_ok=True)
    (ROOT / "scripts" / "auto").mkdir(parents=True, exist_ok=True)
    for idea in ideas:
        if made >= n:
            break
        try:
            spec = MW.write_spec(idea, news)
            import random
            spec["theme"] = themes[made % len(themes)]
            spec["style"] = {"layout": ["flat", "tilt", "photo"][made % 3],
                             "card_in": random.choice(MV.STYLE_CHOICES["card_in"]),
                             "caps": random.choice(MV.STYLE_CHOICES["caps"]),
                             "flash": random.random() < .5}
            spec["music"] = random.choice(["synthwave", "trap"])
            slug = re.sub(r"[^a-z0-9]+", "_", spec["title"].lower()).strip("_")[:40] or f"video{made}"
            sp = ROOT / "scripts" / "auto" / f"{slug}.json"
            sp.write_text(json.dumps(spec, indent=2))
            out = out_dir / f"{slug}.mp4"
            MV.build(sp, out)
            when = start + timedelta(minutes=gap * made)
            publish_at = None if made == 0 else when.strftime("%Y-%m-%dT%H:%M:%SZ")
            vid = uploaders.youtube(out, spec["yt_title"], spec["description"], spec.get("tags", []), publish_at)
            local = when.astimezone(IST).strftime("%I:%M %p")
            tg(f"{'✅ Live' if made == 0 else '🕒 Scheduled ' + local}: {spec['yt_title']}\nhttps://youtube.com/shorts/{vid}")
            MW.remember(spec["title"])
            made += 1
            commit(f"map batch: {spec['title'][:50]}")
        except Exception as e:
            log.error("video failed (%s): %s", idea, e)
            traceback.print_exc()
    tg(f"🗺 Map batch done: {made} videos made, one goes live every {gap} min.")


if __name__ == "__main__":
    main()
