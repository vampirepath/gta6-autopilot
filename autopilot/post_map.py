"""Post a finished map video:  python -m autopilot.post_map <video.mp4> <spec.json> <now|review>"""
import json
import sys
from pathlib import Path

from .common import log
from . import uploaders


def main():
    video, spec, mode = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text()), sys.argv[3]
    if mode == "review":
        from .review import review
        if review(video, spec["yt_title"]) != "post":
            log.info("skipped by review")
            return
    vid = uploaders.youtube(video, spec["yt_title"], spec["description"], spec.get("tags", []))
    try:
        from .review import _api
        from .common import env
        _api("sendMessage", data={"chat_id": env("TELEGRAM_CHAT_ID"),
                                  "text": f"✅ Posted on YouTube: {spec['yt_title']}\nhttps://youtube.com/shorts/{vid}"})
    except Exception as e:
        log.warning("telegram notice failed: %s", e)


if __name__ == "__main__":
    main()
