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

from .common import CLIPS_DIR, MUSIC_DIR, config, log
from .library import load_index, save_index
from .pill import make_pill
from .sfx import path as sfx

W, H, FPS = 1080, 1920, 30
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an"]


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr[-1500:]}")


# ---------------- clip picking --------------------------------------------------
class ClipPicker:
    def __init__(self):
        self.idx = [c for c in load_index() if c.get("ok")]
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
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{off:.2f}", "-t", f"{dur + 0.2:.3f}",
           "-i", str(CLIPS_DIR / clip["file"])]
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
    """News 'proof': article screenshot on a blurred dark background, headline highlight wipes in."""
    cmd = ["ffmpeg", "-y", "-v", "error", "-t", f"{dur + 0.2:.3f}", "-i", str(CLIPS_DIR / bg["file"]),
           "-loop", "1", "-t", f"{dur + 0.2:.3f}", "-i", str(plain),
           "-loop", "1", "-t", f"{dur + 0.2:.3f}", "-i", str(hi)]
    z = f"(1+0.06*t/{dur:.3f})"
    fl = (f"[0:v]setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H},boxblur=25:2,eq=brightness=-0.25,setsar=1,"
          f"tpad=stop_mode=clone:stop_duration=1[bg];"
          f"[1:v]scale=920:-2,format=rgba[p];"
          f"[2:v]scale=920:-2,format=rgba,fade=in:st=0.45:d=0.3:alpha=1[h];"
          f"[bg][p]overlay=(W-w)/2:(H-h)/2[b1];[b1][h]overlay=(W-w)/2:(H-h)/2,"
          f"scale=w='trunc({W}*{z}/2)*2':h=-2:eval=frame,crop={W}:{H},format=yuv420p[vout]")
    _run(cmd + ["-filter_complex", fl, "-map", "[vout]", "-frames:v", str(round(dur * FPS))] + ENC + [str(out)])


# ---------------- audio ----------------------------------------------------------
def _music(total: float, work: Path) -> Path:
    tracks = sorted(MUSIC_DIR.glob("*.mp3")) + sorted(MUSIC_DIR.glob("*.m4a")) + sorted(MUSIC_DIR.glob("*.wav"))
    if tracks:
        return random.choice(tracks)
    from .beat import make_beat
    return make_beat(work / "beat.wav", total + 2, seed=random.randint(0, 999), bpm=random.choice([130, 140, 145]))


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
           article: tuple[Path, Path] | None = None):
    picker = ClipPicker()
    shots, events = [], [(0.0, "boom", 0.8)]
    frame_t = 0                      # frames already placed (keeps picture in sync with voice)
    n = 0

    def place(dur_target_end: float):
        nonlocal frame_t
        f_end = round(dur_target_end * FPS)
        d = (f_end - frame_t) / FPS
        frame_t = f_end
        return d

    for li, line in enumerate(lines):
        start, end = line["start"], line["end"]
        pill = None
        if line["label"]:
            pill = make_pill(line["label"], work / f"pill_{li}.png",
                             size=118 if line["big"] else 84, max_w=980 if line["big"] else 860)
        if li > 0:
            events.append((start, "whoosh", 0.35))
        if pill is not None:
            events.append((start + 0.03, "ding" if line["big"] else "pop", 0.45 if line["big"] else 0.6))

        t = start
        first = True
        # hook: split screen for up to 3 s
        if li == 0:
            seg_end = min(end, 3.0)
            d = place(seg_end)
            p = work / f"shot_{n:03d}.mp4"; n += 1
            shot_hook(picker.pick(line["tag"], 0, d), picker.pick("city_skyline", 0, d), d, pill, p)
            shots.append(p)
            t, first = seg_end, False
        # article proof shot
        if line["visual"] == "article" and article and t < end - 0.5:
            seg_end = min(end, t + 4.0)
            d = place(seg_end)
            p = work / f"shot_{n:03d}.mp4"; n += 1
            shot_article(picker.pick("any", t, 1), article[0], article[1], d, p)
            events.append((t, "click", 0.7))
            shots.append(p)
            t, first = seg_end, False
            pill = None              # the article itself carries the text
        # fast gameplay cuts
        while end - t > 0.05:
            seg = random.uniform(0.9, 2.0)
            if end - (t + seg) < 0.6:
                seg = end - t
            seg_end = min(end, t + seg)
            d = place(seg_end)
            if d <= 0:
                t = seg_end
                continue
            p = work / f"shot_{n:03d}.mp4"; n += 1
            shot_clip(picker.pick(line["tag"], t, d), d, p, punch=True, pill=pill,
                      pill_y=960 if line["big"] else 1010, pop=first)
            shots.append(p)
            t, first = seg_end, False
    picker.save()

    video = work / "video.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for p in shots:
        cmd += ["-i", str(p)]
    fl = "".join(f"[{i}:v]settb=1/{FPS},setpts=N/{FPS}/TB[c{i}];" for i in range(len(shots)))
    fl += "".join(f"[c{i}]" for i in range(len(shots))) + f"concat=n={len(shots)}:v=1:a=0[v]"
    _run(cmd + ["-filter_complex", fl, "-map", "[v]", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                "-pix_fmt", "yuv420p", "-r", str(FPS), "-profile:v", "high", str(video)])
    audio = mix_audio(voice_mp3, total, events, work)
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a",
          "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out)])
    log.info("rendered %d shots, %.1fs", len(shots), total)
    return out
