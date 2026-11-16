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
- 14–16 lines and AT LEAST {words} words total (about 55–60 seconds spoken). Shorter scripts are rejected.
{lang}

EVERYTHING MUST BE ON SCREEN – viewers watch on mute. Every line gets a visual that matches what is said.

"label" (every line, never empty): 2–5 word UPPERCASE ENGLISH summary of the line's key fact
("17TH & LAST LEAK", "LEAKS STARTED AUG 18", "$270,000 CASHED OUT"). Line 1's label is the hook question.
"big": true when the label is just a date / money / number.

"visual" – pick the BEST match for each line:
- "subject": an official Rockstar image/clip of a named character/place/vehicle. Use whenever the line
   mentions one. Set "subject" to one EXACT name from: {subjects}
- "stat": animated big number. Use for ANY number, price, date countdown, sales, size, percentage.
   Set "stat": {{"value": "$7.6 BILLION", "caption": "expected first-year revenue"}}
- "compare": two growing bars. Use when two things are compared.
   Set "compare": {{"a_label": "GTA 5 map", "a_value": "49", "b_label": "GTA 6 map", "b_value": "100", "unit": "sq km"}}
- "list": checklist that ticks in. Use when the line lists 2–4 things.
   Set "list": {{"title": "WHAT'S NEW", "items": ["Two playable leads", "Vice City", "Online at launch"]}}
- "quote": quote card. Use when someone is quoted. Set "quote": {{"text": "...", "by": "Take-Two CEO"}}
- "article": screenshot of the source article with the headline highlighted (1 line max, when citing the source{article_note})
- "photo": the main image from the news article (1–2 lines max{photo_note})
- "clip": gameplay footage. Set "tag" from: {tags}
- "ai": AI-generated image, ONLY when nothing above fits (max 2). Set "ai_prompt" to a GENERIC scene
   (e.g. "courtroom with lawyers and legal papers", "hacker in dark room with monitors") – never name
   game characters, brands, logos or real people.
Use at least 5 non-"clip" visuals per script. Never two "stat"/"compare"/"list"/"quote" in a row.

Return ONLY JSON:
{{
 "title": "YouTube title, max 70 chars, curiosity + 'GTA 6', no clickbait lies",
 "lines": [{{"text": "...", "label": "...", "big": false, "visual": "clip", "tag": "...", "subject": "", "stat": null, "compare": null, "list": null, "quote": null, "ai_prompt": ""}}],
 "description": "2-3 sentence description in English",
 "hashtags": ["#GTA6", "..."],
 "is_rumour": true/false
}}"""


def write_script(story: dict, tags: list[str], subjects: list[str] | None = None,
                 has_photo: bool = False) -> dict:
    cfg = config()
    subjects = subjects or []
    lang = cfg.get("language", "en")
    user = (f"SOURCE: {story['source']}\nHEADLINE: {story['title']}\nURL: {story['url'] or 'none'}\n\n"
            f"ARTICLE:\n{story['body']}\n\n"
            "OTHER GTA 6 HEADLINES PEOPLE ARE TALKING ABOUT TODAY:\n- " + "\n- ".join(story.get("related", [])))
    can_article = bool(story.get("url")) and "news.google.com" not in story["url"] and "reddit.com" not in story["url"]
    raw = ask(user, system=SYSTEM.format(
        words=cfg["target_words"], tags=", ".join(tags), lang=LANG.get(lang, LANG["en"]),
        subjects=", ".join(subjects) or "(none available – don't use subject)",
        article_note="" if can_article else " – NOT AVAILABLE for this story, don't use",
        photo_note="" if has_photo else " – NOT AVAILABLE for this story, don't use"))
    data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
    lines = [l for l in data["lines"] if l.get("text", "").strip()]
    if len(lines) < 5:
        raise ValueError("script too short")
    low = {x.lower(): x for x in subjects}
    for i, l in enumerate(lines):
        if l.get("tag") not in tags:
            l["tag"] = "any"
        v = l.get("visual", "clip")
        if v == "subject":
            subj = low.get((l.get("subject") or "").lower())
            l["subject"] = subj or ""
            if not subj:
                v = "clip"
        if v == "article" and not can_article:
            v = "clip"
        if v == "photo" and not has_photo:
            v = "clip"
        if v in ("stat", "compare", "list", "quote") and not isinstance(l.get(v), dict):
            v = "clip"
        if v == "list" and not (l["list"].get("items")):
            v = "clip"
        if v == "ai" and not (l.get("ai_prompt") or "").strip():
            v = "clip"
        if i == 0 and v in ("article", "stat", "compare", "list", "quote", "ai"):
            v = "clip"
        l["visual"] = v
        l["label"] = (l.get("label") or "").strip().upper()[:40] or " ".join(re.sub(r"[^\w$%,.' -]", "", l["text"]).split()[:4]).upper()
        l["big"] = bool(l.get("big"))
    if not lines[0]["label"]:
        lines[0]["label"] = data.get("title", "GTA 6 NEWS").upper()[:30]
    data["lines"] = lines
    data["title"] = data["title"][:95]
    log.info("script: %s (%d lines, %d words)", data["title"], len(lines), sum(len(l["text"].split()) for l in lines))
    log.info("visuals: %s", ", ".join(l["visual"] + (f"[{l['subject']}]" if l.get("subject") else "") for l in lines))
    return data
