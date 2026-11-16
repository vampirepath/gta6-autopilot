"""Step 4 – edit the Short like top GTA news channels.

 • 0–3 s hook: split screen (two gameplay shots) + glowing purple hook label + boom
 • fast cuts every ~1–2 s with a punch-zoom on every cut
 • purple glowing key-phrase labels that pop in (with pop + whoosh SFX)
 • big full-width callouts for dates / money / numbers (+ ding)
 • article "proof" shots with the headline highlighted (+ camera click)
 • background beat under the voice, gently ducked while talking
"""
import random
import subprocess
from pathlib import Path

from .common import CLIPS_DIR, FONT_DIR, MUSIC_DIR, config, log
from .library import STILLS_DIR, load_index, load_stills, save_index
from .pill import make_pill
from .sfx import path as sfx, pick as sfx_pick

W, H, FPS = 1080, 1920, 30
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an"]


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr[-1500:]}")


# ---------------- clip picking --------------------------------------------------
class ClipPicker:
    def __init__(self):
        self.idx = [c for c in load_index() if c.get("ok") and "Cover_Art" not in c.get("source", "")
                    and "Pre_Load" not in c.get("source", "")]
        if len(self.idx) < 10:
            raise RuntimeError("clip library is empty – run the 'Build clip library' workflow first")
        self.used = set()

    def pick(self, tag: str, t0: float, min_dur: float) -> dict:
        pool = [c for c in self.idx if c["file"] not in self.used]
        if len(pool) < 5:
            self.used.clear()
            pool = self.idx[:]
        if t0 < 8:                                   # YouTube: no graphic violence in the first seconds
            pool = [c for c in pool if not c.get("graphic")] or pool
        long_enough = [c for c in pool if c["dur"] >= min_dur] or pool
        tagged = [c for c in long_enough if tag in c.get("tags", [])]
        if tag == "jason_and_lucia":
            tagged += [c for c in long_enough if {"jason", "lucia"} & set(c.get("tags", []))]
        choice_pool = tagged or long_enough
        choice_pool.sort(key=lambda c: (c.get("uses", 0), random.random()))
        c = choice_pool[0]
        self.used.add(c["file"])
        c["uses"] = c.get("uses", 0) + 1
        return c

    def save(self):
        uses = {c["file"]: c.get("uses", 0) for c in self.idx}
        full = load_index()
        for c in full:
            if c["file"] in uses:
                c["uses"] = uses[c["file"]]
        save_index(full)


# ---------------- shot builders ---------------------------------------------------
def _zoom_expr(dur: float, punch: bool) -> str:
    """Punch-in on the cut (1.12 → 1.0 in 0.18 s) then a slow push-in."""
    slow = f"(1+0.04*t/{dur:.3f})"
    if punch:
        return f"if(lt(t,0.18),1.12-0.12*t/0.18,1)*{slow}"
    return slow


def _pill_filters(pill_in: int, base: str, y_center: int, pop: bool) -> str:
    if pop:   # 0.5 → 1.1 → 1.0 scale pop in 0.2 s
        s = "if(lt(t,0.12),0.5+5*t,if(lt(t,0.2),1.1-1.25*(t-0.12),1))"
        sc = f"[{pill_in}:v]format=rgba,scale=w='trunc(iw*{s}/2)*2':h=-2:eval=frame[pl]"
    else:
        sc = f"[{pill_in}:v]format=rgba[pl]"
    return f"{sc};[{base}][pl]overlay=x=(W-w)/2:y={y_center}-h/2:eval=frame:shortest=1[vout]"


def shot_clip(clip: dict, dur: float, out: Path, punch=True, pill: Path | None = None,
              pill_y=1000, pop=False):
    off = max(0.0, random.uniform(0, max(0.0, clip["dur"] - dur - 0.05)))
    src = clip["file"] if clip.get("abs") else str(CLIPS_DIR / clip["file"])
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{off:.2f}", "-t", f"{dur + 0.2:.3f}", "-i", src]
    z = _zoom_expr(dur, punch)
    fl = (f"[0:v]setpts=PTS-STARTPTS,fps={FPS},scale=w='trunc({W}*{z}/2)*2':h=-2:eval=frame,"
          f"crop={W}:{H},setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration=1[base]")
    if pill:
        cmd += ["-loop", "1", "-t", f"{dur + 0.2:.3f}", "-i", str(pill)]
        fl += ";" + _pill_filters(1, "base", pill_y, pop)
    else:
        fl += ";[base]null[vout]"
    _run(cmd + ["-filter_complex", fl, "-map", "[vout]", "-frames:v", str(round(dur * FPS))] + ENC + [str(out)])


def shot_hook(top: dict, bottom: dict, dur: float, pill: Path, out: Path):
    """Split screen: two gameplay shots stacked, hook label across the middle (like the reference)."""
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for c in (top, bottom):
        off = max(0.0, random.uniform(0, max(0.0, c["dur"] - dur - 0.05)))
        cmd += ["-ss", f"{off:.2f}", "-t", f"{dur + 0.2:.3f}", "-i", str(CLIPS_DIR / c["file"])]
    cmd += ["-loop", "1", "-t", f"{dur + 0.2:.3f}", "-i", str(pill)]
    half = H // 2
    z = f"(1+0.05*t/{dur:.3f})"
    fl = (f"[0:v]setpts=PTS-STARTPTS,fps={FPS},scale=w='trunc({W}*{z}/2)*2':h=-2:eval=frame,crop={W}:{half},setsar=1,tpad=stop_mode=clone:stop_duration=1[a];"
          f"[1:v]setpts=PTS-STARTPTS,fps={FPS},scale=w='trunc({W}*{z}/2)*2':h=-2:eval=frame,crop={W}:{half},setsar=1,tpad=stop_mode=clone:stop_duration=1[b];"
          f"[a][b]vstack,format=yuv420p[base];" + _pill_filters(2, "base", half, True))
    _run(cmd + ["-filter_complex", fl, "-map", "[vout]", "-frames:v", str(round(dur * FPS))] + ENC + [str(out)])


def shot_article(bg: dict, plain: Path, hi: Path, dur: float, out: Path):
    """News 'proof': article screenshot; a yellow highlighter sweeps across the key sentence, slow push-in."""
    from PIL import Image
    fdir = out.with_suffix("")
    fdir.mkdir(exist_ok=True)
    a = Image.open(plain).convert("RGB")
    b = Image.open(hi).convert("RGB").resize(a.size)
    tw = 940
    th = int(a.height * tw / a.width)
    a, b = a.resize((tw, th)), b.resize((tw, th))
    from PIL import ImageChops
    diff = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v > 24 else 0)
    box = diff.getbbox() or (0, 0, tw, th)
    n = round(dur * FPS)
    start, sweep = int(0.35 * FPS), int(0.7 * FPS)
    last = None
    for f in range(n):
        p = fdir / f"{f:04d}.png"
        if f < start + sweep + 1:
            prog = min(1, max(0, (f - start) / sweep))
            x = int(box[0] + (box[2] - box[0]) * prog)
            fr = a.copy()
            if x > box[0]:
                fr.paste(b.crop((box[0], box[1], x, box[3])), (box[0], box[1]))
            fr.save(p, compress_level=1)
            last = p
        else:
            p.write_bytes(last.read_bytes())
    cy = (box[1] + box[3]) / 2 / th
    cmd = ["ffmpeg", "-y", "-v", "error", "-t", f"{dur + 0.2:.3f}", "-i", str(CLIPS_DIR / bg["file"]),
           "-framerate", str(FPS), "-i", str(fdir / "%04d.png")]
    z = f"(1+0.10*t/{dur:.3f})"
    fl = (f"[0:v]setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H},boxblur=25:2,eq=brightness=-0.3,setsar=1,"
          f"tpad=stop_mode=clone:stop_duration=2[bg];"
          f"[bg][1:v]overlay=(W-w)/2:(H-h)/2:shortest=0,"
          f"scale=w='trunc({W}*{z}/2)*2':h=-2:eval=frame,"
          f"crop={W}:{H}:x='(iw-{W})/2':y='max(0,min(ih-{H},(ih-{H})*{cy:.3f}*1.0))',format=yuv420p[vout]")
    _run(cmd + ["-filter_complex", fl, "-map", "[vout]", "-frames:v", str(n)] + ENC + [str(out)])

class StillPicker:
    def __init__(self):
        self.stills = [x for x in load_stills() if (STILLS_DIR / x["file"]).exists()]
        self.used = set()

    def pick(self, subject: str) -> Path | None:
        pool = [x for x in self.stills if x["subject"].lower() == subject.lower()] or \
               [x for x in self.stills if subject.lower() in x["subject"].lower() or x["subject"].lower() in subject.lower()]
        fresh = [x for x in pool if x["file"] not in self.used] or pool
        if not fresh:
            return None
        x = random.choice(fresh)
        self.used.add(x["file"])
        return STILLS_DIR / x["file"]


def shot_still(img: Path, dur: float, out: Path, pill: Path | None = None, pill_y=1000, pop=False):
    """Ken-Burns pan across an official image / article photo (fills the 9:16 frame)."""
    direction = random.choice([1, -1])
    cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", f"{dur + 0.2:.3f}", "-i", str(img)]
    z = f"if(lt(t,0.18),1.18-0.12*t/0.18,1.06+0.04*t/{dur:.3f})"
    xexpr = f"(iw-{W})*({0.5 - 0.25 * direction}+{0.5 * direction}*t/{dur:.3f})"
    fl = (f"[0:v]fps={FPS},scale=w=-2:h='trunc({H}*{z}/2)*2':eval=frame,"
          f"crop={W}:{H}:x='max(0,min(iw-{W},{xexpr}))':y='(ih-{H})/2',setsar=1,format=yuv420p[base]")
    if pill:
        cmd += ["-loop", "1", "-t", f"{dur + 0.2:.3f}", "-i", str(pill)]
        fl += ";" + _pill_filters(1, "base", pill_y, pop)
    else:
        fl += ";[base]null[vout]"
    _run(cmd + ["-filter_complex", fl, "-map", "[vout]", "-frames:v", str(round(dur * FPS))] + ENC + [str(out)])


def shot_zoom(img: Path, dur: float, out: Path):
    """Centred zoom-in on a 9:16 image (maps)."""
    z = f"(1.0+0.22*min(1,t/{dur:.3f}))"
    cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", f"{dur + 0.2:.3f}", "-i", str(img)]
    fl = (f"[0:v]fps={FPS},scale=w='trunc({W}*{z}/2)*2':h=-2:eval=frame,crop={W}:{H},setsar=1,format=yuv420p[vout]")
    _run(cmd + ["-filter_complex", fl, "-map", "[vout]", "-frames:v", str(round(dur * FPS))] + ENC + [str(out)])


def shot_card(kind: str, params: dict, bg: dict, dur: float, out: Path, work: Path):
    """Infographic card animating over darkened gameplay."""
    from .infographic import render_frames
    fdir = render_frames(kind, dur, work / f"card_{out.stem}", **params)
    off = max(0.0, random.uniform(0, max(0.0, bg["dur"] - dur - 0.05)))
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{off:.2f}", "-t", f"{dur + 0.2:.3f}", "-i", str(CLIPS_DIR / bg["file"]),
           "-framerate", str(FPS), "-i", str(fdir / "%04d.png")]
    fl = (f"[0:v]setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H},boxblur=8:1,eq=brightness=-0.22:saturation=0.8,setsar=1,"
          f"tpad=stop_mode=clone:stop_duration=2[bg];[1:v]format=rgba[c];"
          f"[bg][c]overlay=x=(W-w)/2:y=330:shortest=0,format=yuv420p[vout]")
    _run(cmd + ["-filter_complex", fl, "-map", "[vout]", "-frames:v", str(round(dur * FPS))] + ENC + [str(out)])


# ---------------- captions ---------------------------------------------------------
def _ts(t: float) -> str:
    h, rem = divmod(max(t, 0), 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{sec:05.2f}"


def write_captions(words: list[dict], total: float, path: Path):
    """Word-by-word captions: 3 words at a time, the spoken word turns yellow and pops."""
    per = config().get("caption_words_per_line", 3)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Anton,132,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,0,0,0,0,100,100,2,0,1,10,5,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    groups = [words[i:i + per] for i in range(0, len(words), per)]
    for gi, g in enumerate(groups):
        g_end = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else total
        for wi, w in enumerate(g):
            end = g[wi + 1]["start"] if wi + 1 < len(g) else g_end
            parts = []
            for k, x in enumerate(g):
                txt = x["w"].upper().replace("{", "").replace("}", "")
                if k == wi:
                    parts.append(r"{\c&H0040D8FF&\fscx115\fscy115}" + txt + r"{\c&H00FFFFFF&\fscx100\fscy100}")
                else:
                    parts.append(txt)
            ev.append(f"Dialogue: 0,{_ts(w['start'])},{_ts(end)},Cap,,0,0,0,,{{\\pos(540,1520)}}{' '.join(parts)}")
    path.write_text(head + "\n".join(ev) + "\n", encoding="utf-8")


# ---------------- audio ----------------------------------------------------------
def _music(total: float, work: Path) -> Path:
    tracks = sorted(MUSIC_DIR.glob("*.mp3")) + sorted(MUSIC_DIR.glob("*.m4a")) + sorted(MUSIC_DIR.glob("*.wav"))
    if tracks:
        return random.choice(tracks)
    from .beat import make_beat, make_synthwave
    style = config().get("music_style", "synthwave")
    if style == "trap":
        return make_beat(work / "beat.wav", total + 2, seed=random.randint(0, 999), bpm=random.choice([130, 140, 145]))
    return make_synthwave(work / "beat.wav", total + 2, seed=random.randint(0, 999), bpm=random.choice([100, 104, 108]))


def mix_audio(voice: str, total: float, events: list[tuple[float, str, float]], work: Path) -> Path:
    cfg = config()
    out = work / "mix.m4a"
    music = _music(total, work)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", voice, "-stream_loop", "-1", "-i", str(music)]
    fl = [f"[0:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-15:TP=-1.5,aresample=48000,apad=whole_dur={total:.2f},asplit=2[v][vsc]",
          f"[1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.2f},volume={cfg.get('music_volume', 0.22)},"
          f"afade=t=out:st={max(total - 1.5, 0):.2f}:d=1.5[m0]",
          "[m0][vsc]sidechaincompress=threshold=0.05:ratio=4:attack=20:release=300[m]"]
    labels = ["[v]", "[m]"]
    for i, (t, name, gain) in enumerate(events):
        cmd += ["-i", str(sfx(name))]
        k = i + 2
        ms = max(0, int(t * 1000))
        fl.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,volume={gain},adelay={ms}|{ms}[s{i}]")
        labels.append(f"[s{i}]")
    fl.append("".join(labels) + f"amix=inputs={len(labels)}:duration=longest:normalize=0,"
              f"alimiter=limit=0.95,atrim=0:{total:.2f},aresample=48000[aout]")
    _run(cmd + ["-filter_complex", ";".join(fl), "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(out)])
    return out


# ---------------- main ---------------------------------------------------------------
def render(lines, words, voice_mp3: str, total: float, badge: str, out: Path, work: Path,
           article: tuple[Path, Path] | None = None, photo: Path | None = None):
    picker, stills = ClipPicker(), StillPicker()
    shots, events = [], [(0.0, "impact2", 0.8), (0.0, "boom", 0.5)]
    frame_t = 0
    n = 0
    LABEL_Y, BIG_Y = 1010, 960

    def place(end_t: float):
        nonlocal frame_t
        f_end = round(end_t * FPS)
        d = (f_end - frame_t) / FPS
        frame_t = f_end
        return d

    def new_shot():
        nonlocal n
        p = work / f"shot_{n:03d}.mp4"
        n += 1
        shots.append(p)
        return p

    for li, line in enumerate(lines):
        start, end = line["start"], line["end"]
        vis = line.get("visual", "clip")
        pill = None
        if line["label"]:
            pill = make_pill(line["label"], work / f"pill_{li}.png",
                             size=124 if line["big"] else 96, max_w=990 if line["big"] else 920)
        if li > 0:
            lab = line["label"].upper()
            if any(w in lab for w in ("TWIST", "LEAK", "BUT ", "SECRET", "HACK", "BANNED", "BAN")):
                events.append((start, "glitch", 0.35))
            elif random.random() < 0.7:
                events.append((start, sfx_pick("whoosh"), 0.22))
        t, first = start, True

        # 1) hook – split screen (first ≤3 s)
        if li == 0:
            seg_end = min(end, 3.0)
            d = place(seg_end)
            shot_hook(picker.pick(line["tag"], 0, d), picker.pick("city_skyline", 0, d), d, pill, new_shot())
            events.append((0.03, "pop", 0.6))
            t, first = seg_end, False

        # 2) the line's main visual (≤4 s), then gameplay cuts keep the label on screen
        if t < end - 0.4 and vis != "clip":
            seg_end = min(end, t + 4.0)
            d = place(seg_end)
            done = False
            try:
                if vis in ("stat", "compare", "list", "quote", "person"):
                    shot_card(vis, line[vis] if vis != "list" else {"title": line["list"].get("title", line["label"]),
                                                                   "items": line["list"].get("items", [])},
                              picker.pick("any", t, d), d, new_shot(), work)
                    money = vis == "stat" and "$" in str(line["stat"].get("value", ""))
                    events.append((t + 0.02, sfx_pick("impact"), 0.45))
                    events.append((t + 0.05, "cash" if money else ("ding" if vis == "stat" else "pop"), 0.45))
                    if vis == "list":
                        events += [(t + 0.35 + k * 0.45, "pop", 0.4) for k in range(len(line["list"]["items"][:4]))]
                    done = True
                elif vis == "article" and article:
                    shot_article(picker.pick("any", t, 1), article[0], article[1], d, new_shot())
                    events.append((t, "shutter", 0.6))
                    events.append((t + 0.35, "typing", 0.45))
                    done = True
                elif vis == "map":
                    from .geomap import render_map
                    m = render_map(line["country"], work / f"map_{li}.jpg")
                    if m:
                        shot_zoom(m, d, new_shot())
                        events.append((t + 0.05, "ping", 0.5))
                        done = True
                elif vis == "stock":
                    from .stock import stock_clip
                    c = stock_clip(line.get("stock_query", ""), d, work / f"stock_{li}.mp4")
                    if c:
                        shot_clip(c, d, new_shot(), punch=True, pill=pill, pill_y=LABEL_Y, pop=True)
                        events.append((t + 0.03, "pop", 0.6))
                        done = True
                elif vis in ("subject", "photo", "ai"):
                    img = None
                    if vis == "subject":
                        subj_clips = [c for c in picker.idx if line["subject"] in c.get("subjects", [])]
                        if subj_clips and random.random() < 0.5:
                            c = random.choice(subj_clips)
                            shot_clip(c, d, new_shot(), punch=True, pill=pill, pill_y=LABEL_Y, pop=True)
                            done = True
                        else:
                            img = stills.pick(line["subject"])
                    elif vis == "photo":
                        img = photo
                    else:
                        from .aiimage import ai_image
                        img = ai_image(line["ai_prompt"], work / f"ai_{li}.jpg")
                    if img and not done:
                        shot_still(img, d, new_shot(), pill=pill, pill_y=LABEL_Y, pop=True)
                        done = True
                    if done:
                        events.append((t + 0.03, "swish" if vis == "subject" else "pop", 0.4))
            except Exception as e:
                log.warning("visual %s failed (%s) – using gameplay", vis, e)
                if shots and not shots[-1].exists():
                    shots.pop()
                done = False
            if done:
                t, first = seg_end, False
            else:
                frame_t = round(t * FPS)       # undo the placement, fall back to gameplay below
        elif pill is not None and li > 0:
            events.append((start + 0.03, "ding" if line["big"] else "pop", 0.45 if line["big"] else 0.6))

        # 3) fast gameplay cuts for the rest of the line
        while end - t > 0.05:
            seg = random.uniform(0.9, 2.0)
            if end - (t + seg) < 0.6:
                seg = end - t
            seg_end = min(end, t + seg)
            d = place(seg_end)
            if d <= 0:
                t = seg_end
                continue
            shot_clip(picker.pick(line["tag"], t, d), d, new_shot(), punch=True, pill=pill,
                      pill_y=BIG_Y if line["big"] else LABEL_Y, pop=first)
            t, first = seg_end, False
    picker.save()

    # join shots (exact frame timing) + burn word-by-word captions
    caps = work / "captions.ass"
    write_captions(words, total, caps)
    video = work / "video.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for p in shots:
        cmd += ["-i", str(p)]
    fl = "".join(f"[{i}:v]settb=1/{FPS},setpts=N/{FPS}/TB[c{i}];" for i in range(len(shots)))
    cap_esc = str(caps).replace(":", r"\:")
    fl += "".join(f"[c{i}]" for i in range(len(shots))) + f"concat=n={len(shots)}:v=1:a=0[cat];"
    fl += f"[cat]subtitles='{cap_esc}':fontsdir='{FONT_DIR}'[v]" if config().get("word_captions", True) else "[cat]null[v]"
    _run(cmd + ["-filter_complex", fl, "-map", "[v]", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                "-pix_fmt", "yuv420p", "-r", str(FPS), "-profile:v", "high", str(video)])
    audio = mix_audio(voice_mp3, total, events, work)
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a",
          "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out)])
    log.info("rendered %d shots, %.1fs", len(shots), total)
    return out
