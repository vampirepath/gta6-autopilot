"""GTA 6 Super Clipper promo-reel autopilot.

script (Claude script bank)  ->  voice (free VoxCPM2, your chosen voice)  ->  animated reel (HTML engine + Chrome)
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
CTAS = [("Agar tumhe bhi ye app chahiye, toh mujhe follow karo, link meri bio mein hai.",
         "अगर तुम्हें भी ये ऐप चाहिए, तो मुझे फ़ॉलो करो, लिंक मेरी बायो में है।"),
        ("Ye app chahiye? Toh abhi follow karo, link meri bio mein hai.",
         "ये ऐप चाहिए? तो अभी फ़ॉलो करो, लिंक मेरी बायो में है।"),
        ("App chahiye toh mujhe follow karo, link bio mein hai.",
         "ऐप चाहिए तो मुझे फ़ॉलो करो, लिंक बायो में है।")]
PERMS = [("Aur haan, sirf unhi streamers ko clip karna jo clipping ki permission dete hain.",
          "और हाँ, सिर्फ़ उन्हीं स्ट्रीमर्स को क्लिप करना जो क्लिपिंग की परमिशन देते हैं।"),
         ("Bas yaad rakhna, sirf wahi streamers chunna jo clipping allow karte hain.",
          "बस याद रखना, सिर्फ़ वही स्ट्रीमर्स चुनना जो क्लिपिंग अलाउ करते हैं।")]
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
    c, cd = random.choice(CTAS)
    pm, pd = random.choice(PERMS)
    beats.append({"text": c, "deva": cd, "scene": "cta", "params": {}, "cues": ["follow", "link"]})
    beats.append({"text": pm, "deva": pd, "scene": "permission", "params": {}, "cues": []})
    feats = random.sample(FEATS, 5)
    cap = (f"{s['cap']}\n\nNo laptop, no editing. Just paste a live stream link and the app does the rest 😎\n\n" + "\n".join(feats) +
           "\n\nWant the app? Follow me 👉 link in bio 🔗\n\n⚠️ Only clip streamers who allow clipping, and always give credit 🙏\n"
           "Not affiliated with Rockstar Games.\n\n" + " ".join(random.sample(TAGS, 14)))
    d = {"idx": i, "hook_summary": beats[0]["text"], "beats": beats, "caption": cap, "cover": s.get("cover") or {}}
    return d, len(left) - 1


# ---------------------------------------------------------------- voice
EL = "https://api.elevenlabs.io/v1"


VIRAJ = "FmBhnvP58BK0vz65OOj7"   # "Viraj - Energetic, Clear Narrator" – same voice as in your ElevenLabs Studio


def voice_id(key):
    vf = STATE / "voice.json"
    if env("PROMO_VOICE_ID"):
        return env("PROMO_VOICE_ID")
    return VIRAJ
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



VIRAJ_SOFT = "P1bg08DkjqiVEzOn76yG"   # "Viraj - Rich and Soft" (your current ElevenLabs voice)


def make_voice_el(beats, work):
    key = env("PROMO_ELEVENLABS_API_KEY") or env("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("no ElevenLabs key")
    text = " ".join(" ".join(b["text"].split()) for b in beats)
    vid = env("PROMO_VOICE_ID") or VIRAJ_SOFT
    r = None
    for model in ("eleven_v4", "eleven_multilingual_v2"):
        r = requests.post(f"{EL}/text-to-speech/{vid}/with-timestamps", params={"output_format": "mp3_44100_128"},
                          headers={"xi-api-key": key}, timeout=240,
                          json={"text": text, "model_id": model,
                                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "use_speaker_boost": True}})
        if r.status_code == 200:
            log.info("voice: ElevenLabs %s", model)
            break
        log.warning("ElevenLabs %s error %s: %s", model, r.status_code, r.text[:300])
        if "quota" in r.text or r.status_code in (401, 402):
            break
    if r is None or r.status_code != 200:
        raise RuntimeError(f"ElevenLabs {r.status_code if r is not None else '?'}: {r.text[:160] if r is not None else ''}")
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
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", work / "raw.mp3", "-ac", "1", "-ar", "48000", work / "raw.wav"], check=True)
    x, sr = sf.read(work / "raw.wav")
    keep, shift, segs, prev_end, out = 0.12, 0.0, [], 0.0, []
    for w, s, e in words:                       # remove pauses longer than ~0.25 s ("no gaps")
        gap = s - prev_end
        if gap > 0.25 and out:
            segs.append((prev_end + keep / 2, s - keep / 2)); shift += gap - keep
        out.append([w, s - shift, e - shift]); prev_end = e
    mask = np.ones(len(x), bool)
    for a, b in segs:
        mask[int(a * sr):int(b * sr)] = False
    y = x[mask][: int((out[-1][2] + 0.3) * sr)]
    sf.write(work / "tight.wav", y, sr)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", work / "tight.wav", "-af",
                    f"atempo={TEMPO},highpass=f=80,lowpass=f=15000,afftdn=nf=-25,equalizer=f=180:t=q:w=1:g=2,equalizer=f=3200:t=q:w=1.2:g=3,"
                    "deesser=i=0.4,acompressor=threshold=-20dB:ratio=3.5:attack=5:release=80:makeup=4,loudnorm=I=-16:TP=-1.5:LRA=9",
                    "-ar", "48000", "-ac", "1", work / "vo.wav"], check=True)
    W = [{"w": w, "s": round(s / TEMPO, 3), "e": round(e / TEMPO, 3)} for w, s, e in out]
    return W, len(sf.read(work / "vo.wav")[0]) / 48000, credits_left(key)


# ---------------- free voice: VoxCPM2 (Apache-2.0, commercial use OK – the engine inside VoiceStudio) ----------------
VOICE_REF = STATE / "voice_ref.wav"   # the voice you picked ("2_clone_hindi"); every reel clones it so they all sound the same
VOICE_DESC = "(A young Indian man in his twenties, energetic and excited, clear upbeat social media narrator voice)"


def _trim(w, sr, thr=0.012):
    e = np.convolve(np.abs(w), np.ones(int(sr * .02)) / int(sr * .02), "same")
    idx = np.where(e > thr)[0]
    if not len(idx):
        return w
    a, b = max(0, idx[0] - int(sr * .03)), min(len(w), idx[-1] + int(sr * .06))
    return w[a:b]


def make_voice_beats(beats, work):
    from voxcpm import VoxCPM
    t0 = time.time()
    m = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False, optimize=False, device="cpu")
    sr = m.tts_model.sample_rate
    if not VOICE_REF.exists():
        log.warning("no saved voice – designing a new one")
        w = m.generate(text=VOICE_DESC + beats[0]["deva"], inference_timesteps=10, cfg_value=2.0)
        sf.write(VOICE_REF, w, sr)
    gap = np.zeros(int(sr * 0.12), dtype=np.float32)
    parts, W, cur = [], [], 0.0
    for k, bt in enumerate(beats):
        w = None
        for attempt in range(2):
            try:
                w = m.generate(text=bt["deva"], reference_wav_path=str(VOICE_REF), inference_timesteps=10, cfg_value=2.0)
                break
            except Exception as e:
                log.warning("voice beat %d failed (%s) – retrying", k, e)
        if w is None:
            raise RuntimeError(f"voice failed for beat {k}")
        w = _trim(np.asarray(w, dtype=np.float32), sr)
        dur = len(w) / sr
        log.info("voice beat %d/%d: %.1fs (%.0fs elapsed)", k + 1, len(beats), dur, time.time() - t0)
        # spread the Roman (caption) words over this beat's audio by word length
        words = bt["text"].split()
        wts = [max(1.0, len(re.sub(r"[^A-Za-z0-9]", "", x)) * .55 + .6) for x in words]
        tot, acc = sum(wts), cur
        for x, wt in zip(words, wts):
            d = dur * wt / tot
            W.append({"w": x, "s": round(acc, 3), "e": round(acc + d, 3)}); acc += d
        parts += [w, gap]; cur += dur + len(gap) / sr
    y = np.concatenate(parts)
    sf.write(work / "raw.wav", y, sr)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", work / "raw.wav", "-af",
                    "highpass=f=80,lowpass=f=15000,equalizer=f=180:t=q:w=1:g=2,equalizer=f=3200:t=q:w=1.2:g=3,"
                    "deesser=i=0.4,acompressor=threshold=-20dB:ratio=3.5:attack=5:release=80:makeup=4,loudnorm=I=-16:TP=-1.5:LRA=9",
                    "-ar", "48000", "-ac", "1", work / "vo.wav"], check=True)
    return W, len(y) / sr


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



# ---------------- editing styles: a different look (fonts, background, colours) every reel ----------------
F = "f/"
SKINS = {
 "Paper Notebook": dict(fonts=dict(B="bricolage-grotesque-latin-800-normal", H="bricolage-grotesque-latin-800-normal", S="instrument-serif-latin-400-italic", C="caveat-latin-700-normal"),
    bg="#f3eee3", pat="radial-gradient(#141414 1.6px,transparent 1.7px)", patsz="44px 44px", patop=".11", grain=".18", headc="#141414", ink="#141414", line="#141414",
    card="#ffffff", acc="#ff4a1c", hl="#ffe14a", onhl="#141414", blu="#2f6bff", grn="#21c46b", sh="#141414", rad="26px", hw="800", hlh=".98", hls="-.035em", htt="none", w1="#141414", w2="#ff4a1c", capbg="#ffffff", capc="#141414"),
 "Neon Night": dict(fonts=dict(B="space-grotesk-latin-700-normal", H="anton", S="dm-serif-display-latin-400-italic", C="permanent-marker-latin-400-normal"),
    bg="radial-gradient(70% 50% at 50% 30%,#1b1446,#0a0b1f 70%)", pat="linear-gradient(rgba(46,242,255,.35) 1px,transparent 1px),linear-gradient(90deg,rgba(46,242,255,.35) 1px,transparent 1px)", patsz="90px 90px", patop=".25", grain=".05", headc="#ffffff", ink="#0a0b1f", line="#0a0b1f",
    card="#ffffff", acc="#ff2e88", hl="#2ef2ff", onhl="#0a0b1f", blu="#7c4dff", grn="#18d47b", sh="#ff2e88", rad="18px", hw="400", hlh="1.0", hls=".005em", htt="uppercase", w1="#2ef2ff", w2="#ff2e88", capbg="#0a0b1f", capc="#ffffff"),
 "Comic Pop": dict(fonts=dict(B="archivo-black-latin-400-normal", H="bangers-latin-400-normal", S="bangers-latin-400-normal", C="permanent-marker-latin-400-normal"),
    bg="#ffd400", pat="radial-gradient(#e8212b 3px,transparent 3.5px)", patsz="34px 34px", patop=".22", grain=".08", headc="#111111", ink="#111111", line="#111111",
    card="#ffffff", acc="#e8212b", hl="#4fc3ff", onhl="#111111", blu="#1e5bff", grn="#16b85a", sh="#111111", rad="8px", hw="400", hlh="1.0", hls=".03em", htt="uppercase", w1="#111111", w2="#e8212b", capbg="#ffffff", capc="#111111"),
 "Clean Mono": dict(fonts=dict(B="space-grotesk-latin-700-normal", H="space-grotesk-latin-700-normal", S="dm-serif-display-latin-400-italic", C="caveat-latin-700-normal"),
    bg="#fafafa", pat="linear-gradient(#e6e6e6 1px,transparent 1px),linear-gradient(90deg,#e6e6e6 1px,transparent 1px)", patsz="60px 60px", patop=".9", grain=".0", headc="#0a0a0a", ink="#0a0a0a", line="#0a0a0a",
    card="#ffffff", acc="#2f5bff", hl="#d7ff3a", onhl="#0a0a0a", blu="#2f5bff", grn="#11b866", sh="#2f5bff", rad="30px", hw="700", hlh="1.0", hls="-.04em", htt="none", w1="#0a0a0a", w2="#2f5bff", capbg="#0a0a0a", capc="#ffffff"),
 "Vice Sunset": dict(fonts=dict(B="righteous-latin-400-normal", H="righteous-latin-400-normal", S="dm-serif-display-latin-400-italic", C="permanent-marker-latin-400-normal"),
    bg="linear-gradient(180deg,#2b0a3d 0%,#7a1f6b 45%,#ff5f8f 75%,#ffb36b 100%)", pat="repeating-linear-gradient(0deg,rgba(255,255,255,.12) 0 2px,transparent 2px 22px)", patsz="auto", patop=".6", grain=".06", headc="#ffffff", ink="#2b0a3d", line="#2b0a3d",
    card="#ffffff", acc="#ff2e88", hl="#29f2ff", onhl="#2b0a3d", blu="#6a4cff", grn="#18d47b", sh="#2b0a3d", rad="22px", hw="400", hlh="1.0", hls=".01em", htt="uppercase", w1="#29f2ff", w2="#ff2e88", capbg="#ffffff", capc="#2b0a3d"),
 "Kraft Marker": dict(fonts=dict(B="archivo-black-latin-400-normal", H="archivo-black-latin-400-normal", S="dm-serif-display-latin-400-italic", C="permanent-marker-latin-400-normal"),
    bg="#c9a27a", pat="radial-gradient(rgba(60,30,10,.35) 1.2px,transparent 1.4px)", patsz="18px 18px", patop=".5", grain=".35", headc="#2a1a0e", ink="#2a1a0e", line="#2a1a0e",
    card="#fff8ec", acc="#d7261e", hl="#fff3a0", onhl="#2a1a0e", blu="#1d4ed8", grn="#2f8f46", sh="#2a1a0e", rad="6px", hw="400", hlh="1.02", hls="-.02em", htt="uppercase", w1="#2a1a0e", w2="#d7261e", capbg="#fff8ec", capc="#2a1a0e"),
 "Terminal Green": dict(fonts=dict(B="jetbrains-mono-latin-800-normal", H="jetbrains-mono-latin-800-normal", S="dm-serif-display-latin-400-italic", C="permanent-marker-latin-400-normal"),
    bg="#050805", pat="repeating-linear-gradient(0deg,rgba(57,255,106,.10) 0 2px,transparent 2px 6px)", patsz="auto", patop="1", grain=".05", headc="#39ff6a", ink="#06110a", line="#39ff6a",
    card="#eaffef", acc="#39ff6a", hl="#ffb000", onhl="#06110a", blu="#00c2ff", grn="#39ff6a", sh="#39ff6a", rad="4px", hw="800", hlh="1.0", hls="-.04em", htt="uppercase", w1="#39ff6a", w2="#ffb000", capbg="#06110a", capc="#39ff6a"),
}


def skin_css(sk):
    faces = "".join(f"@font-face{{font-family:{k};src:url({F}{v}.woff2);font-weight:100 900;font-style:normal}}" for k, v in sk["fonts"].items())
    vars_ = ";".join(f"--{k}:{v}" for k, v in sk.items() if k != "fonts")
    return faces + ":root{" + vars_ + ";--bgc:" + (sk["bg"] if sk["bg"].startswith("#") else "#000") + ";--mkc:" + sk["onhl"] + "}"

ENGINE_PAPER = HERE / "engine_paper"


def build_html(plan, W, skin, path):
    """Paper-engine reel with GTA 6 trailer hook, in one of the SKINS (fonts, background, colours)."""
    E = ENGINE_PAPER
    sk = SKINS.get(skin) or SKINS["Paper Notebook"]
    head = (E / "head.html").read_text().replace("/*SKIN*/", skin_css(sk))
    js_skin = "const SKIN=" + json.dumps({k: v for k, v in sk.items() if k != "fonts"}) + ";\n"
    html = head + js_skin + (E / "helpers.js").read_text() + "\nconst PLAN=" + json.dumps(plan, ensure_ascii=False) + ";\n" \
        + (E / "templates.js").read_text() + "\n" + (E / "tail.html").read_text()
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


def mix(work, plan, dur, seed, skin=""):
    rng = np.random.default_rng(seed)
    progs = [[[41, [65, 69, 72, 76]], [38, [62, 65, 69, 72]], [46, [65, 70, 74, 77]], [36, [64, 67, 70, 74]]],
             [[45, [69, 72, 76, 79]], [41, [65, 69, 72, 76]], [43, [67, 71, 74, 77]], [40, [64, 67, 71, 74]]],
             [[43, [67, 71, 74, 78]], [40, [64, 67, 71, 74]], [36, [64, 67, 71, 72]], [38, [62, 66, 69, 72]]],
             [[38, [62, 65, 69, 72]], [43, [65, 67, 71, 74]], [36, [64, 67, 71, 76]], [45, [64, 67, 69, 72]]]]
    drop = plan[1]["s"] if len(plan) > 1 and plan[1]["s"] > 1.2 else 3.0
    cfg = {"D": dur + 0.5, "seed": int(seed), "bpm": int(rng.integers(116, 128)), "prog": progs[int(rng.integers(0, 4))],
           "drop": round(drop, 2), "end": round(dur + 0.2, 2), "sfx": sfx_events(plan, dur, rng)}
    (work / "music.json").write_text(json.dumps(cfg))
    engine = "music.py" if skin in ("Neon Night", "Terminal Green", "Vice Sunset") else "music_house.py"   # trap beat for dark styles, house for light
    if engine == "music.py":
        cfg["bpm"] = int(rng.integers(128, 146))
        (work / "music.json").write_text(json.dumps(cfg))
    subprocess.run([sys.executable, HERE / engine, work / "music.json", work / "vo.wav", work / "music.wav", work / "sfx.wav"], check=True)


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
        voice_note, left = "ElevenLabs Viraj", None
        try:
            W, dur, left = make_voice_el(d["beats"], work)
        except Exception as ex:
            log.warning("ElevenLabs failed (%s) – using the free voice", ex)
            voice_note = f"free voice (ElevenLabs: {str(ex)[:80]})"
            W, dur = make_voice_beats(d["beats"], work)
        plan = make_plan(d["beats"], W, dur)
        (work / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1))
        recent = hist.get("skins", [])[-3:]
        tname = random.choice([s for s in SKINS if s not in recent])
        theme = tname
        html = ASSETS / "_reel.html"
        build_html(plan, W, theme, html)
        render(html, work / "video.mp4", dur + 0.5)
        mix(work, plan, dur, seed=int(time.time()) % 100000, skin=tname)
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
        info = f"🎬 Promo reel #{n} ready ({dur:.0f}s · {tname} style)\nHook: {d.get('hook_summary', '')[:200]}"
        if remaining <= 6:
            info += f"\n⚠️ Only {remaining} scripts left – ask Claude for more."
        info += f"\nVoice: {voice_note}"
        if left is not None:
            info += f"\nElevenLabs credits left: {left:,}"
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
        hist["skins"] = (hist.get("skins", []) + [tname])[-10:]
        HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=1))
        log.info("done: %s", final)
    except Exception as e:
        log.exception("promo reel failed")
        tg("sendMessage", data={"chat_id": tg_chat(), "text": f"⚠️ Promo reel autopilot failed: {str(e)[:500]}"})
        raise


if __name__ == "__main__":
    main()
