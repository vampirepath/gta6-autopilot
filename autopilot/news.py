"""Step 1 – find the freshest GTA 6 stories nobody on the channel has covered yet."""
import hashlib
import re
import time
from difflib import SequenceMatcher

import feedparser
import requests
import trafilatura

from .common import config, log, recent_titles, story_used

UA = {"User-Agent": "Mozilla/5.0 (GTA6-news-bot; +https://vampirepath.com)"}


def _key(title: str) -> str:
    norm = re.sub(r"[^a-z0-9 ]", "", title.lower())
    return hashlib.sha1(norm.encode()).hexdigest()[:16]


def _clean(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def fetch_stories() -> list[dict]:
    cfg = config()
    must = [w.lower() for w in cfg["must_contain_any"]]
    skip = [w.lower() for w in cfg["skip_if_contains"]]
    out, now = [], time.time()
    for url in cfg["feeds"]:
        try:
            raw = requests.get(url, headers=UA, timeout=20).content
            feed = feedparser.parse(raw)
        except Exception as e:
            log.warning("feed failed %s: %s", url, e)
            continue
        for e in feed.entries[:30]:
            title = _clean(e.get("title", ""))
            summary = _clean(e.get("summary", ""))[:1500]
            text = f"{title} {summary}".lower()
            if not any(w in text for w in must) or any(w in text for w in skip):
                continue
            ts = e.get("published_parsed") or e.get("updated_parsed")
            age_h = (now - time.mktime(ts)) / 3600 if ts else 24
            if age_h > 72:
                continue
            out.append({
                "title": title, "summary": summary, "url": e.get("link", ""),
                "source": feed.feed.get("title", url), "age_h": max(age_h, 0),
                "reddit": "reddit.com" in url,
            })
    log.info("fetched %d candidate stories", len(out))
    return out


def _too_similar(title: str, previous: list[str]) -> bool:
    t = title.lower()
    return any(SequenceMatcher(None, t, p.lower()).ratio() > 0.6 for p in previous)


def rank(stories: list[dict]) -> list[dict]:
    """Newer is better; a topic covered by several sources is hotter."""
    seen, ranked = set(), []
    prev = recent_titles(40)
    for s in stories:
        k = _key(s["title"])
        if k in seen or story_used(k) or _too_similar(s["title"], prev):
            continue
        seen.add(k)
        s["key"] = k
        buzz = sum(1 for o in stories if o is not s and
                   SequenceMatcher(None, s["title"].lower(), o["title"].lower()).ratio() > 0.45)
        s["score"] = 100 / (1 + s["age_h"]) + 15 * buzz + (5 if not s["reddit"] else 0)
        ranked.append(s)
    ranked.sort(key=lambda s: s["score"], reverse=True)
    return ranked


def article_text(story: dict) -> str:
    """Grab the article body so the script has real facts, not just a headline."""
    if story["reddit"] or "news.google.com" in story["url"]:
        return story["summary"]
    try:
        html = requests.get(story["url"], headers=UA, timeout=20).text
        body = trafilatura.extract(html) or ""
        return (body or story["summary"])[:6000]
    except Exception:
        return story["summary"]


def pick_story() -> dict | None:
    ranked = rank(fetch_stories())
    if not ranked:
        return None
    top = ranked[0]
    # related headlines give Claude extra context ("what others are saying")
    top["related"] = [s["title"] for s in ranked[1:8]]
    top["body"] = article_text(top)
    return top
