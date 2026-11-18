"""Map-explainer Shorts ("Vice City Center" style).

Everything happens on one stylised Leonida map: the camera flies between
places, pins pop in, a pink route draws itself, official screenshots pop up
on cards with pill labels, a progress tracker fills up, and 1–3 word captions
pop at the bottom with one coloured keyword.

    python -m autopilot.mapvideo scripts/leonida_tour.json [--fake-voice] [--out out.mp4]
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import leonida_map as LM
from .common import log

ROOT = Path(__file__).resolve().parent.parent
STILLS = ROOT / "library" / "stills"
ICONS = ROOT / "assets" / "icons"
FW, FH, FPS = 1080, 1920, 30
FOCUS_Y = 860
PINK = (255, 54, 136)
COLORS = [(255, 64, 160), (255, 214, 0), (0, 214, 255), (90, 140, 255), (255, 140, 0), (60, 230, 120)]
ICON_FOR = {"Lake Leonida": "boat", "Vice City": "palm", "Leonida Keys": "island", "Grassrivers": "boat", "Port Gellhorn": "ghost",
            "Ambrosia": "fire", "Mount Kalaga National Park": "target"}


def font(size, black=True):
    return ImageFont.truetype(str(LM.FONT_B if black else LM.FONT_XB), size)


def ease(x):                          # ease in-out cubic
    x = min(1.0, max(0.0, x))
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def back(x):                          # overshoot pop
    x = min(1.0, max(0.0, x))
    c1, c3 = 1.9, 2.9
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


# ---------------- drawing helpers -------------------------------------------------------------------
def pill(text, size=34, fg=None, bg=None, outline=None, pad=(26, 12)):
    bg = bg or PINK
    if fg is None:   # dark text on bright accents (yellow, cyan, green)
        fg = (15, 15, 25) if 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2] > 165 else (255, 255, 255)
    f = font(size)
    l, t, r, b = f.getbbox(text)
    w, h = r - l + pad[0] * 2, size + pad[1] * 2
    im = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([4, 4, w + 4, h + 4], radius=h // 2, fill=bg + (255,) if len(bg) == 3 else bg,
                        outline=outline, width=4 if outline else 0)
    d.text((w / 2 + 4, h / 2 + 4), text, font=f, fill=fg, anchor="mm")
    return im


def paste_center(canvas, im, cx, cy, scale=1.0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    if abs(scale - 1) > 0.01:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if alpha < 0.99:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy()
        im.putalpha(a)
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def caption_box(words, color, size=78):
    f = font(size)
    key = max(range(len(words)), key=lambda i: len(words[i].strip(",.!?")))
    gap = 18
    ws = [f.getlength(w) + 36 for w in words]
    W_ = int(sum(ws) + gap * (len(words) - 1) + 40)
    H_ = size + 70
    im = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 20
    for i, (w, ww) in enumerate(zip(words, ws)):
        bg = color + (255,) if i == key else (12, 12, 20, 235)
        d.rounded_rectangle([x, 12, x + ww, H_ - 12], 16, fill=bg)
        fg = (15, 15, 25) if i == key and sum(color) > 450 else (255, 255, 255)
        d.text((x + ww / 2, H_ / 2), w, font=f, fill=fg, anchor="mm")
        x += ww + gap
    return im


def make_card(img_path: Path, w=900):
    h = int(w * 9 / 16)
    src = Image.open(img_path).convert("RGB")
    sr = src.width / src.height
    if sr > 16 / 9:
        nw = int(src.height * 16 / 9)
        src = src.crop(((src.width - nw) // 2, 0, (src.width + nw) // 2, src.height))
    else:
        nh = int(src.width * 9 / 16)
        src = src.crop((0, (src.height - nh) // 2, src.width, (src.height + nh) // 2))
    src = src.resize((w, h), Image.LANCZOS)
    pad = 40
    im = Image.new("RGBA", (w + 16 + pad * 2, h + 16 + pad * 2), (0, 0, 0, 0))
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle([pad + 6, pad + 14, pad + w + 22, pad + h + 26], 30, fill=170)
    im.paste((0, 0, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([pad, pad, pad + w + 16, pad + h + 16], 30, fill=(245, 245, 250, 255))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w, h], 24, fill=255)
    im.paste(src, (pad + 8, pad + 8), m)
    return im


def make_pin(icon: str, r=46):
    im = Image.new("RGBA", (r * 2 + 20, int(r * 3.1)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = r + 10, r + 6
    d.polygon([(cx - r * .62, cy + r * .6), (cx + r * .62, cy + r * .6), (cx, cy + r * 1.75)], fill=PINK + (255,))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PINK + (255,), outline=(255, 255, 255, 255), width=5)
    d.ellipse([cx - r * .72, cy - r * .72, cx + r * .72, cy + r * .72], fill=(255, 255, 255, 255))
    p = ICONS / f"{icon}.png"
    if p.exists():
        ic = Image.open(p).convert("RGBA").resize((int(r * 1.15), int(r * 1.15)), Image.LANCZOS)
        im.alpha_composite(ic, (int(cx - ic.width / 2), int(cy - ic.height / 2)))
    return im, (cx, cy + r * 1.75)        # anchor = pin tip


def photo_bg(path: Path, dim=.35):
    """Full-screen 9:16 crop of an official screenshot, a bit darker at top and bottom."""
    src = Image.open(path).convert("RGB")
    w = int(src.height * FW / FH)
    if w < src.width:
        src = src.crop(((src.width - w) // 2, 0, (src.width + w) // 2, src.height))
    src = src.resize((int(FW * 1.15), int(FH * 1.15)), Image.LANCZOS)
    a = np.asarray(src, np.float32)
    yy = np.linspace(0, 1, a.shape[0])[:, None, None]
    shade = 1 - dim * (np.clip((yy - .45) * 2.2, 0, 1) + np.clip((.25 - yy) * 3, 0, 1))
    return Image.fromarray(np.clip(a * shade, 0, 255).astype(np.uint8))


def brand_badge(path: Path, size=360):
    """The official GTA VI logo area of the cover art as a rounded badge."""
    src = Image.open(path).convert("RGB")
    w, h = src.size
    crop = src.crop((int(w * .17), int(h * .27), int(w * .77), int(h * .71))).resize((size, int(size * .733)), Image.LANCZOS)
    m = Image.new("L", crop.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, crop.width - 1, crop.height - 1], 28, fill=255)
    out = Image.new("RGBA", (crop.width + 40, crop.height + 40), (0, 0, 0, 0))
    sh = Image.new("L", out.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle([20, 26, crop.width + 20, crop.height + 26], 28, fill=180)
    out.paste((0, 0, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(12)))
    out.paste(crop, (20, 20), m)
    ImageDraw.Draw(out).rounded_rectangle([18, 18, crop.width + 22, crop.height + 22], 30, outline=(255, 255, 255, 255), width=5)
    return out


def vignette():
    yy, xx = np.mgrid[0:FH, 0:FW].astype(np.float32)
    r = np.sqrt(((xx - FW / 2) / FW) ** 2 + ((yy - FH / 2) / FH) ** 2)
    a = np.clip((r - .32) * 2.0, 0, 1) * 150
    v = np.zeros((FH, FW, 4), np.uint8)
    v[..., 3] = a.astype(np.uint8)
    return Image.fromarray(v, "RGBA")


def caption_img(words, color, size=80, box=False):
    if box:
        return caption_box(words, color, size)
    f = font(size)
    text = " ".join(words)
    l, t, r, b = f.getbbox(text)
    w, h = r - l + 60, size + 60
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = 30
    key = max(range(len(words)), key=lambda i: len(words[i].strip(",.!?")) + (2 if i == len(words) - 1 else 0))
    for i, wd in enumerate(words):
        ImageDraw.Draw(sh).text((x + 4, 34), wd, font=f, fill=(0, 0, 0, 230))
        ImageDraw.Draw(im).text((x, 30), wd, font=f, fill=color if i == key else (255, 255, 255),
                                stroke_width=5, stroke_fill=(10, 10, 20))
        x += f.getlength(wd + " ")
    sh = sh.filter(ImageFilter.GaussianBlur(8))
    sh.alpha_composite(im)
    return sh


def big_text(text):
    f = font(150)
    while f.getlength(text) > 980 and f.size > 70:
        f = font(f.size - 8)
    w, h = int(f.getlength(text)) + 80, f.size + 80
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((w / 2 + 6, h / 2 + 8), text, font=f, fill=(0, 0, 0, 220), anchor="mm")
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    ImageDraw.Draw(im).text((w / 2, h / 2), text, font=f, fill=PINK, anchor="mm", stroke_width=8,
                            stroke_fill=(255, 255, 255))
    sh.alpha_composite(im)
    return sh


def _homography(src, dst):
    """3x3 matrix mapping src points to dst points (4 pairs)."""
    A, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    h = np.linalg.solve(np.array(A, float), np.array(b, float))
    return np.append(h, 1).reshape(3, 3)


# flat screen -> tilted "3D" screen (top of the map leans away from the viewer)
_FLAT = [(0, 0), (FW, 0), (FW, FH), (0, FH)]
_TILT = [(FW * .2, FH * .2), (FW * .8, FH * .2), (FW * 1.08, FH * 1.0), (-FW * .08, FH * 1.0)]
H_FWD = _homography(_FLAT, _TILT)
H_INV = _homography(_TILT, _FLAT)


def tilt_point(x, y):
    v = H_FWD @ np.array([x, y, 1.0])
    return v[0] / v[2], v[1] / v[2]


def sky(theme):
    top = np.array(theme["deep"], np.float32) * .55
    bot = np.array(theme["mid"], np.float32)
    k = np.clip(np.linspace(0, 1, FH)[:, None, None] * 2.4, 0, 1)
    g = top * (1 - k) + bot * k
    return Image.fromarray(np.repeat(g, FW, axis=1).astype(np.uint8)).convert("RGBA")


STYLE_CHOICES = {
    "layout": ["flat", "tilt", "photo"],
    "card_in": ["pop", "slide", "drop", "flip"],
    "caps": ["pop", "box", "single"],
    "flash": [True, False],
}


def chunks(words, size=3):
    out, cur = [], []
    for w in words:
        cur.append(w)
        txt = w["w"]
        if len(cur) >= size or txt.endswith((",", ".", "?", "!")) or sum(len(x["w"]) for x in cur) > 12:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


# ---------------- scene ---------------------------------------------------------------------------
class Scene:
    def __init__(self, spec, lines, words, total):
        self.spec, self.lines, self.words, self.total = spec, lines, words, total
        global PINK
        LM.set_theme(spec.get("theme", "day"))
        PINK = tuple(LM.THEME["accent"])
        for k, v in (spec.get("places") or {}).items():
            LM.PLACES[k] = tuple(v)
        ICON_FOR.update(spec.get("icons") or {})
        self.map = LM.base_map()
        self.small = self.map.resize((self.map.width // 3, self.map.height // 3), Image.BILINEAR)
        self.vig = vignette()
        self.pins = {p: make_pin(ICON_FOR.get(p, "pin")) for p in spec.get("tour", [])}
        self.cards = {}
        for l in lines:
            c = l.get("card")
            if c and c["img"] not in self.cards:
                self.cards[c["img"]] = make_card(STILLS / c["img"])
        st = dict(spec.get("style") or {})
        for k, opts in STYLE_CHOICES.items():
            st.setdefault(k, opts[0])
        self.style = st
        self.sky = sky(LM.THEME) if st["layout"] == "tilt" else None
        self.photos = {}
        if st["layout"] == "photo":
            for l in lines:
                c = l.get("card")
                f = c["img"] if c else None
                if f and f not in self.photos:
                    self.photos[f] = photo_bg(STILLS / f)
            self.photos["_brand"] = photo_bg(STILLS / "art_Official_Cover_Art_portrait.jpg", dim=.55)
        self.brand = None
        bp = STILLS / "art_Official_Cover_Art_square.jpg"
        if bp.exists():
            self.brand = brand_badge(bp)
        self.pills = {}
        self.caps = []
        for i, ch in enumerate(chunks(words, 1 if st["caps"] == "single" else 3)):
            self.caps.append((ch[0]["start"], [w["w"].upper() for w in ch], COLORS[i % len(COLORS)]))
        self.cap_imgs = []
        for _, ws, c in self.caps:
            im = caption_img(ws, c, size=110 if st["caps"] == "single" else 80, box=st["caps"] == "box")
            if im.width > 1010:                      # never run off the screen
                k = 1010 / im.width
                im = im.resize((1010, int(im.height * k)), Image.LANCZOS)
            self.cap_imgs.append(im)
        # map-space spots
        self.spot = {k: LM.to_px(*v) for k, v in LM.PLACES.items()}
        land_y0, land_y1 = LM.to_px(0, 30.5)[1], LM.to_px(0, 24.45)[1]
        self.full = ((LM.to_px(-81.6, 0)[0]), (land_y0 + land_y1) / 2 - 120, 1450 / (land_y1 - land_y0))
        # per line camera target and visit order
        self.targets, visited, prev = [], [], None
        for l in lines:
            cam = l.get("cam", "full")
            if cam == "full":
                t = self.full
            else:
                x, y = self.spot[cam]
                t = (x, y, l.get("zoom", 0.95))
                if cam not in visited:
                    visited.append(cam)
            self.targets.append(t)
            l["_visited"] = list(visited)
            l["_from"] = prev if l.get("route") else None
            if cam != "full":
                prev = cam

    def _pill(self, key, **kw):
        k = (key, tuple(sorted((a, str(b)) for a, b in kw.items())))
        if k not in self.pills:
            self.pills[k] = pill(key[0], **kw)
        return self.pills[k]

    @staticmethod
    def card_delay(l):
        if not l.get("card"):
            return 0
        d = l["end"] - l["start"]
        return min(max(1.1 if l.get("route") else 0.8, d * 0.42), d - 1.0)

    def line_at(self, t):
        i = 0
        for k, l in enumerate(self.lines):
            if l["start"] <= t:
                i = k
        return i

    def camera(self, t):
        i = self.line_at(t)
        l = self.lines[i]
        tgt = self.targets[i]
        src = self.targets[i - 1] if i > 0 else (tgt[0], tgt[1], tgt[2] * 0.85)
        dur = min(0.75, max(0.3, (l["end"] - l["start"]) * 0.4))
        k = ease((t - l["start"]) / dur)
        # zoom out a bit mid-flight for long hops (feels like a camera move, not a slide)
        dist = math.hypot(tgt[0] - src[0], tgt[1] - src[1])
        dip = 1 - min(0.35, dist / 6000) * math.sin(math.pi * k)
        x = src[0] + (tgt[0] - src[0]) * k
        y = src[1] + (tgt[1] - src[1]) * k
        z = (src[2] + (tgt[2] - src[2]) * k) * dip
        z *= 1 + 0.035 * max(0, t - l["start"] - dur)        # slow push-in while talking
        speed = 0 if k >= 1 else dist / dur * (math.pi / 2) * math.sin(math.pi * k)
        return x, y, z, speed

    def view(self, x, y, z):
        cw, ch = FW / z, FH / z
        x0, y0 = x - cw / 2, y - FOCUS_Y / z
        src, f = (self.small, 3) if z < 0.6 else (self.map, 1)
        box = (x0 / f, y0 / f, (x0 + cw) / f, (y0 + ch) / f)
        return src.transform((FW, FH), Image.EXTENT, box, Image.BILINEAR, fillcolor=tuple(LM.THEME["deep"]))

    def to_screen(self, mx, my, cam):
        x, y, z, _ = cam
        return (mx - x) * z + FW / 2, (my - y) * z + FOCUS_Y

    def route_pts(self, a, b, n=60):
        (x0, y0), (x1, y1) = self.spot[a], self.spot[b]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        nx, ny = -(y1 - y0), (x1 - x0)
        cx, cy = mx + nx * .18, my + ny * .18
        return [((1 - s) ** 2 * x0 + 2 * (1 - s) * s * cx + s * s * x1,
                 (1 - s) ** 2 * y0 + 2 * (1 - s) * s * cy + s * s * y1) for s in np.linspace(0, 1, n)]

    def frame(self, t):
        i = self.line_at(t)
        l = self.lines[i]
        lt = t - l["start"]
        ldur = l["end"] - l["start"]
        cam = self.camera(t)
        if self.style["layout"] == "photo":
            return self.photo_frame(t, i, l, lt, ldur)
        base = self.view(cam[0], cam[1], cam[2]).convert("RGBA")

        # routes (all finished ones faint, current one drawing)
        lay = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for k in range(i + 1):
            lk = self.lines[k]
            if not lk.get("_from"):
                continue
            pts = self.route_pts(lk["_from"], lk["cam"])
            p = 1.0 if k < i else ease(lt / 0.9)
            pts = pts[:max(2, int(len(pts) * p))]
            sp = [self.to_screen(px, py, cam) for px, py in pts]
            d.line(sp, fill=(255, 255, 255, 255), width=16, joint="curve")
            d.line(sp, fill=PINK + (255,), width=9, joint="curve")
            if k == i and p < 1:
                hx, hy = sp[-1]
                d.ellipse([hx - 14, hy - 14, hx + 14, hy + 14], fill=(255, 255, 255, 255))
        glow = lay.filter(ImageFilter.GaussianBlur(10))
        base.alpha_composite(glow)
        base.alpha_composite(lay)

        # pins
        for name in l["_visited"]:
            pin, (ax, ay) = self.pins[name]
            sx, sy = self.to_screen(*self.spot[name], cam)
            first = name == l.get("cam") and name not in self.lines[i - 1]["_visited"] if i > 0 else False
            appear = (lt - (0.75 if l.get("route") else 0.3)) / 0.35 if first else 1
            sc = back(appear) * (0.8 if cam[2] < 0.6 else 1.0)
            if sc > 0.02:
                pin_s = pin.resize((max(1, int(pin.width * sc)), max(1, int(pin.height * sc))), Image.BICUBIC)
                base.alpha_composite(pin_s, (int(sx - ax * sc), int(sy - ay * sc)))
        if self.style["layout"] == "tilt":
            warped = base.transform((FW, FH), Image.PERSPECTIVE, list((H_INV / H_INV[2, 2]).flatten()[:8]),
                                    Image.BILINEAR, fillcolor=(0, 0, 0, 0))
            base = self.sky.copy()
            base.alpha_composite(warped)
        # blur + darken when a card is on screen, and motion blur during fast moves
        card = l.get("card")
        cd = self.card_delay(l)
        ct = lt - cd                                  # time since the card popped
        if card and ct < 0:
            card = None
        blur = min(8, cam[3] / 900)
        if card:
            k = min(1, ct / 0.3)
            blur = max(blur, 10 * k)
        if blur > 0.5:
            b = base.resize((FW // 4, FH // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(blur / 3))
            base = b.resize((FW, FH), Image.BILINEAR)
            if card:
                base = Image.blend(base, Image.new("RGBA", (FW, FH), (10, 20, 45, 255)), 0.25 * min(1, ct / 0.3))
        base.alpha_composite(self.vig)

        # huge punchy text on the map
        if l.get("big") and not card:
            sc = back((lt - 0.15) / 0.3)
            if l["big"] not in self.pills:
                self.pills[l["big"]] = big_text(l["big"])
            paste_center(base, self.pills[l["big"]], FW / 2, 560, 0.6 + 0.4 * sc, min(1, max(0, sc)))
        # GTA VI branding: official logo badge on the hook line and on the end card
        if self.brand is not None and (i == 0 or l.get("poll")):
            bt = lt if i == 0 else lt - 0.1
            yb = 520 if i == 0 else 760
            paste_center(base, self.brand, FW / 2, yb, 0.6 + 0.4 * back(bt / 0.35), min(1, max(0, bt / 0.15)))
        # date pill / title pill
        if l.get("pill"):
            sc = back(lt / 0.3)
            paste_center(base, self._pill((l["pill"],), size=40, bg=(230, 40, 60)), FW / 2, 250, sc)
        # card
        if card:
            pop = back(ct / 0.3)
            out = 1 - ease((lt - (ldur - 0.12)) / 0.12) if i + 1 < len(self.lines) and not self.lines[i + 1].get("card") else 1
            cy = 760
            cx, scl, cim = FW / 2, 0.85 + 0.15 * pop, self.cards[card["img"]]
            mode = self.style["card_in"]
            if mode == "slide":
                cx, scl = FW / 2 + (1 - ease(ct / 0.35)) * FW, 1
            elif mode == "drop":
                cy, scl = 760 - (1 - pop) * 500, 1
            elif mode == "flip":
                k = ease(ct / 0.3)
                if k < 0.98:
                    cim = cim.resize((max(2, int(cim.width * k)), cim.height))
                scl = 1
            paste_center(base, cim, cx, cy, scl, min(1, max(0.05, ease(ct / 0.2))) * out)
            if card.get("top"):
                paste_center(base, self._pill((card["top"],), size=26, bg=(20, 22, 30), outline=(255, 255, 255)),
                             FW / 2, cy - 300, back((ct - 0.12) / 0.25), out)
            if card.get("bottom"):
                paste_center(base, self._pill((card["bottom"],), size=40, bg=PINK), FW / 2, cy + 300,
                             back((ct - 0.2) / 0.25), out)
        if not card and l.get("cam") and l["cam"] != "full":
            sx, sy = self.to_screen(*self.spot[l["cam"]], cam)
            if self.style["layout"] == "tilt":
                sx, sy = tilt_point(sx, sy)
            paste_center(base, self._pill((l["cam"].upper(),), size=34), sx, sy + 50, back((lt - 0.6) / 0.25))

        # progress tracker
        tr = l.get("tracker")
        if tr is not None and not l.get("poll"):
            self._tracker(base, tr, lt, i)
        # poll card
        if l.get("poll"):
            self._poll(base, l["poll"], lt)

        # captions
        ci = -1
        for k, (st, _, _) in enumerate(self.caps):
            if st <= t + 0.03:
                ci = k
        if ci >= 0:
            pt = t - self.caps[ci][0]
            paste_center(base, self.cap_imgs[ci], FW / 2, 1290, 0.82 + 0.18 * back(pt / 0.12))
        self._flash(base, lt, i)
        # footer
        d = ImageDraw.Draw(base)
        d.text((FW / 2, 1880), "GTA 6 map is fan-made  |  locations are estimates  |  screenshots: Rockstar Games",
               font=font(19, False), fill=(255, 255, 255, 120), anchor="mm")
        return base.convert("RGB")

    def _flash(self, base, lt, i):
        if self.style.get("flash") and i > 0 and lt < 0.14:
            a = int(200 * (1 - lt / 0.14))
            base.alpha_composite(Image.new("RGBA", (FW, FH), (255, 255, 255, a)))

    def photo_frame(self, t, i, l, lt, ldur):
        """Photo layout: full-screen official screenshot behind everything, slow zoom, no map."""
        key = None
        for k in range(i, -1, -1):
            c = self.lines[k].get("card")
            if c:
                key = c["img"]
                break
        bg = self.photos.get(key) if key else self.photos["_brand"]
        z = 1 + 0.06 * min(1, lt / max(1, ldur))
        w, h = int(FW * z), int(FH * z)
        sx = (bg.width - w) // 2 + int((i % 2 * 2 - 1) * 20 * lt)
        sy = (bg.height - h) // 2
        base = bg.crop((max(0, sx), max(0, sy), max(0, sx) + w, max(0, sy) + h)).resize((FW, FH), Image.BILINEAR).convert("RGBA")
        if lt < 0.25 and i > 0:        # zoom-punch into each new line
            k = 1 - lt / 0.25
            pz = 1 + 0.08 * k
            base = base.resize((int(FW * pz), int(FH * pz)), Image.BILINEAR).crop(
                (int(FW * (pz - 1) / 2), int(FH * (pz - 1) / 2), int(FW * (pz - 1) / 2) + FW, int(FH * (pz - 1) / 2) + FH))
        base.alpha_composite(self.vig)
        if self.brand is not None and (i == 0 or l.get("poll")):
            bt = lt if i == 0 else lt - 0.1
            paste_center(base, self.brand, FW / 2, 470 if i == 0 else 760, 0.6 + 0.4 * back(bt / 0.35), min(1, max(0, bt / 0.15)))
        if l.get("pill"):
            paste_center(base, self._pill((l["pill"],), size=40, bg=(230, 40, 60)), FW / 2, 250, back(lt / 0.3))
        if l.get("big"):
            if l["big"] not in self.pills:
                self.pills[l["big"]] = big_text(l["big"])
            sc = back((lt - 0.15) / 0.3)
            paste_center(base, self.pills[l["big"]], FW / 2, 640, 0.6 + 0.4 * sc, min(1, max(0, sc)))
        c = l.get("card")
        if c:
            paste_center(base, self._pill((c["bottom"],), size=46), FW / 2, 1060, back((lt - 0.2) / 0.3))
            paste_center(base, self._pill((c.get("top") or "OFFICIAL SCREENSHOT",), size=24, bg=(20, 22, 30), outline=(255, 255, 255)),
                         FW / 2, 980, back((lt - 0.1) / 0.3))
        tr = l.get("tracker")
        if tr is not None and not l.get("poll"):
            self._tracker(base, tr, lt, i)
        if l.get("poll"):
            self._poll(base, l["poll"], lt)
        ci = -1
        for k, (st, _, _) in enumerate(self.caps):
            if st <= t + 0.03:
                ci = k
        if ci >= 0:
            paste_center(base, self.cap_imgs[ci], FW / 2, 1290, 0.82 + 0.18 * back((t - self.caps[ci][0]) / 0.12))
        self._flash(base, lt, i)
        d = ImageDraw.Draw(base)
        d.text((FW / 2, 1880), "screenshots: Rockstar Games  |  GTA VI is a trademark of Rockstar Games",
               font=font(19, False), fill=(255, 255, 255, 140), anchor="mm")
        return base.convert("RGB")

    def _tracker(self, base, idx, lt, i):
        tour = self.spec.get("tour", [])
        n = len(tour)
        prev = self.lines[i - 1].get("tracker") if i > 0 else None
        appear = 1 if prev is not None else back(lt / 0.3)
        w, h = 760, 176
        panel = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(panel)
        d.rounded_rectangle([0, 0, w - 1, h - 1], 26, fill=(14, 16, 26, 235), outline=(255, 255, 255, 40), width=2)
        d.text((w / 2, 26), self.spec.get("tracker_title", "LEONIDA TOUR"), font=font(24), fill=(255, 255, 255, 230), anchor="mm")
        x0, x1, y = 60, w - 60, 136
        d.line([(x0, y), (x1, y)], fill=(255, 255, 255, 70), width=6)
        fill_to = idx if prev is None or prev == idx else prev + (idx - prev) * ease(lt / 0.5)
        fx = x0 + (x1 - x0) * max(0, fill_to - 1) / max(1, n - 1) if fill_to >= 1 else x0
        if fill_to >= 1:
            d.line([(x0, y), (fx, y)], fill=PINK + (255,), width=8)
        for k in range(n):
            x = x0 + (x1 - x0) * k / max(1, n - 1)
            done = k + 1 <= fill_to + 1e-6
            r = 13 if done else 10
            d.ellipse([x - r, y - r, x + r, y + r], fill=PINK + (255,) if done else (40, 44, 60, 255),
                      outline=(255, 255, 255, 200), width=3)
        if idx >= 1:
            x = x0 + (x1 - x0) * (idx - 1) / max(1, n - 1)
            name = (self.spec.get("tracker_names") or {}).get(tour[idx - 1], tour[idx - 1]).replace(" National Park", "").upper()
            p = self._pill((name,), size=22, pad=(16, 7))
            px = min(max(x, p.width / 2 + 6), w - p.width / 2 - 6)
            panel.alpha_composite(p, (int(px - p.width / 2), int(y - 30 - p.height)))
        paste_center(base, panel, FW / 2, 1560, 0.8 + 0.2 * appear, min(1, appear))

    def _poll(self, base, q, lt):
        w, h = 820, 250
        card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        d.rounded_rectangle([0, 0, w - 1, h - 1], 30, fill=(14, 16, 26, 240), outline=PINK + (255,), width=5)
        fs = 40
        while font(fs).getlength(q) > w - 60 and fs > 22:
            fs -= 2
        d.text((w / 2, 70), q, font=font(fs), fill=(255, 255, 255), anchor="mm")
        d.rounded_rectangle([w / 2 - 190, 140, w / 2 + 190, 210], 35, fill=(40, 170, 90, 255))
        d.text((w / 2, 175), "COMMENT BELOW", font=font(32), fill=(255, 255, 255), anchor="mm")
        paste_center(base, card, FW / 2, 1560, 0.7 + 0.3 * back(lt / 0.35), min(1, lt / 0.2))


# ---------------- build -------------------------------------------------------------------------------
def fake_words(lines):
    words, t = [], 0.25
    for l in lines:
        for w in l["text"].split():
            d = 0.12 + 0.045 * len(w)
            words.append({"w": w, "start": t, "end": t + d})
            t += d + (0.18 if w.endswith((",", ".", "?")) else 0.03)
    return words, t + 0.4


def assign_lines(lines, words, total):
    i = 0
    for l in lines:
        n = len(l["text"].split())
        l["start"] = words[i]["start"]
        l["end"] = words[min(len(words) - 1, i + n - 1)]["end"]
        i += n
    for a, b in zip(lines, lines[1:]):
        a["end"] = b["start"]
    lines[0]["start"], lines[-1]["end"] = 0.0, total


def sfx_events(scene):
    ev = []
    for i, l in enumerate(scene.lines):
        s = l["start"]
        if i == 0:
            ev.append((0.0, "boom", 0.55))
        elif scene.targets[i] != scene.targets[i - 1]:
            ev.append((max(0, s - 0.05), "whoosh", 0.45))
        if l.get("route"):
            ev.append((s + 0.75, "pop", 0.5))
        elif l.get("cam") not in (None, "full"):
            ev.append((s + 0.3, "pop", 0.5))
        if l.get("card"):
            ev.append((s + Scene.card_delay(l), "swish", 0.4))
        if l.get("tracker") is not None and (i == 0 or scene.lines[i - 1].get("tracker") != l.get("tracker")):
            ev.append((s + 0.2, "ding", 0.25))
        if l.get("pill") or l.get("poll"):
            ev.append((s + 0.05, "ping", 0.4))
        if l.get("big"):
            ev.append((s + 0.15, "boom", 0.4))
    return ev


def build(spec_path: Path, out: Path, fake_voice=False, preview_only=False):
    spec = json.loads(Path(spec_path).read_text())
    lines = spec["lines"]
    work = out.parent / (out.stem + "_work")
    work.mkdir(parents=True, exist_ok=True)
    voice_mp3 = work / "voice.mp3"
    if fake_voice:
        words, total = fake_words(lines)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                        "-t", f"{total:.2f}", str(voice_mp3)], check=True)
    else:
        from .voice import make_voice
        words, total = make_voice([dict(l) for l in lines], str(voice_mp3))
    assign_lines(lines, words, total)
    scene = Scene(spec, lines, words, total)
    if preview_only:
        return scene
    n = int(total * FPS)
    log.info("map video: %d lines, %.1fs, %d frames", len(lines), total, n)
    silent = work / "video.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{FW}x{FH}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                          "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    for f in range(n):
        p.stdin.write(scene.frame(f / FPS).tobytes())
        if f % 150 == 0:
            log.info("  frame %d/%d", f, n)
    p.stdin.close()
    p.wait()
    from .render import mix_audio
    import os
    if spec.get("music"):
        os.environ["MUSIC_STYLE"] = spec["music"]
    audio = mix_audio(str(voice_mp3), total, sfx_events(scene), work)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(audio), "-c:v", "copy",
                    "-c:a", "copy", "-shortest", str(out)], check=True)
    meta = {k: spec.get(k) for k in ("title", "yt_title", "description", "tags")}
    meta["caption"] = spec.get("title", "") + "\n\n" + spec.get("description", "")
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    # contact sheet for checking
    sheet = Image.new("RGB", (8 * 270, 3 * 480))
    for k in range(24):
        fr = scene.frame(total * (k + 0.5) / 24).resize((270, 480))
        sheet.paste(fr, ((k % 8) * 270, (k // 8) * 480))
    sheet.save(out.with_name(out.stem + "_sheet.jpg"), quality=85)
    log.info("map video ready: %s (%.1fs)", out, total)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    spec = Path(args[0])
    out = Path(args[args.index("--out") + 1]) if "--out" in args else ROOT / "output" / (spec.stem + ".mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    build(spec, out, fake_voice="--fake-voice" in args)
