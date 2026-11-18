"""AI writer for map-explainer videos: turns a launch-week topic into a mapvideo spec."""
import json
import random
import re
from pathlib import Path

from .common import ROOT, log
from .llm import ask
from . import leonida_map as LM

STILLS_JSON = ROOT / "library" / "stills.json"
STATE = ROOT / "state" / "map_titles.txt"

PLACE_INFO = {
    "Vice City": "Rockstar's Miami: neon nightlife, beaches, the main city. South-east coast.",
    "Leonida Keys": "island chain south of Vice City, boats, iguanas, reportedly where the story begins.",
    "Grassrivers": "Everglades-style swamp: alligators, airboats, rough locals.",
    "Port Gellhorn": "Leonida's forgotten Gulf coast: run-down motels, empty strip malls, a working port.",
    "Ambrosia": "heart of Leonida beside Lake Leonida: Allied Crystal sugar refinery, biker gangs.",
    "Mount Kalaga National Park": "against the northern border: hunting, fishing, off-road trails, kayaking.",
    "Lake Leonida": "big lake in the middle of the state, next to Ambrosia.",
}

FACTS = """Facts you may use (all official or widely reported):
- GTA 6 launches November 19, 2026 on PS5 and Xbox Series X|S. PC has no date yet. Digital preload started November 12.
- It is set in the state of Leonida (Rockstar's Florida). Main city: Vice City.
- Six regions named by Rockstar: Vice City, Leonida Keys, Grassrivers, Port Gellhorn, Ambrosia, Mount Kalaga National Park.
- Main characters: Jason Duval and Lucia Caminos, a criminal couple.
- Other named characters: Cal Hampton, Boobie Ike, Dre'Quan Priest, Real Dimez, Raul Bautista, Brian Heder.
- Trailer 1 came out December 2023, Trailer 2 in May 2025, the launch trailer on October 15, 2026.
- GTA 6 was delayed twice (from 2025, then from May 26, 2026).
Never invent numbers, prices, map sizes, leaks or features that are not in these facts or in the news lines given."""

SYSTEM = """You write viral 25–40 second YouTube Shorts scripts for a GTA 6 channel in the
"map explainer" style: the whole video happens on a map of Leonida, the camera flies
between places, official screenshots pop up on cards, captions pop 1–3 words at a time.

Writing style: hook in line 1 (curiosity or shock, max 10 words), short punchy lines
(6–14 words), talk to the viewer ("you"), build hype for LAUNCH (it is launch week),
end with a question that makes people comment. 7–10 lines, 80–110 words total. English.

Return JSON:
{"title": "...", "yt_title": "... #shorts (max 70 chars, hype, no clickbait lies)",
 "description": "2–3 sentences + hashtags", "tags": ["..."],
 "tracker_title": "2–3 word name for the progress bar, e.g. LEONIDA TOUR / LAUNCH CHECKLIST",
 "poll": "short question for the end card (max 34 chars)",
 "lines": [{"text": "...", "cam": "full" or a place name, "card": null or {"img": "<file>", "bottom": "2–3 WORD LABEL"},
            "pill": null or "SHORT RED LABEL (max 16 chars)", "big": null or "HUGE TEXT (max 12 chars)"}]}

Rules:
- "cam" must be "full" or one of the places listed. Visit 3–6 different places; first and last lines use "full".
- Use "card" on most place lines, with an image file from the list that really fits (same subject).
- "pill" only on line 1 (e.g. "NOVEMBER 19", "OUT TOMORROW", "LAUNCH WEEK").
- "big" on 1–2 lines max for a punchy number or phrase shown huge on the map (e.g. "1 DAY LEFT", "6 REGIONS", "13 YEARS").
- Only use facts given. It is fine to be hyped and to give opinions ("this could be the best part").
"""


def _catalog():
    d = json.loads(STILLS_JSON.read_text())
    by = {}
    for x in d:
        if x["w"] > x["h"] and x["subject"] not in ("Cover Art", "The Album Cover Art"):
            by.setdefault(x["subject"], []).append(x["file"])
    return by


def used_titles():
    return STATE.read_text().splitlines() if STATE.exists() else []


def topics(n: int, news: list[str]) -> list[str]:
    prompt = (f"{FACTS}\n\nLatest news headlines:\n" + "\n".join(f"- {h}" for h in news[:25]) +
              f"\n\nAlready made (do NOT repeat): {used_titles()[-60:]}\n\n"
              f"Give {n} DIFFERENT launch-week video ideas that work as a map tour of Leonida "
              "(places, characters' turf, where to go first, what to do on day one, hidden spots in screenshots, "
              "countdown, region battles, best place to live, etc). Each must be possible with the facts/news. "
              'Return JSON {"topics": ["...", ...]} with one short sentence per idea.')
    data = json.loads(ask(prompt, json_out=True))
    return [t for t in data.get("topics", []) if isinstance(t, str)][:n]


def write_spec(topic: str, news: list[str]) -> dict:
    cat = _catalog()
    cat_txt = "\n".join(f"{k}: {', '.join(v[:10])}" for k, v in cat.items())
    places = "\n".join(f"- {k}: {v}" for k, v in PLACE_INFO.items())
    prompt = (f"{FACTS}\n\nNews lines you may use:\n" + "\n".join(f"- {h}" for h in news[:15]) +
              f"\n\nPlaces (for cam):\n{places}\n\nOfficial screenshot files by subject:\n{cat_txt}\n\n"
              f"TOPIC: {topic}")
    spec = json.loads(ask(prompt, system=SYSTEM, json_out=True))
    return fix_spec(spec, cat)


def fix_spec(spec: dict, cat: dict) -> dict:
    files = {f for v in cat.values() for f in v}
    places = set(LM.PLACES)
    lines = [l for l in spec.get("lines", []) if isinstance(l, dict) and (l.get("text") or "").strip()]
    if len(lines) < 5:
        raise ValueError("script too short")
    tour, prev = [], None
    for i, l in enumerate(lines):
        l["text"] = re.sub(r"\s+", " ", l["text"]).strip()
        cam = l.get("cam") or "full"
        if cam not in places:
            cam = "full"
        l["cam"] = cam
        c = l.get("card")
        if isinstance(c, dict) and c.get("img") in files and cam != "full":
            c["top"] = "OFFICIAL SCREENSHOT"
            c["bottom"] = (c.get("bottom") or cam).upper()[:22]
        else:
            l["card"] = None
        if i > 0:
            l["pill"] = None
        elif l.get("pill"):
            l["pill"] = str(l["pill"]).upper()[:18]
        if l.get("big"):
            l["big"] = str(l["big"]).upper()[:14]
            if l.get("card"):
                l["big"] = None
        if cam != "full":
            l["route"] = prev is not None and prev != cam
            if cam not in tour:
                tour.append(cam)
            prev = cam
    lines[0]["cam"] = "full"
    lines[0]["card"] = None
    lines[-1]["cam"] = "full"
    lines[-1]["card"] = None
    lines[-1]["poll"] = (spec.get("poll") or "WHERE ARE YOU GOING FIRST?").upper()[:40]
    # progress tracker numbers
    n = 0
    for l in lines:
        if l["cam"] != "full" and l["cam"] in tour:
            n = max(n, tour.index(l["cam"]) + 1)
        if tour:
            l["tracker"] = n
    spec["lines"] = lines
    spec["tour"] = tour
    spec["tracker_title"] = (spec.get("tracker_title") or "LEONIDA TOUR").upper()[:22]
    spec.setdefault("tags", ["GTA 6", "GTA VI", "Leonida", "Vice City"])
    d = spec.get("description") or spec.get("title", "")
    if "fan-made" not in d:
        d += "\n\nMap is fan-made and spots are estimates. Screenshots: Rockstar Games."
    spec["description"] = d
    yt = (spec.get("yt_title") or spec.get("title") or "GTA 6 is almost here").strip()
    if "#shorts" not in yt.lower():
        yt = yt[:90] + " #shorts"
    spec["yt_title"] = yt
    spec["theme"] = spec.get("theme") or random.choice(list(LM.THEMES))
    return spec


def remember(title: str):
    STATE.parent.mkdir(exist_ok=True)
    with STATE.open("a") as f:
        f.write(title + "\n")
