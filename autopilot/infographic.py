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
    m = re.search(r"(\d[\d.,]*\d|\d)", value)
    if not m:
        return None
    num = m.group(1)
    if num.count(".") > 1 or (num.count(".") == 1 and len(num.split(".")[1]) == 3 and "," not in num):
        num = num.replace(".", ",")          # European thousands separators: 1.002.000
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
    is_year = parts and parts[3] == 0 and not parts[4] and 1900 <= parts[1] <= 2100 and not parts[0].strip()
    if parts and parts[1] >= 2 and not is_year:
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


def card_person(t, name, role, country=""):
    """Name card for a real person/organisation (no photo): initials badge + name + role (+ country)."""
    img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    k = _ease(t / 0.3)
    if k <= 0.01:
        return img
    d = _panel(img, (40, 300, CW - 40, 860))
    initials = "".join(w[0] for w in name.split()[:2]).upper() or "?"
    d.ellipse((CW // 2 - 110, 340, CW // 2 + 110, 560), fill=PURPLE2, outline=WHITE, width=6)
    f = _f(120)
    w = d.textlength(initials, font=f)
    d.text((CW / 2 - w / 2, 365), initials, font=f, fill=WHITE)
    nf = _fit(d, name.upper(), 96, CW - 140)
    _center(d, 590, name.upper(), nf, fill=GOLD)
    rf = _fit(d, role.upper(), 60, CW - 160)
    _center(d, 710, role.upper(), rf)
    if country:
        cf = _fit(d, country.upper(), 46, CW - 200)
        _center(d, 790, country.upper(), cf, fill=(235, 190, 255))
    return _scale(img, k)


def card_blocks(t, total, highlight, caption, icon="music", mode="remove"):
    """Grid of icon blocks; the highlighted ones drop out (remove) or light up (add).
    e.g. 50 songs, 17 removed -> 17 blocks fall away."""
    from .pill import ICON_DIR
    img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    k = _ease(t / 0.25)
    if k <= 0.01:
        return img
    try:
        total, highlight = int(float(str(total).replace(",", ""))), int(float(str(highlight).replace(",", "")))
    except ValueError:
        return img
    steps = [m * 10 ** e for e in range(0, 10) for m in (1, 2, 5)]
    per = next(x for x in steps if total / x <= 60)
    n, h = max(1, round(total / per)), max(1, round(highlight / per))
    h = min(h, n)
    cols = 8 if n > 40 else 6 if n > 18 else 5 if n > 8 else 4
    rows = math.ceil(n / cols)
    cell = min((CW - 140) // cols, 640 // max(rows, 1))
    gw, gh = cols * cell, rows * cell
    top = 260
    d = _panel(img, (40, 90, CW - 40, top + gh + 300))
    cf = _fit(d, caption.upper(), 74, CW - 160)
    _center(d, 130, caption.upper(), cf, fill=GOLD)
    try:
        ic = Image.open(ICON_DIR / f"{icon}.png").convert("RGBA")
    except Exception:
        ic = Image.open(ICON_DIR / "music.png").convert("RGBA")
    icon_img = ic.resize((int(cell * 0.62),) * 2, Image.LANCZOS)
    ic = Image.new("RGBA", (int(cell * 0.86),) * 2, (0, 0, 0, 0))
    ImageDraw.Draw(ic).rounded_rectangle((0, 0, ic.width - 1, ic.height - 1), int(cell * 0.18),
                                         fill=(236, 214, 255, 255), outline=(255, 255, 255, 255), width=3)
    off = (ic.width - icon_img.width) // 2
    ic.alpha_composite(icon_img, (off, off))
    x0 = (CW - gw) // 2
    hl_idx = set(range(n - h, n))     # last blocks are the affected ones
    for i in range(n):
        appear = _ease_out((t - 0.15 - i * 0.025) / 0.2)
        if appear <= 0:
            continue
        r, c = divmod(i, cols)
        x, y = x0 + c * cell + int(cell * 0.09), top + r * cell + int(cell * 0.09)
        tile = ic
        if i in hl_idx:
            fall = _ease_out((t - 1.2 - (i - (n - h)) * 0.03) / 0.5)
            if mode == "remove" and fall > 0:
                red = Image.new("RGBA", tile.size, (255, 40, 60, 0))
                red.putalpha(tile.split()[3].point(lambda a: int(a * 0.55)))
                tile = Image.alpha_composite(tile, red)
                y += int(fall * 520)
                tile = tile.copy()
                tile.putalpha(tile.split()[3].point(lambda a, f=fall: int(a * (1 - f))))
                if fall >= 0.99:
                    continue
            elif mode == "add" and fall > 0:
                g = Image.new("RGBA", (tile.width + 30, tile.height + 30), (0, 0, 0, 0))
                ImageDraw.Draw(g).ellipse((0, 0, g.width, g.height), fill=(255, 214, 64, int(150 * fall)))
                img.alpha_composite(g.filter(ImageFilter.GaussianBlur(10)), (x - 15, y - 15))
        if appear < 1:
            s_ = max(1, int(tile.width * appear))
            tile = tile.resize((s_, s_))
            x += (ic.width - s_) // 2; y += (ic.height - s_) // 2
        img.alpha_composite(tile, (x, max(0, min(CH - tile.height, y))))
    # counter
    shown = h if t > 1.2 else 0
    cnt = int(h * per * _ease_out((t - 1.2) / 0.6)) if t > 1.2 else 0
    cnt = int(round(highlight * _ease_out((t - 1.2) / 0.6))) if t > 1.2 else 0
    label = (f"-{cnt:,}" if mode == "remove" else f"+{cnt:,}") + (f"  (1 BLOCK = {per:,})" if per >= 5 else "")
    bf = _f(110)
    _center(d, top + gh + 60, label, bf, fill=(255, 80, 110) if mode == "remove" else (120, 255, 150))
    return _scale(img, k)


def _scale(img, k):
    if abs(k - 1) < 0.01:
        return img
    w, h = max(1, int(CW * k)), max(1, int(CH * k))
    small = img.resize((w, h), Image.LANCZOS)
    out = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    out.alpha_composite(small, ((CW - w) // 2, (CH - h) // 2))
    return out


CARDS = {"stat": card_stat, "compare": card_compare, "list": card_list, "quote": card_quote, "person": card_person, "blocks": card_blocks}


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
