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
