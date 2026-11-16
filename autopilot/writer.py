"""Step 2 – the AI writes the Short in the style of top GTA news channels (story-driven investigation)."""
import json
import re

from .common import config, env, log
from .llm import ask
from .pill import icon_names

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

"icon" (every line): one 3D icon that fits the line, from: {icons}

"label" (every line, never empty): 2–5 word UPPERCASE ENGLISH summary of the line's key fact
("17TH & LAST LEAK", "LEAKS STARTED AUG 18", "$270,000 CASHED OUT"). Line 1's label is the hook question.
"big": true when the label is just a date / money / number.

"visual" – pick the BEST match for each line:
- "subject": an official Rockstar image/clip of a named character/place/vehicle. Use whenever the line
   mentions one. Set "subject" to one EXACT name from: {subjects}
- "stat": animated big number. Use for real, meaningful numbers from the source (money, sales, dates, sizes,
   percentages, version numbers) – never invent a number just to fill a stat.
   Set "stat": {{"value": "$7.6 BILLION", "caption": "expected first-year revenue"}}
- "compare": two growing bars. Use when two things are compared.
   Set "compare": {{"a_label": "GTA 5 map", "a_value": "49", "b_label": "GTA 6 map", "b_value": "100", "unit": "sq km"}}
- "blocks": a grid of icon blocks where some drop out / light up. Use when something is COUNTED
   (songs removed, players, missions, cities…). Set "blocks": {{"total": 50, "highlight": 17,
   "caption": "tracks removed from GTA 4", "icon": "music", "mode": "remove"}}  (mode "add" = they light up)
- "list": checklist that ticks in. Use when the line lists 2–4 things.
   Set "list": {{"title": "WHAT'S NEW", "items": ["Two playable leads", "Vice City", "Online at launch"]}}
- "quote": quote card. Use when someone is quoted. Set "quote": {{"text": "...", "by": "Take-Two CEO"}}
- "article": screenshot of the source article with the headline highlighted (1 line max, when citing the source{article_note})
- "photo": the main image from the news article (1–2 lines max{photo_note})
- "map": animated map that zooms to a COUNTRY with its flag. Use whenever a country is mentioned
   (bans, ratings, sales in a country, studios). Set "country": "South Korea"
- "person": name card for a real person or organisation (we never show real people's photos).
   Set "person": {{"name": "Strauss Zelnick", "role": "Take-Two CEO", "country": "USA"}}
- "stock": REAL-LIFE footage{stock_note}. Use for real-world things: courts, lawyers, money, hackers,
   police, Miami streets, crowds, gaming setups, stock market, offices. Set "stock_query" (2–4 English words,
   e.g. "courtroom judge", "counting money", "miami night traffic"). Use 2–4 times per script when relevant.
- "clip": gameplay footage. Set "tag" from: {tags}
- "ai": AI-generated image, ONLY when nothing above fits (max 2). Set "ai_prompt" to a GENERIC scene
   (e.g. "courtroom with lawyers and legal papers", "hacker in dark room with monitors") – never name
   game characters, brands, logos or real people.
"mascot": our cartoon flamingo mascot reacts on screen – use on 3–4 lines max (hook, twist, shocking fact,
ending). One of: shocked, pointing, laughing, thinking, money, thumbsup, angry. "" for other lines.

Use at least 8 non-"clip" visuals per script; "clip" is the LAST choice. Never two "stat"/"compare"/"list"/"quote" in a row.

Return ONLY JSON:
{{
 "title": "YouTube title, max 70 chars, curiosity + 'GTA 6', no clickbait lies",
 "lines": [{{"text": "...", "label": "...", "big": false, "visual": "clip", "tag": "...", "subject": "", "stat": null, "compare": null, "list": null, "quote": null, "ai_prompt": "", "stock_query": "", "country": "", "person": null, "blocks": null, "icon": "", "mascot": ""}}],
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
        icons=", ".join(icon_names()),
        subjects=", ".join(subjects) or "(none available – don't use subject)",
        article_note="" if can_article else " – NOT AVAILABLE for this story, don't use",
        photo_note="" if has_photo else " – NOT AVAILABLE for this story, don't use",
        stock_note="" if env("PEXELS_API_KEY") else " – NOT AVAILABLE, don't use"))
    data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
    lines = [l for l in data["lines"] if l.get("text", "").strip()]
    if len(lines) < 5:
        raise ValueError("script too short")
    low = {x.lower(): x for x in subjects}
    for i, l in enumerate(lines):
      try:
          if l.get("tag") not in tags:
              l["tag"] = "any"
          v = l.get("visual", "clip")
          if v == "clip" and i > 0 and low.get((l.get("subject") or "").lower()):
              v = "subject"                      # Gemini named a subject but forgot to use it
          if v == "subject":
              subj = low.get((l.get("subject") or "").lower())
              l["subject"] = subj or ""
              if not subj:
                  v = "clip"
          if v == "article" and not can_article:
              v = "clip"
          if v == "photo" and not has_photo:
              v = "clip"
          if v == "map":
              from .geomap import resolve
              if not (l.get("country") and resolve(l["country"])):
                  v = "clip"
          if v == "blocks":
              b = l.get("blocks") or {}
              try:
                  tot, hl = float(str(b.get("total", 0)).replace(",", "")), float(str(b.get("highlight", 0)).replace(",", ""))
                  if not (tot >= 2 and 0 < hl <= tot):
                      v = "clip"
                  elif b.get("icon") not in icon_names():
                      b["icon"] = l.get("icon") if l.get("icon") in icon_names() else "star"
              except (TypeError, ValueError, AttributeError):
                  v = "clip"
          if v in ("stat", "compare", "list", "quote", "person", "blocks") and not isinstance(l.get(v), dict):
              v = "clip"
          if v == "stat":
              val = str(l["stat"].get("value", ""))
              digits = re.sub(r"\D", "", val)
              try:
                  tiny = bool(digits) and int(digits) < 2
              except ValueError:
                  tiny = False
              if not val or (tiny and not re.search(r"[$%]|billion|million", val, re.I)):
                  v = "clip"
          if v == "list" and not (l["list"].get("items")):
              v = "clip"
          if v == "stock" and not ((l.get("stock_query") or "").strip() and env("PEXELS_API_KEY")):
              v = "clip"
          if v == "ai" and not (l.get("ai_prompt") or "").strip():
              v = "clip"
          if i == 0 and v in ("article", "stat", "compare", "list", "quote", "ai", "stock", "person", "blocks"):
              v = "clip"
          l["visual"] = v
          l["icon"] = l.get("icon") if l.get("icon") in icon_names() else ""
          l["mascot"] = l.get("mascot") if l.get("mascot") in _mascots() else ""
          l["label"] = (l.get("label") or "").strip().upper()[:40] or " ".join(re.sub(r"[^\w$%,.' -]", "", l["text"]).split()[:4]).upper()
          l["big"] = bool(l.get("big"))
      except Exception as e:                 # a weird value in one line must never kill the video
        log.warning("line %d visual reset to clip: %s", i, e)
        l["visual"], l["tag"] = "clip", l.get("tag") if l.get("tag") in tags else "any"
        l["label"] = (l.get("label") or "").strip().upper()[:40] or "GTA 6"
        l["big"] = False
    _enforce_variety(lines, subjects)
    if not lines[0]["label"]:
        lines[0]["label"] = data.get("title", "GTA 6 NEWS").upper()[:30]
    data["lines"] = lines
    data["title"] = data["title"][:95]
    log.info("script: %s (%d lines, %d words)", data["title"], len(lines), sum(len(l["text"].split()) for l in lines))
    log.info("visuals: %s", ", ".join(l["visual"] + (f"[{l['subject']}]" if l.get("subject") else "") for l in lines))
    return data


def _mascots():
    try:
        from .mascot import available
        return available()
    except Exception:
        return []


MASCOT_POSES = ["shocked", "pointing", "laughing", "thinking", "money", "thumbsup", "angry"]
COUNTRY_WORDS = ["South Korea", "North Korea", "Japan", "China", "India", "Australia", "Germany", "United Kingdom", "UK",
                 "Saudi Arabia", "United Arab Emirates", "UAE", "Brazil", "Russia", "Canada", "Mexico", "France",
                 "Indonesia", "Malaysia", "Singapore", "Thailand", "Vietnam", "Turkey", "Egypt", "Qatar", "Kuwait",
                 "Pakistan", "Bangladesh", "Philippines", "Italy", "Spain", "Poland", "Netherlands", "Sweden",
                 "Scotland", "Ireland", "New Zealand", "South Africa", "Argentina", "Colombia"]
GENERIC_SUBJECTS = ["Vice City", "Jason And Lucia", "Leonida Keys", "Lucia Caminos", "Jason Duval",
                    "Port Gellhorn", "Grassrivers", "Ambrosia", "Mount Kalaga National Park"]
NUM = re.compile(r"(\$\s?\d[\d,.]*\s*(?:million|billion|k)?|\d[\d,.]*\s*(?:million|billion|%|percent|copies|players|hours|km|miles))", re.I)


def _enforce_variety(lines: list[dict], subjects: list[str]):
    """Gemini likes to fall back to plain gameplay. Guarantee that most lines show something specific."""
    if not subjects:
        return
    by_len = sorted(subjects, key=len, reverse=True)
    first_names = {}
    for sname in subjects:
        for part in sname.split():
            if len(part) > 3 and part.lower() not in ("and", "the", "city", "keys", "park", "mount", "national", "cover", "art", "album"):
                first_names.setdefault(part.lower(), sname)
    # 1) any line naming a character/place -> show that character/place
    for l in lines[1:]:
        if l["visual"] != "clip":
            continue
        low = l["text"].lower()
        hit = next((sn for sn in by_len if sn.lower() in low), None) or \
              next((sn for fn, sn in first_names.items() if re.search(rf"\b{re.escape(fn)}\b", low)), None)
        if not hit and re.search(r"\bvice city\b|\bmiami\b", low):
            hit = "Vice City" if "Vice City" in subjects else None
        if not hit and "leonida" in low:
            hit = next((x for x in subjects if "Leonida" in x), None)
        if hit:
            l["visual"], l["subject"] = "subject", hit
    # 1b) a country named in a plain line -> map
    from .geomap import resolve
    for l in lines[1:]:
        if l["visual"] != "clip":
            continue
        for cname in COUNTRY_WORDS:
            if re.search(rf"\b{re.escape(cname)}\b", l["text"], re.I) and resolve(cname):
                l["visual"], l["country"] = "map", cname
                break
    # mascot on max 4 lines, not on two lines in a row
    m_used, prev = 0, False
    lines[0]["mascot"] = ""                  # hook layout has its own label in the middle
    for l in lines:
        if l.get("mascot") and (m_used >= 4 or prev):
            l["mascot"] = ""
        if l.get("mascot"):
            m_used += 1
        prev = bool(l.get("mascot"))
    # max 2 maps per video, and never the same country twice
    seen, maps = set(), 0
    for l in lines:
        if l["visual"] == "map":
            key = (l.get("country") or "").lower()
            if maps >= 2 or key in seen:
                l["visual"] = "clip"
            else:
                seen.add(key); maps += 1
    # 2) real numbers in plain lines -> stat card
    prev_card = False
    for l in lines[1:]:
        if l["visual"] == "clip" and not prev_card:
            m = NUM.search(l["text"])
            if m:
                l["visual"] = "stat"
                l["stat"] = {"value": m.group(1).strip().upper(), "caption": l["label"] or ""}
        prev_card = l["visual"] in ("stat", "compare", "list", "quote")
    # 3) keep gameplay to about a third of the lines – the rest get official Rockstar imagery
    clips = [l for l in lines[1:] if l["visual"] == "clip"]
    allowed = max(2, len(lines) // 3)
    pool = [x for x in GENERIC_SUBJECTS if x in subjects] or subjects
    for k, l in enumerate(clips[::2][: max(0, len(clips) - allowed)]):
        l["visual"], l["subject"] = "subject", pool[k % len(pool)]
