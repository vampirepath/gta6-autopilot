"""Draws our own stylised map of Leonida (GTA 6's Florida-like state).

Fan-made: the coastline comes from public-domain US census shapes of the
Florida peninsula, drawn in a game-map style. Region positions are fan
estimates (Rockstar has not released an official map).
"""
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
GEO = ROOT / "assets" / "geo" / "leonida.json"
FONT_B = ROOT / "assets" / "fonts" / "Montserrat-Black.woff"
FONT_XB = ROOT / "assets" / "fonts" / "Montserrat-ExtraBold.woff"

# map canvas
S = 560.0                      # pixels per degree of latitude
LON0, LAT0 = -84.6, 31.35      # top-left corner
COSL = math.cos(math.radians(27.6))
W, H = 3300, 4300
CUT_LON = -83.25               # drop the panhandle so it reads as "Leonida", not Florida

# fan-estimated region spots (lon, lat)
PLACES = {
    "Vice City": (-80.22, 25.80),
    "Leonida Keys": (-81.05, 24.82),
    "Grassrivers": (-80.85, 25.95),
    "Port Gellhorn": (-81.90, 26.62),
    "Ambrosia": (-80.95, 26.72),
    "Mount Kalaga National Park": (-82.35, 30.25),
    "Lake Leonida": (-80.83, 26.95),
}
COUNTIES = [("LEONARD COUNTY", -80.45, 27.55), ("KELLY COUNTY", -81.75, 26.95),
            ("MARIANA COUNTY", -81.15, 25.55), ("AMBROSIA COUNTY", -81.25, 27.35),
            ("LUMMOX COUNTY", -82.35, 29.75), ("VICE-DALE COUNTY", -80.25, 26.2)]


def to_px(lon, lat):
    return ((lon - LON0) * COSL * S, (LAT0 - lat) * S)


def _font(size, black=True):
    return ImageFont.truetype(str(FONT_B if black else FONT_XB), size)


def _noise(w, h, scale, seed):
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    im = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im, np.float32) / 255.0


CACHE = Path("/tmp/leonida_base_v1.png")


@lru_cache(maxsize=1)
def base_map() -> Image.Image:
    if CACHE.exists():
        return Image.open(CACHE).convert("RGB")
    im = _draw()
    im.save(CACHE)
    return im


def _draw() -> Image.Image:
    geo = json.loads(GEO.read_text())
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    for poly in geo["state"]:
        rings = [[to_px(x, y) for x, y in r] for r in poly]
        d.polygon(rings[0], fill=255)
        for hole in rings[1:]:
            d.polygon(hole, fill=0)
    # cut the panhandle with a wobbly fake coastline
    rng = np.random.default_rng(7)
    cx = to_px(CUT_LON, 0)[0]
    edge = [(cx + 75 * math.sin(y / 230) + 25 * math.sin(y / 57) + rng.normal(0, 6), y) for y in range(0, int(to_px(0, 29.4)[1]), 20)]
    d.polygon([(0, 0)] + edge + [(0, edge[-1][1])], fill=0)
    ty = to_px(0, 30.42)[1]          # wobbly north coast instead of the straight state line
    top = [(x, ty + 70 * math.sin(x / 260) + 30 * math.sin(x / 61) + rng.normal(0, 5)) for x in range(0, W, 20)]
    d.polygon([(0, 0), (W, 0)] + top[::-1], fill=0)
    keys = [(-80.45, 25.2), (-80.6, 25.0), (-80.8, 24.88), (-81.05, 24.76), (-81.3, 24.68), (-81.55, 24.62), (-81.78, 24.56)]
    for i, (lon, lat) in enumerate(keys):   # make the island chain readable
        x, y = to_px(lon, lat)
        rr = 26 + (i % 3) * 8
        d.ellipse([x - rr * 1.8, y - rr * .7, x + rr * 1.8, y + rr * .7], fill=255)
    # organic coastline
    m = np.asarray(mask.filter(ImageFilter.GaussianBlur(6)), np.float32) / 255
    m = m + (_noise(W, H, 18, 1) - 0.5) * 0.35
    land = (m > 0.5).astype(np.float32)
    landI = Image.fromarray((land * 255).astype(np.uint8))

    # ocean: deep blue with a lighter centre
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W * .55) / W) ** 2 + ((yy - H * .55) / H) ** 2)
    deep = np.array([14, 52, 104], np.float32)
    mid = np.array([28, 92, 160], np.float32)
    k = np.clip(r * 1.6, 0, 1)[..., None]
    img = mid * (1 - k) + deep * k
    img += (_noise(W, H, 260, 2)[..., None] - .5) * 12
    # shallow water halo
    halo = np.asarray(landI.filter(ImageFilter.MaxFilter(41)).filter(ImageFilter.GaussianBlur(28)), np.float32) / 255
    shallow = np.array([90, 190, 215], np.float32)
    img = img * (1 - halo[..., None] * .75) + shallow * halo[..., None] * .75
    # land colours: green with sandy and dark patches
    n1, n2 = _noise(W, H, 320, 3), _noise(W, H, 120, 4)
    green = np.array([118, 158, 96], np.float32)
    dark = np.array([78, 120, 70], np.float32)
    sand = np.array([214, 200, 150], np.float32)
    swamp = np.array([96, 140, 110], np.float32)
    lc = green * (1 - n1[..., None]) + dark * n1[..., None]
    south = np.clip((yy - to_px(0, 26.3)[1]) / 500, 0, 1)[..., None]            # everglades tint
    lc = lc * (1 - south * .6) + swamp * south * .6
    sp = np.clip((n2[..., None] - .72) * 4, 0, 1) * .45
    lc = lc * (1 - sp) + sand * sp
    lc += (_noise(W, H, 14, 5)[..., None] - .5) * 10
    beach = np.asarray(landI.filter(ImageFilter.MinFilter(9)), np.float32) / 255
    rim = (land - beach)[..., None]
    lc = lc * (1 - rim) + np.array([235, 222, 178], np.float32) * rim
    img = img * (1 - land[..., None]) + lc * land[..., None]
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

    d = ImageDraw.Draw(out, "RGBA")
    # city patches (grey/white urban texture)
    for lon, lat, rad in [(-80.25, 25.85, 150), (-80.15, 26.25, 110), (-80.1, 26.7, 90), (-82.5, 27.95, 120),
                          (-81.38, 28.54, 110), (-81.87, 26.62, 80), (-81.65, 30.3, 100)]:
        x, y = to_px(lon, lat)
        for i in range(70):
            a, rr = rng.uniform(0, 6.28), rng.uniform(0, rad)
            px, py = x + rr * math.cos(a), y + rr * math.sin(a)
            if land[int(min(H - 1, max(0, py))), int(min(W - 1, max(0, px)))] > 0:
                s = rng.uniform(10, 26)
                d.rectangle([px, py, px + s, py + s * rng.uniform(.6, 1.4)], fill=(225, 228, 232, 210))
    # county borders (faint, only on land)
    lines = Image.new("L", (W, H), 0)
    dl = ImageDraw.Draw(lines)
    for poly in geo["counties"]:
        pts = [to_px(x, y) for x, y in poly[0]]
        dl.line(pts + [pts[0]], fill=40, width=3)
    lines = Image.fromarray((np.asarray(lines, np.float32) * land).astype(np.uint8))
    out.paste(Image.new("RGB", (W, H), (255, 255, 255)), (0, 0), lines)
    # lake
    lx, ly = to_px(*PLACES["Lake Leonida"])
    d.ellipse([lx - 105, ly - 120, lx + 105, ly + 110], fill=(70, 150, 200, 255), outline=(235, 222, 178, 255), width=6)
    # highways
    roads = [[(-80.2, 25.75), (-80.12, 26.3), (-80.05, 26.9), (-80.4, 27.6), (-80.8, 28.3), (-81.1, 29.2), (-81.6, 30.3)],
             [(-80.35, 25.85), (-81.3, 26.15), (-81.8, 26.6), (-82.3, 27.4), (-82.45, 28.2), (-82.3, 29.2), (-82.6, 30.3)],
             [(-80.3, 26.0), (-80.75, 27.0), (-81.2, 27.9), (-81.4, 28.5), (-81.9, 28.9), (-82.2, 29.4)],
             [(-80.45, 25.45), (-80.6, 25.15), (-80.95, 24.85), (-81.3, 24.68), (-81.75, 24.56)]]
    for rd in roads:
        pts = [to_px(*p) for p in rd]
        d.line(pts, fill=(250, 250, 250, 200), width=7, joint="curve")
    # county labels
    f = _font(30, black=False)
    for name, lon, lat in COUNTIES:
        x, y = to_px(lon, lat)
        d.text((x, y), name, font=f, fill=(255, 255, 255, 120), anchor="mm")
    x, y = to_px(-81.3, 28.0)
    d.text((x, y), "L E O N I D A", font=_font(110), fill=(255, 255, 255, 70), anchor="mm")
    return out


if __name__ == "__main__":
    im = base_map()
    im.resize((W // 3, H // 3)).save("/tmp/leonida_preview.jpg", quality=90)
    print("saved")
