"""Step 2 – Claude writes the Short: hook, script, per-line visuals, title, hashtags."""
import json
import re

import anthropic

from .common import config, env, log

SYSTEM = """You write viral YouTube Shorts scripts for a faceless GTA 6 news channel.
Style: fast, hype, conversational, like a GTA superfan talking to friends. Short punchy sentences.

RULES
- Line 1 is the HOOK: a surprising claim or question that makes people stop scrolling (max 12 words). Never start with "Hey guys" or "In this video".
- Use ONLY facts in the source material. Never invent dates, numbers, quotes or features.
- Leaks, rumours, insider claims and fan theories MUST be labelled ("according to a rumour", "an insider claims", "fans think") – never state them as confirmed.
- Never describe how to get leaked or pirated copies.
- End with a short engagement line (e.g. "Would you do this mission first? Comment below.") – no "like and subscribe".
- Plain spoken English, no emojis, no hashtags, no stage directions inside the script.
- Total length: about {words} words.

VISUALS
For every line, choose ONE tag for the background clip from this list:
{tags}

Return ONLY JSON:
{{
 "title": "YouTube title, max 70 chars, curiosity + 'GTA 6', no clickbait lies",
 "lines": [{{"text": "spoken line", "tag": "one tag"}}, ...],
 "description": "2-3 sentence description",
 "hashtags": ["#GTA6", "..."],
 "is_rumour": true/false
}}"""


def write_script(story: dict, tags: list[str]) -> dict:
    cfg = config()
    client = anthropic.Anthropic(api_key=env("ANTHROPIC_API_KEY"))
    user = (f"SOURCE: {story['source']}\nHEADLINE: {story['title']}\nURL: {story['url']}\n\n"
            f"ARTICLE:\n{story['body']}\n\n"
            f"OTHER GTA 6 HEADLINES PEOPLE ARE TALKING ABOUT TODAY:\n- " + "\n- ".join(story.get("related", [])))
    msg = client.messages.create(
        model=cfg["claude_model"], max_tokens=1500,
        system=SYSTEM.format(words=cfg["target_words"], tags=", ".join(tags)),
        messages=[{"role": "user", "content": user}],
    )
    raw = msg.content[0].text
    data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
    lines = [l for l in data["lines"] if l.get("text", "").strip()]
    if len(lines) < 3:
        raise ValueError("script too short")
    for l in lines:
        if l.get("tag") not in tags:
            l["tag"] = "any"
    data["lines"] = lines
    data["title"] = data["title"][:95]
    log.info("script: %s (%d lines)", data["title"], len(lines))
    return data
