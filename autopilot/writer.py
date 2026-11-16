"""Step 2 – the AI writes the Short in the style of top GTA news channels (story-driven investigation)."""
import json
import re

from .common import config, log
from .llm import ask

LANG = {
    "en": "Write the spoken lines in simple, punchy spoken English.",
    "hi": "Write the spoken lines in casual spoken Hindi (Devanagari script), like Indian gaming YouTubers talk. "
          "Keep game names, brands and English gaming words in English (GTA 6, Rockstar, leak, trailer, update). "
          "Write numbers and dates as digits.",
}

SYSTEM = """You write viral 50–60 second YouTube Shorts scripts for a faceless GTA 6 news channel.

THE STYLE (copy it exactly – learned from a top GTA news channel):
1. HOOK (line 1): a mystery or shock about ONE specific thing, max 12 words.
   e.g. "GTA 6's biggest leaker just disappeared without a trace."
2. STORY, not a list: tell what happened in time order with EXACT dates and numbers from the source
   ("On August 27th…", "That same day…", "Three weeks later…").
3. TURNS: build tension with "But…", "And then…", "Here's the twist…".
4. PROOF: mention who reported or confirmed it ("PC Gamer reports…", "Take-Two filed…").
5. PAYOFF: the reveal / what it means for players.
6. ENDING: one short punchy line or rhetorical question. No "like and subscribe", no "comment below".
- Short sentences (5–14 words). One idea per line. Conversational, confident, a bit dramatic.
- Use ONLY facts from the source material. Never invent dates, numbers, names or quotes.
- Leaks/rumours/insider claims MUST be labelled ("according to a rumour", "an insider claims") and the
  script must say when something is not confirmed.
- Never explain how to get leaked or pirated content.
- 12–16 lines, about {words} words total.
{lang}

ON-SCREEN LABELS (the purple text boxes):
- "label": 2–5 word UPPERCASE ENGLISH summary of the line's key fact ("NO UPDATE & NO LEAKS",
  "17TH & LAST LEAK", "LEAKS STARTED AUG 18"). Give a label to about 2 of every 3 lines; "" for the rest.
  Line 1 ALWAYS has a label (the hook question, e.g. "WHERE IS CYBERLEEK?").
- "big": true when the label is a date, money amount or big number that should fill the screen.

VISUALS for each line – "visual" is one of:
- "clip": gameplay background. Also give "tag" from: {tags}
- "article": show the news article screenshot (use for the 1–2 lines that cite the source; only if a source URL exists)

Return ONLY JSON:
{{
 "title": "YouTube title, max 70 chars, curiosity + 'GTA 6', no clickbait lies",
 "lines": [{{"text": "...", "visual": "clip", "tag": "...", "label": "...", "big": false}}],
 "description": "2-3 sentence description in English",
 "hashtags": ["#GTA6", "..."],
 "is_rumour": true/false
}}"""


def write_script(story: dict, tags: list[str]) -> dict:
    cfg = config()
    lang = cfg.get("language", "en")
    user = (f"SOURCE: {story['source']}\nHEADLINE: {story['title']}\nURL: {story['url'] or 'none'}\n\n"
            f"ARTICLE:\n{story['body']}\n\n"
            "OTHER GTA 6 HEADLINES PEOPLE ARE TALKING ABOUT TODAY:\n- " + "\n- ".join(story.get("related", [])))
    raw = ask(user, system=SYSTEM.format(words=cfg["target_words"], tags=", ".join(tags), lang=LANG.get(lang, LANG["en"])))
    data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
    lines = [l for l in data["lines"] if l.get("text", "").strip()]
    if len(lines) < 5:
        raise ValueError("script too short")
    can_article = bool(story.get("url")) and "news.google.com" not in story["url"] and "reddit.com" not in story["url"]
    for i, l in enumerate(lines):
        if l.get("tag") not in tags:
            l["tag"] = "any"
        if l.get("visual") != "article" or not can_article or i == 0:
            l["visual"] = "clip"
        l["label"] = (l.get("label") or "").strip().upper()[:40]
        l["big"] = bool(l.get("big"))
    if not lines[0]["label"]:
        lines[0]["label"] = data.get("title", "GTA 6 NEWS").upper()[:30]
    data["lines"] = lines
    data["title"] = data["title"][:95]
    log.info("script: %s (%d lines)", data["title"], len(lines))
    return data
