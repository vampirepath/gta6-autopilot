"""Approve videos from your phone with Telegram.

Each new Short is sent to your Telegram with two buttons:
   ✅ Post now   -> uploads to YouTube, Instagram, Facebook
   🗑 Skip       -> throws it away
If you don't tap anything within `review_timeout_minutes`, the setting
`on_timeout` decides (post or skip) – so the channel keeps running while you sleep.
"""
import json
import time

import requests

from .common import config, env, log


def _api(method: str, **kw):
    try:
        return requests.post(f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/{method}",
                             timeout=120, **kw).json()
    except Exception as e:
        log.warning("telegram %s failed: %s", method, e)
        return {}


def _latest_offset() -> int:
    upd = _api("getUpdates", data={"offset": -1, "timeout": 0}).get("result", [])
    return upd[-1]["update_id"] + 1 if upd else 0


def review(video, title: str) -> str:
    """Send the video, wait for a button press. Returns 'post' or 'skip'."""
    cfg = config()
    if not env("TELEGRAM_BOT_TOKEN"):
        return "post"
    chat = env("TELEGRAM_CHAT_ID")
    mins, default = cfg.get("review_timeout_minutes", 40), cfg.get("on_timeout", "post")
    offset = _latest_offset()
    kb = {"inline_keyboard": [[{"text": "✅ Post now", "callback_data": f"post:{video.stem}"},
                               {"text": "🗑 Skip", "callback_data": f"skip:{video.stem}"}]]}
    cap = f"{title}\n\nNo answer in {mins} min = {'auto-post' if default == 'post' else 'skip'}."
    with open(video, "rb") as f:
        r = _api("sendVideo", data={"chat_id": chat, "caption": cap[:1000], "supports_streaming": "true",
                                    "reply_markup": json.dumps(kb)}, files={"video": f})
    if not r.get("ok"):
        log.warning("telegram sendVideo failed: %s", r)
        return default
    deadline = time.time() + mins * 60
    while time.time() < deadline:
        upd = _api("getUpdates", data={"offset": offset, "timeout": 50,
                                       "allowed_updates": json.dumps(["callback_query"])}).get("result", [])
        for u in upd:
            offset = u["update_id"] + 1
            cb = u.get("callback_query")
            if not cb or str(cb["message"]["chat"]["id"]) != chat:
                continue
            action, vid = cb["data"].split(":", 1)
            if vid != video.stem:
                continue
            _api("answerCallbackQuery", data={"callback_query_id": cb["id"],
                                              "text": "Posting…" if action == "post" else "Skipped"})
            return action
    _api("sendMessage", data={"chat_id": chat, "text": f"⏰ No answer – {default} for: {title}"})
    return default
