"""GTA 6 Super Clipper promo-reel autopilot.

script (Claude script bank)  ->  voice (ElevenLabs, Viraj)  ->  animated reel (HTML engine + Chrome)
->  music + SFX  ->  Telegram (video + cover + ready-to-paste caption).  Nothing is posted anywhere.

Run:  python -m promo.make            (from the repo root)
"""
import base64, json, os, random, re, subprocess, sys, time
from pathlib import Path

import numpy as np
import requests
import soundfile as sf

from autopilot.common import env, log

HERE = Path(__file__).resolve().parent
ASSETS, ENGINE, STATE = HERE / "assets", HERE / "engine", HERE / "state"
OUT = HERE.parent / "output" / "promo"
OUT.mkdir(parents=True, exist_ok=True)
STATE.mkdir(exist_ok=True)
HIST = STATE / "history.json"
FPS = 30
TEMPO = 1.15

# ---------------------------------------------------------------- themes
BASE = {"acc": "#ff3b5c", "sec": "#ffb020", "pk": "#38bdf8", "bg1": "#2a0a10", "bg2": "#14060a", "bg3": "#070304",
        "bg4": "#5a1420", "mut": "#d6a9ad", "lt": "#ffeaea", "lt2": "#fff3f1"}
THEMES = {
    "Hot Red": BASE,
    "Moonlight": {"acc": "#7dffcf", "sec": "#a78bfa", "pk": "#ff5c8a", "bg1": "#120e2e", "bg2": "#09071c", "bg3": "#05040f", "bg4": "#2e2670", "mut": "#a9a3d6", "lt": "#e9e6ff", "lt2": "#f3f1ff"},
    "Black Gold": {"acc": "#ffe14d", "sec": "#ff9f1a", "pk": "#ff4d6d", "bg1": "#1c1b03", "bg2": "#0d0c02", "bg3": "#050500", "bg4": "#3d3a08", "mut": "#c9c39a", "lt": "#fffbe0", "lt2": "#fffbe8"},
    "Cyber Blue": {"acc": "#22d3ee", "sec": "#e879f9", "pk": "#facc15", "bg1": "#0a1630", "bg2": "#060d1f", "bg3": "#02050c", "bg4": "#16305e", "mut": "#9fb3d6", "lt": "#e6f4ff", "lt2": "#f0faff"},
    "Toxic Green": {"acc": "#a3e635", "sec": "#8b5cf6", "pk": "#f472b6", "bg1": "#0f1a07", "bg2": "#081004", "bg3": "#030601", "bg4": "#25400f", "mut": "#b0c59a", "lt": "#f0ffe0", "lt2": "#f6ffec"},
    "Vice Sunset": {"acc": "#ff8a3d", "sec": "#ff4fa3", "pk": "#38bdf8", "bg1": "#2a0f24", "bg2": "#170814", "bg3": "#080308", "bg4": "#4f1c43", "mut": "#d9a9c6", "lt": "#ffecf6", "lt2": "#fff3f8"},
}


def rgba(h):
    h = h.lstrip("#")
    return "rgba(%d,%d,%d" % tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def themed(text, th):
    pairs = []
    for k, v in BASE.items():
        pairs += [(v, th[k]), (rgba(v), rgba(th[k]))]
    # two-step swap so a new colour can't be swapped again
    for i, (a, _) in enumerate(pairs):
        text = re.sub(re.escape(a), f"@@{i}@@", text, flags=re.I)
    for i, (_, b) in enumerate(pairs):
        text = text.replace(f"@@{i}@@", b)
    return text


# ---------------------------------------------------------------- script (from Claude's script bank)
def load_hist():
    try:
        return json.loads(HIST.read_text())
    except Exception:
        return {"n": 0, "hooks": [], "themes": []}


BANK = HERE / "scripts.json"      # scripts written by Claude (no Gemini)
CTAS = ["Agar tumhe bhi ye app chahiye, toh mujhe follow karo, link meri bio mein hai.",
        "Ye app chahiye? Toh abhi follow karo, link meri bio mein hai.",
        "App chahiye toh mujhe follow karo, link bio mein hai."]
PERMS = ["Aur haan, sirf unhi streamers ko clip karna jo clipping ki permission dete hain.",
         "Bas yaad rakhna, sirf wahi streamers chunna jo clipping allow karte hain."]
FEATS = ["✅ Works with YouTube and Twitch live streams", "✅ Catches hype moments from live chat on its own 🔥",
         "✅ Detects action: chases, fails, crashes", "✅ \"Clip from\" lets you clip earlier gameplay ⏪",
         "✅ Auto captions + facecam layout", "✅ Hook, title & hashtags ready for every clip",
         "✅ Export 9:16 or 16:9", "✅ Up to 50 clips from one stream 🤯", "✅ Works fully on mobile, no laptop"]
TAGS = ["#gta6", "#gta6clips", "#livestream", "#clipping", "#streamclips", "#mobileediting", "#aitools", "#reelsindia",
        "#shortsindia", "#gamingreels", "#contentcreator", "#clipper", "#twitchclips", "#youtubelive", "#gamingindia",
        "#gta6news", "#streamer", "#gamingclips"]


def write_script(hist):
    bank = json.loads(BANK.read_text())
    used = set(hist.get("used", []))
    left = [i for i in range(len(bank)) if i not in used]
    if not left:
        return None, 0
    i = left[0]
    s = bank[i]
    beats = [dict(b) for b in s["beats"]]
    beats.append({"text": random.choice(CTAS), "scene": "cta", "params": {}, "cues": ["follow", "link"]})
    beats.append({"text": random.choice(PERMS), "scene": "permission", "params": {}, "cues": []})
    feats = random.sample(FEATS, 5)
    cap = (f"{s['cap']}\n\nNo laptop, no editing. Just paste a live stream link and the app does the rest 😎\n\n" + "\n".join(feats) +
           "\n\nWant the app? Follow me 👉 link in bio 🔗\n\n⚠️ Only clip streamers who allow clipping, and always give credit 🙏\n"
           "Not affiliated with Rockstar Games.\n\n" + " ".join(random.sample(TAGS, 14)))
    d = {"idx": i, "hook_summary": beats[0]["text"], "beats": beats, "caption": cap, "cover": s.get("cover") or {}}
    return d, len(left) - 1


# ---------------------------------------------------------------- voice
EL = "https://api.elevenlabs.io/v1"


def voice_id(key):
    vf = STATE / "voice.json"
    if env("PROMO_VOICE_ID"):
        return env("PROMO_VOICE_ID")
    if vf.exists():
        return json.loads(vf.read_text())["voice_id"]
    h = {"xi-api-key": key}
    mine = requests.get(f"{EL}/voices", headers=h, timeout=60).json().get("voices", [])
    for v in mine:
        if "viraj" in v["name"].lower():
            vf.write_text(json.dumps({"voice_id": v["voice_id"], "name": v["name"]}))
            return v["voice_id"]
    shared = requests.get(f"{EL}/shared-voices", headers=h, params={"search": "Viraj", "page_size": 30}, timeout=60).json().get("voices", [])
    shared.sort(key=lambda v: ("energetic" not in v["name"].lower(), "narrator" not in v["name"].lower()))
    if not shared:
        raise RuntimeError("Viraj voice not found on ElevenLabs")
    v = shared[0]
    r = requests.post(f"{EL}/voices/add/{v['public_owner_id']}/{v['voice_id']}", headers=h, json={"new_name": v["name"]}, timeout=60)
    vid = r.json().get("voice_id") or v["voice_id"]
    vf.write_text(json.dumps({"voice_id": vid, "name": v["name"]}))
    log.info("using ElevenLabs voice %s (%s)", v["name"], vid)
    return vid


def credits_left(key):
    try:
        s = requests.get(f"{EL}/user/subscription", headers={"xi-api-key": key}, timeout=30).json()
        return s["character_limit"] - s["character_count"]
    except Exception:
        return None


def make_voice(text, work):
    key = env("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY secret is missing")
    vid = voice_id(key)
    r = requests.post(f"{EL}/text-to-speech/{vid}/with-timestamps", params={"output_format": "mp3_44100_128"},
                      headers={"xi-api-key": key}, timeout=240,
                      json={"text": text, "model_id": "eleven_multilingual_v2",
                            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.3, "use_speaker_boost": True}})
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text[:300]}")
    data = r.json()
    (work / "raw.mp3").write_bytes(base64.b64decode(data["audio_base64"]))
    al = data.get("alignment") or data["normalized_alignment"]
    words, cur, ws, we = [], "", 0, 0
    for c, s, e in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
        if c.isspace():
            if cur:
                words.append([cur, ws, we]); cur = ""
            continue
        if not cur:
            ws = s
        cur += c; we = e
    if cur:
        words.append([cur, ws, we])
    # remove long pauses ("no gaps"), then speed up 1.15x like the hand-made reels
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", work / "raw.mp3", "-ac", "1", "-ar", "48000", work / "raw.wav"], check=True)
    x, sr = sf.read(work / "raw.wav")
    keep, shift, segs, prev_end = 0.14, 0.0, [], 0.0
    out_words = []
    for w, s, e in words:
        gap = s - prev_end
        if gap > 0.28 and out_words:
            cut = gap - keep
            segs.append((prev_end + keep / 2, s - keep / 2)); shift += cut
        out_words.append([w, s - shift, e - shift]); prev_end = e
    mask = np.ones(len(x), bool)
    for a, b in segs:
        mask[int(a * sr):int(b * sr)] = False
    y = x[mask][: int((out_words[-1][2] + 0.35) * sr)]
    sf.write(work / "tight.wav", y, sr)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", work / "tight.wav", "-af",
                    f"atempo={TEMPO},highpass=f=80,lowpass=f=15000,afftdn=nf=-25,equalizer=f=180:t=q:w=1:g=2,equalizer=f=3200:t=q:w=1.2:g=3,"
                    "deesser=i=0.4,acompressor=threshold=-20dB:ratio=3.5:attack=5:release=80:makeup=4,loudnorm=I=-16:TP=-1.5:LRA=9",
                    "-ar", "48000", "-ac", "1", work / "vo.wav"], check=True)
    W = [{"w": w, "s": round(s / TEMPO, 3), "e": round(e / TEMPO, 3)} for w, s, e in out_words]
    dur = len(sf.read(work / "vo.wav")[0]) / 48000
    return W, dur, credits_left(key)


# ---------------------------------------------------------------- plan
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())


def make_plan(beats, W, dur):
    plan, i = [], 0
    for b in beats:
        n = len(b["text"].split())
        idx = list(range(i, min(i + n, len(W))))
        i += n
        if not idx:
            continue
        plan.append({"t": b.get("scene", "statement"), "p": b.get("params") or {}, "idx": idx, "cues": b.get("cues") or []})
    for k, b in enumerate(plan):
        b["s"] = 0.0 if k == 0 else W[b["idx"][0]]["s"] - 0.05
    for k, b in enumerate(plan):
        b["e"] = plan[k + 1]["s"] if k + 1 < len(plan) else dur + 0.4
    # merge beats that are too short to read (keep the earlier scene, extend it)
    merged = []
    for b in plan:
        if merged and (b["e"] - b["s"] < 1.3) and b["t"] not in ("cta", "permission", "name"):
            merged[-1]["e"] = b["e"]; merged[-1]["idx"] += b["idx"]
        else:
            merged.append(b)
    out = []
    for b in merged:
        cues, j = [], 0
        for cw in b["cues"][:4]:
            t = None
            for k in range(j, len(b["idx"])):
                if norm(W[b["idx"][k]]["w"]).startswith(norm(cw)[:5] or "#"):
                    t = round(max(0.15, W[b["idx"][k]]["s"] - b["s"]), 2); j = k + 1
                    break
            cues.append(t)
        out.append({"t": b["t"], "s": round(b["s"], 2), "e": round(b["e"], 2), "p": b["p"], "c": cues})
    return out


def build_html(plan, W, theme, path):
    head = themed((ENGINE / "head.html").read_text(), theme)
    lib = themed((ENGINE / "lib.js").read_text(), theme)
    tpl = themed((ENGINE / "templates.js").read_text(), theme)
    tail = themed((ENGINE / "tail.html").read_text(), theme)
    consts = f"const BG1='{theme['bg1']}',BG4='{theme['bg4']}',MUT='{theme['mut']}',LT='{theme['lt']}';\nconst PLAN={json.dumps(plan, ensure_ascii=False)};\n"
    html = head + lib + "\n" + consts + tpl + "\n" + tail
    path.write_text(html.replace("const W=WORDS;", "const W=" + json.dumps(W, ensure_ascii=False) + ";"))


def chrome():
    for c in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable"):
        if os.path.exists(c):
            return c
    return None


def render(html, mp4, dur, stills=()):
    from playwright.sync_api import sync_playwright
    n = int(dur * FPS)
    ff = None
    if mp4:
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(mp4)], stdin=subprocess.PIPE)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome(), args=["--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(html.as_uri()); pg.wait_for_timeout(1500)
        for t, path in stills:
            pg.evaluate(f"renderA({t})"); pg.wait_for_timeout(700); pg.evaluate(f"renderA({t})"); pg.wait_for_timeout(300)
            pg.screenshot(path=str(path), type="jpeg", quality=92)
        if ff:
            for i in range(n):
                pg.evaluate(f"renderA({i / FPS})")
                ff.stdin.write(pg.screenshot(type="jpeg", quality=90))
                if i % 300 == 0:
                    log.info("render %d/%d", i, n)
        b.close()
        if errs:
            log.warning("page errors: %s", errs[:3])
    if ff:
        ff.stdin.close(); ff.wait()


# ---------------------------------------------------------------- sound
def sfx_events(plan, dur, rng):
    ev = [["impact", 0.02, .9, None], ["glitch", 0.05, .5, None]]
    big = {"hook": [0], "paste": [2], "hype": [1, 2], "rewind": [2], "count": [0], "noedit": [0], "export": [1], "flow": [1],
           "copylink": [1], "manual": [0], "moments": [0, 1, 2]}
    for k, b in enumerate(plan):
        s, D = b["s"], b["e"] - b["s"]
        if k:
            ev.append(["whoosh", s - .2, .6, None])
        if b["t"] in ("name", "permission", "statement", "cta"):
            ev.append(["impact" if b["t"] != "cta" else "pop", s, .9, None if b["t"] != "cta" else 900])
        for j, c in enumerate(b["c"]):
            if c is None:
                continue
            if j in big.get(b["t"], []):
                ev += [["impact", s + c, 1.0, None], ["ding", s + c + .02, .4, 1568]]
            else:
                ev += [["pop", s + c, .6, 900 + 100 * j], ["click", s + c, .7, None]]
        if b["t"] == "hype":
            t = s + .2
            while t < s + D * .8:
                ev.append(["pop", t, .2, float(rng.integers(900, 1500))]); t += .12
        if b["t"] == "count":
            c0 = (b["c"][0] if b["c"] and b["c"][0] is not None else min(.5, D * .2))
            t = s + c0
            while t < s + c0 + 1.0:
                ev.append(["tick", t, .45, None]); t += .02
            ev.append(["cash", s + c0 + 1.0, .5, None])
        if b["t"] == "cta":
            ev.append(["cash", s + D * .65, .45, None])
    return ev


def mix(work, plan, dur, seed):
    rng = np.random.default_rng(seed)
    progs = [[[37, [56, 61, 65]], [42, [57, 61, 66]], [39, [58, 63, 66]], [44, [56, 59, 63]]],
             [[38, [57, 62, 65]], [34, [58, 62, 65]], [36, [55, 60, 64]], [33, [57, 60, 64]]],
             [[40, [59, 64, 67]], [36, [60, 64, 67]], [43, [59, 62, 67]], [38, [57, 62, 66]]],
             [[33, [57, 60, 64]], [41, [57, 60, 65]], [36, [55, 60, 64]], [40, [56, 59, 64]]]]
    drop = plan[1]["s"] if len(plan) > 1 and plan[1]["s"] > 1.2 else 3.0
    cfg = {"D": dur + 0.5, "seed": int(seed), "bpm": int(rng.integers(124, 146)), "prog": progs[int(rng.integers(0, 4))],
           "drop": round(drop, 2), "end": round(dur + 0.2, 2), "sfx": sfx_events(plan, dur, rng)}
    (work / "music.json").write_text(json.dumps(cfg))
    subprocess.run([sys.executable, HERE / "music.py", work / "music.json", work / "vo.wav", work / "music.wav", work / "sfx.wav"], check=True)


# ---------------------------------------------------------------- telegram
# promo reels go to their OWN Telegram bot (PROMO_TELEGRAM_BOT_TOKEN), separate from the GTA 6 news bot.
# Chat ID: PROMO_TELEGRAM_CHAT_ID if set, else your normal chat ID (same person = same ID for any bot).
def tg_chat():
    return env("PROMO_TELEGRAM_CHAT_ID") or env("TELEGRAM_CHAT_ID")


def tg(method, **kw):
    tok = env("PROMO_TELEGRAM_BOT_TOKEN") or env("TELEGRAM_BOT_TOKEN")
    if not tok:
        return {}
    try:
        return requests.post(f"https://api.telegram.org/bot{tok}/{method}", timeout=300, **kw).json()
    except Exception as e:
        log.warning("telegram %s failed: %s", method, e)
        return {}


def main():
    hist = load_hist()
    n = hist["n"] + 1
    stamp = time.strftime("%Y%m%d_%H%M")
    work = OUT / f"reel_{stamp}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        d, remaining = write_script(hist)
        if d is None:
            tg("sendMessage", data={"chat_id": tg_chat(), "text": "📭 Promo reel autopilot: all scripts are used up. Ask Claude for a new batch of scripts."})
            return
        (work / "script.json").write_text(json.dumps(d, ensure_ascii=False, indent=1))
        text = " ".join(" ".join(b["text"].split()) for b in d["beats"])
        W, dur, left = make_voice(text, work)
        plan = make_plan(d["beats"], W, dur)
        (work / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1))
        recent = hist.get("themes", [])[-2:]
        tname = random.choice([t for t in THEMES if t not in recent])
        theme = THEMES[tname]
        html = ASSETS / "_reel.html"
        build_html(plan, W, theme, html)
        render(html, work / "video.mp4", dur + 0.5)
        mix(work, plan, dur, seed=int(time.time()) % 100000)
        final = OUT / f"Super_Clipper_Reel_{n:03d}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", work / "video.mp4", "-i", work / "vo.wav", "-i", work / "music.wav", "-i", work / "sfx.wav",
                        "-filter_complex", "[1:a]volume=1.0[v];[2:a]volume=0.24[m];[3:a]volume=0.34[s];[v][m][s]amix=inputs=3:normalize=0:duration=first,"
                        "alimiter=limit=0.95,loudnorm=I=-14:TP=-1:LRA=11[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", final], check=True)
        if final.stat().st_size > 48e6:
            small = final.with_name(final.stem + "_s.mp4")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", final, "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-c:a", "copy", small], check=True)
            small.replace(final)
        # cover image: hook scene with the cover lines, no captions
        cov = d.get("cover") or {}
        cplan = [{"t": "hook", "s": 0, "e": 3, "p": {"lines": cov.get("lines") or plan[0]["p"].get("lines"), "hl": cov.get("hl", 1),
                                                     "emoji": plan[0]["p"].get("emoji", "😎"), "visual": "cards", "cover": 1}, "c": [1.0]}]
        build_html(cplan, [], theme, ASSETS / "_cover.html")
        cover = OUT / f"Super_Clipper_Cover_{n:03d}.jpg"
        render(ASSETS / "_cover.html", None, 0, stills=[(2.2, cover)])
        # deliver
        chat = tg_chat()
        info = f"🎬 Promo reel #{n} ready ({dur:.0f}s · {tname} theme)\nHook: {d.get('hook_summary', '')[:200]}"
        if left is not None:
            info += f"\nElevenLabs credits left: {left:,}"
        if remaining <= 6:
            info += f"\n⚠️ Only {remaining} scripts left – ask Claude for more."
        try:
            info += "\nVoice: " + json.loads((STATE / "voice.json").read_text())["name"]
        except Exception:
            pass
        with open(final, "rb") as f:
            r = tg("sendVideo", data={"chat_id": chat, "caption": info[:1000], "supports_streaming": "true"}, files={"video": f})
        if r and not r.get("ok"):
            log.warning("sendVideo: %s", r)
        with open(cover, "rb") as f:
            tg("sendPhoto", data={"chat_id": chat, "caption": f"Cover for reel #{n}"}, files={"photo": f})
        tg("sendMessage", data={"chat_id": chat, "text": d.get("caption", "")[:4000]})
        hist["n"] = n
        hist["hooks"] = (hist["hooks"] + [d.get("hook_summary", "")])[-60:]
        hist["used"] = hist.get("used", []) + [d["idx"]]
        hist["themes"] = (hist.get("themes", []) + [tname])[-10:]
        HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=1))
        log.info("done: %s", final)
    except Exception as e:
        log.exception("promo reel failed")
        tg("sendMessage", data={"chat_id": tg_chat(), "text": f"⚠️ Promo reel autopilot failed: {str(e)[:500]}"})
        raise


if __name__ == "__main__":
    main()
