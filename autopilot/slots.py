"""Prints the post slot that is due now (India time), or nothing.

GitHub's timer often starts runs late or skips them, so the workflow wakes up
every 30 minutes and asks this script. A slot is due when its time has passed
and no run has claimed it yet (state/last_slot.txt). Only the latest slot
counts, so a long GitHub outage never causes a burst of back-to-back posts.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

IST = timezone(timedelta(hours=5, minutes=30))
ROOT = Path(__file__).resolve().parent.parent


def due(now=None) -> str:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    times = cfg.get("post_times") or ["09:13", "12:43", "16:13", "19:43", "21:43", "23:43"]
    now = now or datetime.now(IST)
    cands = []
    for day in (now.date() - timedelta(days=1), now.date()):
        for t in times:
            h, m = map(int, t.split(":"))
            dt = datetime(day.year, day.month, day.day, h, m, tzinfo=IST)
            if dt <= now:
                cands.append(dt)
    latest = max(cands).strftime("%Y-%m-%dT%H:%M")
    last = ROOT / "state" / "last_slot.txt"
    claimed = last.read_text().strip() if last.exists() else ""
    return "" if claimed >= latest else latest


if __name__ == "__main__":
    print(due())
