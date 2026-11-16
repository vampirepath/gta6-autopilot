"""Animated country map: neon-highlighted country + flag + name.
Map data: Natural Earth via world-atlas (public domain). Flags: flagcdn.com (public domain)."""
import io
import json
import math
from functools import lru_cache
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter

from .common import ROOT, log
from .pill import make_pill

GEO = ROOT / "assets" / "geo" / "countries-50m.json"
ALIASES = {"usa": "United States", "us": "United States", "america": "United States", "uk": "United Kingdom",
           "britain": "United Kingdom", "korea": "South Korea", "uae": "United Arab Emirates",
           "russia": "Russia", "gulf": "Saudi Arabia"}


@lru_cache(1)
def _topo():
    return json.loads(GEO.read_text())


def _arcs():
    t = _topo()
    sx, sy = t["transform"]["scale"]
    tx, ty = t["transform"]["translate"]
    out = []
    for arc in t["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx; y += dy
            pts.append((x * sx + tx, y * sy + ty))
        out.append(pts)
    return out


def _ring(idx_list, arcs):
    pts = []
    for i in idx_list:
        a = arcs[i] if i >= 0 else list(reversed(arcs[~i]))
        pts.extend(a if not pts else a[1:])
    return pts


def _countries():
    t, arcs = _topo(), _arcs()
    res = {}
    for g in t["objects"]["countries"]["geometries"]:
        name = g.get("properties", {}).get("name", "")
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]] if g["type"] == "Polygon" else []
        rings = [_ring(p[0], arcs) for p in polys if p]
        res[name] = {"rings": rings, "id": g.get("id")}
    return res


def resolve(name: str) -> tuple[str, str] | None:
    """Return (map name, alpha2) for a country name."""
    import pycountry
    n = ALIASES.get(name.lower().strip(), name.strip())
    cs = _countries()
    try:
        pc = pycountry.countries.lookup(n)
    except LookupError:
        try:
            pc = pycountry.countries.search_fuzzy(n)[0]
        except Exception:
            return None
    for key in (n, getattr(pc, "common_name", ""), pc.name, getattr(pc, "official_name", "")):
        if key in cs:
            return key, pc.alpha_2
    for k, v in cs.items():
        if v["id"] and str(int(v["id"])) == str(int(pc.numeric)):
            return k, pc.alpha_2
    return None


def render_map(country: str, out: Path) -> Path | None:
    r = resolve(country)
    if not r:
        log.warning("map: unknown country %s", country)
        return None
    mname, a2 = r
    cs = _countries()
    target = cs[mname]["rings"]
    # bounding box of the country (largest rings), handle tiny countries
    xs = [p[0] for ring in target for p in ring]
    ys = [p[1] for ring in target for p in ring]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    span = max(max(xs) - min(xs), (max(ys) - min(ys)) * 1.2, 4)
    W, H = 2160, 3840
    lon_span = span * 2.6
    k = W / lon_span
    coslat = math.cos(math.radians(cy))

    def P(lon, lat):
        return ((lon - cx) * k * coslat + W / 2, (cy - lat) * k + H * 0.47)

    img = Image.new("RGB", (W, H), (10, 8, 26))
    d = ImageDraw.Draw(img)
    # subtle grid
    for gx in range(-180, 181, 5):
        x, _ = P(gx, cy)
        if 0 <= x <= W:
            d.line((x, 0, x, H), fill=(26, 20, 52), width=2)
    for gy in range(-85, 86, 5):
        _, y = P(cx, gy)
        if 0 <= y <= H:
            d.line((0, y, W, y), fill=(26, 20, 52), width=2)
    # neighbours
    for name, c in cs.items():
        for ring in c["rings"]:
            pts = [P(*p) for p in ring]
            if not any(-W < x < 2 * W and -H < y < 2 * H for x, y in pts):
                continue
            if name == mname:
                continue
            d.polygon(pts, fill=(44, 34, 78), outline=(90, 70, 150))
    # glow + target
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for ring in target:
        gd.polygon([P(*p) for p in ring], fill=(255, 60, 200, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    d = ImageDraw.Draw(img)
    for ring in target:
        pts = [P(*p) for p in ring]
        d.polygon(pts, fill=(214, 60, 230), outline=(255, 220, 255))
        d.line(pts + [pts[0]], fill=(255, 235, 255), width=8)
    # flag
    try:
        fr = requests.get(f"https://flagcdn.com/w640/{a2.lower()}.png", timeout=20)
        if fr.ok:
            flag = Image.open(io.BytesIO(fr.content)).convert("RGBA")
            fw = 620
            flag = flag.resize((fw, int(flag.height * fw / flag.width)))
            fx, fy = (W - fw) // 2, int(H * 0.25)
            pad = Image.new("RGBA", (fw + 24, flag.height + 24), (255, 255, 255, 255))
            img.alpha_composite(pad, (fx - 12, fy - 12))
            img.alpha_composite(flag, (fx, fy))
    except Exception as e:
        log.warning("flag failed: %s", e)
    # country name
    pill = make_pill(mname, out.with_suffix(".pill.png"), size=170, max_w=1900)
    pl = Image.open(pill)
    img.alpha_composite(pl, ((W - pl.width) // 2, int(H * 0.15)))
    img.convert("RGB").save(out, quality=92)
    return out


# ---------------- extra map styles (so maps never look the same) ------------------
GEO110 = ROOT / "assets" / "geo" / "countries-110m.json"


@lru_cache(1)
def _countries110():
    t = json.loads(GEO110.read_text())
    sx, sy = t["transform"]["scale"]
    tx, ty = t["transform"]["translate"]
    arcs = []
    for arc in t["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx; y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    res = {}
    for g in t["objects"]["countries"]["geometries"]:
        name = g.get("properties", {}).get("name", "")
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]] if g["type"] == "Polygon" else []
        res[name] = [_ring(p[0], arcs) for p in polys if p]
    return res


def _flag(a2: str):
    try:
        fr = requests.get(f"https://flagcdn.com/w1280/{a2.lower()}.png", timeout=20)
        if fr.ok:
            return Image.open(io.BytesIO(fr.content)).convert("RGBA")
    except Exception:
        pass
    return None


def render_flag_silhouette(country: str, out: Path) -> Path | None:
    """The country's shape filled with its own flag, glowing outline, name pill on top."""
    r = resolve(country)
    if not r:
        return None
    mname, a2 = r
    rings = _countries()[mname]["rings"]
    rings = sorted(rings, key=lambda rg: -len(rg))[:12]
    xs = [p[0] for rg in rings for p in rg]; ys = [p[1] for rg in rings for p in rg]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    coslat = math.cos(math.radians(cy))
    w_deg, h_deg = (max(xs) - min(xs)) * coslat, max(ys) - min(ys)
    W, H = 2160, 3840
    k = min(W * 0.82 / max(w_deg, 1e-3), H * 0.5 / max(h_deg, 1e-3))

    def P(lon, lat):
        return ((lon - cx) * coslat * k + W / 2, (cy - lat) * k + H * 0.52)

    bg = Image.new("RGBA", (W, H), (12, 6, 28, 255))
    # radial glow background
    glow_bg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow_bg).ellipse((W * 0.05, H * 0.25, W * 0.95, H * 0.8), fill=(120, 30, 170, 140))
    bg.alpha_composite(glow_bg.filter(ImageFilter.GaussianBlur(160)))
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    for rg in rings:
        md.polygon([P(*p) for p in rg], fill=255)
    box = mask.getbbox() or (0, 0, W, H)
    flag = _flag(a2)
    fill = Image.new("RGBA", (W, H), (214, 60, 230, 255))
    if flag:
        bw, bh = box[2] - box[0], box[3] - box[1]
        s = max(bw / flag.width, bh / flag.height)
        f2 = flag.resize((int(flag.width * s) + 2, int(flag.height * s) + 2), Image.LANCZOS)
        fill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fill.alpha_composite(f2, (box[0] - (f2.width - bw) // 2, box[1] - (f2.height - bh) // 2))
    glow = Image.new("RGBA", (W, H), (255, 80, 220, 0))
    glow.putalpha(mask.filter(ImageFilter.GaussianBlur(45)).point(lambda v: int(v * 0.9)))
    bg.alpha_composite(glow)
    country_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    country_img.paste(fill, (0, 0), mask)
    bg.alpha_composite(country_img)
    d = ImageDraw.Draw(bg)
    for rg in rings:
        pts = [P(*p) for p in rg]
        d.line(pts + [pts[0]], fill=(255, 240, 255, 255), width=9)
    pill = make_pill(mname, out.with_suffix(".pill.png"), size=170, max_w=1900)
    pl = Image.open(pill)
    bg.alpha_composite(pl, ((W - pl.width) // 2, int(H * 0.13)))
    bg.convert("RGB").save(out, quality=92)
    return out


def render_globe_frames(country: str, out_dir: Path, dur: float, fps: int = 30) -> Path | None:
    """Spinning globe (orthographic) that rotates to the country and lights it up. Returns a frames folder."""
    r = resolve(country)
    if not r:
        return None
    mname, a2 = r
    world = _countries110()
    # target centre from the detailed map
    rings = _countries()[mname]["rings"]
    xs = [p[0] for rg in rings for p in rg]; ys = [p[1] for rg in rings for p in rg]
    lon0, lat0 = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    S = 1080                      # rendered at 1080x1920 directly
    W, H, R = 1080, 1920, 430
    cxs, cys = W / 2, H * 0.48
    n = max(1, round(dur * fps))
    out_dir.mkdir(parents=True, exist_ok=True)
    start_lon = lon0 - 110
    flag = _flag(a2)
    pill = Image.open(make_pill(mname, out_dir / "pill.png", size=96, max_w=980))
    stars = Image.new("RGBA", (W, H), (8, 4, 22, 255))
    sd = ImageDraw.Draw(stars)
    import random as _r
    rr = _r.Random(3)
    for _ in range(260):
        x, y = rr.randrange(W), rr.randrange(H)
        sd.ellipse((x, y, x + 2, y + 2), fill=(200, 190, 255, rr.randrange(80, 255)))
    anim_n = min(n, int(1.6 * fps))
    last = None
    for f in range(n):
        p = out_dir / f"{f:04d}.png"
        if f >= anim_n and last is not None:
            p.write_bytes(last.read_bytes())
            continue
        k = 1 - (1 - min(1, f / max(anim_n - 1, 1))) ** 3
        lam0 = math.radians(start_lon + (lon0 - start_lon) * k)
        phi0 = math.radians(lat0 * k)
        img = stars.copy()
        d = ImageDraw.Draw(img)
        # atmosphere glow + ocean
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((cxs - R - 40, cys - R - 40, cxs + R + 40, cys + R + 40), fill=(170, 70, 255, 160))
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(30)))
        d = ImageDraw.Draw(img)
        d.ellipse((cxs - R, cys - R, cxs + R, cys + R), fill=(24, 14, 58, 255), outline=(200, 150, 255, 255), width=3)

        def proj(lon, lat):
            lam, phi = math.radians(lon), math.radians(lat)
            cosc = math.sin(phi0) * math.sin(phi) + math.cos(phi0) * math.cos(phi) * math.cos(lam - lam0)
            x = R * math.cos(phi) * math.sin(lam - lam0)
            y = R * (math.cos(phi0) * math.sin(phi) - math.sin(phi0) * math.cos(phi) * math.cos(lam - lam0))
            return cosc, (cxs + x, cys - y)

        for name, rgs in world.items():
            hit = name == mname or (name in mname or mname in name)
            for rg in rgs:
                pts, vis = [], 0
                for lon, lat in rg:
                    c, xy = proj(lon, lat)
                    if c > 0:
                        vis += 1
                    pts.append(xy)
                if vis < len(rg) * 0.6 or len(pts) < 3:
                    continue
                if hit and k > 0.85:
                    d.polygon(pts, fill=(255, 70, 220, 255), outline=(255, 240, 255, 255))
                else:
                    d.polygon(pts, fill=(74, 56, 130, 255), outline=(120, 96, 190, 255))
        if k > 0.85:   # pulse ring on the country
            c, (px, py) = proj(lon0, lat0)
            pr = int(30 + 60 * ((f % fps) / fps))
            d.ellipse((px - pr, py - pr, px + pr, py + pr), outline=(255, 230, 255, 200), width=6)
        img.alpha_composite(pill, ((W - pill.width) // 2, int(H * 0.12)))
        if flag:
            fw = 300
            fl = flag.resize((fw, int(flag.height * fw / flag.width)))
            img.alpha_composite(fl, ((W - fw) // 2, int(H * 0.12) + pill.height + 10))
        img.convert("RGB").save(p, compress_level=1)
        last = p
    return out_dir
