"""Step 4 – pick matching background clips, add captions + music, render the 9:16 Short."""
import random
import subprocess
from pathlib import Path

from .common import CLIPS_DIR, FONT_DIR, MUSIC_DIR, config, log
from .library import load_index, save_index

W, H = 1080, 1920


# ---------------- clip picking ------------------------------------------------
def pick_clips(lines: list[dict]) -> list[tuple[str, float]]:
    idx = [c for c in load_index() if c.get("ok")]
    if len(idx) < 10:
        raise RuntimeError("clip library is empty – run build_library.sh first")
    used_now: set[str] = set()
    plan = []

    def candidates(tag: str, t0: float):
        pool = [c for c in idx if c["file"] not in used_now]
        if t0 < 8:                                  # YouTube: no graphic violence in first 7 s
            pool = [c for c in pool if not c.get("graphic")]
        tagged = [c for c in pool if tag in c["tags"]]
        if tag == "jason_and_lucia":
            tagged += [c for c in pool if "jason" in c["tags"] or "lucia" in c["tags"]]
        return tagged or pool

    for line in lines:
        t, end = line["start"], line["end"]
        while end - t > 0.05:
            pool = candidates(line["tag"], t)
            # least-used clips first so the channel doesn't repeat the same shots
            pool.sort(key=lambda c: (c.get("uses", 0), random.random()))
            c = pool[0]
            seg = min(c["dur"], end - t, 3.2)       # fast cuts keep retention high
            if end - t - seg < 0.6:                 # avoid tiny leftover segments
                seg = min(c["dur"], end - t)
            if seg < 0.3:
                seg = end - t
            plan.append((c["file"], seg))
            used_now.add(c["file"])
            c["uses"] = c.get("uses", 0) + 1
            t += seg
    full = load_index()
    uses = {c["file"]: c.get("uses", 0) for c in idx}
    for c in full:
        if c["file"] in uses:
            c["uses"] = uses[c["file"]]
    save_index(full)
    return plan


# ---------------- captions (.ass) ----------------------------------------------
def _ts(t: float) -> str:
    h, rem = divmod(max(t, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _font() -> tuple[str, str]:
    anton = FONT_DIR / "Anton-Regular.ttf"
    if anton.exists():
        return "Anton", str(FONT_DIR)
    return "DejaVu Sans", "/usr/share/fonts/truetype/dejavu"


def write_ass(words: list[dict], total: float, badge: str, path: Path):
    cfg = config()
    font, _ = _font()
    base, hi, per = cfg["caption_color"], cfg["caption_highlight"], cfg["caption_words_per_line"]
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},104,{base},{base},&H00000000,&H90000000,1,0,0,0,100,100,2,0,1,7,3,5,60,60,0,1
Style: Badge,{font},58,&H00FFFFFF,&H00FFFFFF,&H000000FF,&H000000FF,1,0,0,0,100,100,3,0,3,14,0,8,60,60,140,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = [f"Dialogue: 1,{_ts(0)},{_ts(total)},Badge,,0,0,0,,{badge}"]
    groups = [words[i:i + per] for i in range(0, len(words), per)]
    for gi, g in enumerate(groups):
        g_end = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else total
        for wi, w in enumerate(g):
            end = g[wi + 1]["start"] if wi + 1 < len(g) else g_end
            parts = []
            for k, x in enumerate(g):
                txt = x["w"].upper().replace("{", "").replace("}", "")
                if k == wi:
                    parts.append(r"{\c" + hi + r"&\fscx112\fscy112}" + txt + r"{\c" + base + r"&\fscx100\fscy100}")
                else:
                    parts.append(txt)
            pop = r"{\pos(540,1240)}" + (r"{\t(0,80,\fscx100\fscy100)}" if wi == 0 else "")
            ev.append(f"Dialogue: 0,{_ts(w['start'])},{_ts(end)},Cap,,0,0,0,,{pop}{' '.join(parts)}")
    path.write_text(head + "\n".join(ev) + "\n", encoding="utf-8")


# ---------------- final render -------------------------------------------------
def render(lines, words, voice_mp3: str, total: float, badge: str, out: Path, work: Path):
    cfg = config()
    plan = pick_clips(lines)
    ass = work / "captions.ass"
    write_ass(words, total, badge, ass)
    _, fontdir = _font()

    cmd = ["ffmpeg", "-y", "-v", "error"]
    for f, seg in plan:
        cmd += ["-t", f"{seg + 0.05:.3f}", "-i", str(CLIPS_DIR / f)]
    cmd += ["-i", voice_mp3]
    music = sorted(MUSIC_DIR.glob("*.mp3")) + sorted(MUSIC_DIR.glob("*.m4a"))
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(random.choice(music))]

    fl = []
    for i, (_, seg) in enumerate(plan):
        z = random.choice([0.05, 0.07, -0.05])           # slow push-in / pull-out
        a, b = (1.0, 1 + z) if z > 0 else (1 - z, 1.0)
        fl.append(f"[{i}:v]trim=duration={seg:.3f},setpts=PTS-STARTPTS,"
                  f"scale=w='trunc(1080*({a}+({b}-{a})*t/{seg:.3f})/2)*2':h=-2:eval=frame,"
                  f"crop={W}:{H},setsar=1,fps=30,format=yuv420p[v{i}]")
    fl.append("".join(f"[v{i}]" for i in range(len(plan))) + f"concat=n={len(plan)}:v=1:a=0[cat]")
    ass_esc = str(ass).replace(":", r"\:")
    fl.append(f"[cat]subtitles='{ass_esc}':fontsdir='{fontdir}'[vout]")
    vi = len(plan)
    if music:
        fl.append(f"[{vi + 1}:a]volume={cfg['music_volume']},atrim=0:{total:.2f},"
                  f"afade=t=out:st={max(total - 1.5, 0):.2f}:d=1.5[m]")
        fl.append(f"[{vi}:a][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5[aout]")
    else:
        fl.append(f"[{vi}:a]loudnorm=I=-14:TP=-1.5[aout]")

    cmd += ["-filter_complex", ";".join(fl), "-map", "[vout]", "-map", "[aout]",
            "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out)]
    log.info("rendering %d cuts, %.1fs", len(plan), total)
    subprocess.run(cmd, check=True)
    return out
