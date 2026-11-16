"""Animated infographic cards (rendered frame by frame with Pillow, overlaid by ffmpeg).

  stat     – big number that counts up + caption        ("$7.6 BILLION" / "expected revenue")
  compare  – two bars that grow                          (GTA 5 map vs GTA 6 map)
  list     – up to 4 points that tick in one by one
  quote    – quote card with who said it
"""
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .common import FONT_DIR

FONT = str(FONT_DIR / "Anton-Regular.ttf")
BODY = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
PURPLE, PURPLE2, PINK, GOLD, WHITE = (150, 26, 190), (196, 64, 230), (255, 92, 200), (255, 214, 64), (255, 255, 255)
CW, CH = 1000, 1100           # card canvas size
FPS = 30


def _f(size, body=False):
    try:
        return ImageFont.truetype(BODY if body else FONT, size)
    except OSError:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)


def _ease(x):  # easeOutBack-ish
    x = max(0.0, min(1.0, x))
    return 1 + 2.2 * (x - 1) ** 3 + 1.2 * (x - 1) ** 2


def _ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _panel(img, box, radius=34, glow=True):
    d = ImageDraw.Draw(img)
    if glow:
        g = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).rounded_rectangle(box, radius, fill=(214, 80, 255, 150))
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(26)))
        d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, radius, fill=(18, 6, 30, 225), outline=(235, 190, 255, 255), width=5)
    return d


def _center(d, y, text, font, fill=WHITE, shadow=True):
    w = d.textlength(text, font=font)
    x = (CW - w) / 2
    if shadow:
        d.text((x + 4, y + 5), text, font=font, fill=(0, 0, 0, 170))
    d.text((x, y), text, font=font, fill=fill)


def _fit(d, text, size, max_w, body=False):
    while size > 30:
        f = _f(size, body)
        if d.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return _f(size, body)


def _wrap(d, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if d.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + ([cur] if cur else [])


# ---------------- number parsing for count-up ------------------------------------
def _split_number(value: str):
    """'$7.6 billion' -> ('$', 7.6, ' BILLION', 1 decimal). Returns None if no number."""
    m = re.search(r"(\d[\d,]*\.?\d*)", value)
    if not m:
        return None
    num = m.group(1)
    dec = len(num.split(".")[1]) if "." in num else 0
    try:
        v = float(num.replace(",", ""))
    except ValueError:
        return None
    return value[:m.start()], v, value[m.end():], dec, "," in num


def _fmt(v, dec, commas):
    s = f"{v:,.{dec}f}" if commas else f"{v:.{dec}f}"
    return s


# ---------------- cards ----------------------------------------------------------
def card_stat(t, value: str, caption: str):
    img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    k = _ease(t / 0.35)
    if k <= 0.01:
        return img
    d = _panel(img, (40, 300, CW - 40, 820))
    parts = _split_number(value)
    if parts and parts[1] >= 2:
        pre, v, post, dec, commas = parts
        shown = v * _ease_out(t / 0.9)
        text = f"{pre}{_fmt(shown, dec, commas)}{post}".upper()
    else:
        text = value.upper()
    f = _fit(d, value.upper() + "0", 190, CW - 160)
    _center(d, 360, text, f, fill=GOLD)
    cf = _fit(d, caption.upper(), 74, CW - 160)
    lines = _wrap(d, caption.upper(), cf, CW - 160)[:2]
    y = 640 if len(lines) == 1 else 600
    for l in lines:
        _center(d, y, l, cf)
        y += int(cf.size * 1.1)
    return _scale(img, k)


def card_compare(t, a_label, a_value, b_label, b_value, unit=""):
    img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    k = _ease(t / 0.3)
    if k <= 0.01:
        return img
    d = _panel(img, (40, 200, CW - 40, 960))
    try:
        av, bv = float(re.sub(r"[^\d.]", "", str(a_value)) or 0), float(re.sub(r"[^\d.]", "", str(b_value)) or 0)
    except ValueError:
        av, bv = 1, 1
    mx = max(av, bv, 1e-9)
    grow = _ease_out((t - 0.25) / 0.9)
    for i, (lab, val, raw, col) in enumerate([(a_label, av, a_value, (120, 120, 150)), (b_label, bv, b_value, PINK)]):
        y = 260 + i * 340
        lf = _fit(d, lab.upper(), 70, CW - 160)
        d.text((90, y), lab.upper(), font=lf, fill=WHITE)
        bw = int((CW - 180) * (val / mx) * grow)
        d.rounded_rectangle((90, y + 100, 90 + max(bw, 20), y + 200), 22, fill=col)
        vf = _f(64)
        txt = f"{raw}{(' ' + unit) if unit else ''}".upper()
        tw = d.textlength(txt, font=vf)
        tx = min(90 + max(bw, 20) + 20, CW - 90 - tw)
        ty = y + 112
        if 90 + max(bw, 20) + 20 + tw > CW - 90:   # put the value inside the bar
            tx = 90 + max(bw, 20) - tw - 24
        d.text((tx, ty), txt, font=vf, fill=WHITE)
    return _scale(img, k)


def card_list(t, title, items):
    img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    k = _ease(t / 0.3)
    if k <= 0.01:
        return img
    items = [i for i in items if i][:4]
    h = 230 + 150 * len(items)
    top = 550 - h // 2
    d = _panel(img, (40, top, CW - 40, top + h))
    tf = _fit(d, title.upper(), 80, CW - 160)
    _center(d, top + 50, title.upper(), tf, fill=GOLD)
    for i, it in enumerate(items):
        appear = _ease_out((t - 0.35 - i * 0.45) / 0.3)
        if appear <= 0:
            continue
        y = top + 190 + i * 150
        x = 90 - int((1 - appear) * 60)
        d.ellipse((x, y + 8, x + 72, y + 80), fill=PURPLE2, outline=WHITE, width=4)
        d.line((x + 18, y + 46, x + 32, y + 62, x + 56, y + 28), fill=WHITE, width=9, joint="curve")
        f = _fit(d, it, 60, CW - 260, body=True)
        d.text((x + 100, y + 14), it, font=f, fill=(255, 255, 255, int(255 * appear)))
    return _scale(img, k)


def card_quote(t, text, by):
    img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    k = _ease(t / 0.3)
    if k <= 0.01:
        return img
    tmp = ImageDraw.Draw(img)
    f = _f(52, body=True)
    lines = _wrap(tmp, f"“{text}”", f, CW - 200)[:6]
    h = 200 + len(lines) * 70 + 90
    top = 550 - h // 2
    d = _panel(img, (40, top, CW - 40, top + h))
    d.text((80, top - 40), "“", font=_f(220), fill=PINK)
    y = top + 110
    for l in lines:
        d.text((100, y), l, font=f, fill=WHITE)
        y += 70
    bf = _fit(d, f"— {by}".upper(), 56, CW - 200)
    d.text((100, y + 20), f"— {by}".upper(), font=bf, fill=GOLD)
    return _scale(img, k)


def _scale(img, k):
    if abs(k - 1) < 0.01:
        return img
    w, h = max(1, int(CW * k)), max(1, int(CH * k))
    small = img.resize((w, h), Image.LANCZOS)
    out = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    out.alpha_composite(small, ((CW - w) // 2, (CH - h) // 2))
    return out


CARDS = {"stat": card_stat, "compare": card_compare, "list": card_list, "quote": card_quote}


def render_frames(kind: str, dur: float, out_dir: Path, **kw) -> Path:
    """Write PNG frames for the card; animation settles after ~1.5 s, then the last frame is reused."""
    out_dir.mkdir(parents=True, exist_ok=True)
    n = max(1, round(dur * FPS))
    fn = CARDS[kind]
    import inspect
    allowed = set(inspect.signature(fn).parameters) - {"t"}
    kw = {k: ("" if v is None else v) for k, v in kw.items() if k in allowed}
    if kind == "list":
        kw["items"] = [str(i) for i in (kw.get("items") or [])]
    last = None
    anim_frames = min(n, int(2.2 * FPS))
    for i in range(n):
        p = out_dir / f"{i:04d}.png"
        if i < anim_frames:
            last = fn(i / FPS, **kw)
            last.save(p, compress_level=1)
        else:
            (out_dir / f"{anim_frames - 1:04d}.png").link_to(p) if hasattr(Path, "link_to") else p.write_bytes((out_dir / f"{anim_frames - 1:04d}.png").read_bytes())
    return out_dir
