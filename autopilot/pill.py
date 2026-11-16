"""Purple glowing "pill" labels – the key-phrase callouts used in viral GTA news Shorts."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .common import FONT_DIR

FONT = FONT_DIR / "Anton-Regular.ttf"
FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _font(size: int):
    try:
        return ImageFont.truetype(str(FONT), size)
    except OSError:
        return ImageFont.truetype(FALLBACK, size)


def _wrap(text: str, font, max_w: int, draw) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_pill(text: str, out: Path, size: int = 84, max_w: int = 900,
              fill=(150, 26, 190), fill2=(184, 52, 214), border=(255, 230, 255), glow=(214, 80, 255)) -> Path:
    """Render a label PNG (transparent background) with a purple gradient, light border and glow."""
    text = text.upper().strip()
    font = _font(size)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lines = _wrap(text, font, max_w - 60, tmp)
    asc, desc = font.getmetrics()
    line_h = int(size * 1.08)
    tw = max(int(tmp.textlength(l, font=font)) for l in lines)
    pad_x, pad_y, glow_r = int(size * 0.38), int(size * 0.16), int(size * 0.45)
    bw, bh = tw + 2 * pad_x, line_h * len(lines) + 2 * pad_y + int(size * 0.12)
    W, H = bw + 4 * glow_r, bh + 4 * glow_r
    x0, y0 = 2 * glow_r, 2 * glow_r
    radius = int(size * 0.18)

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # glow
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).rounded_rectangle([x0 - 6, y0 - 6, x0 + bw + 6, y0 + bh + 6], radius + 6, fill=glow + (200,))
    img = Image.alpha_composite(img, g.filter(ImageFilter.GaussianBlur(glow_r * 0.75)))
    # body: vertical gradient
    body = Image.new("RGBA", (bw, bh))
    bd = ImageDraw.Draw(body)
    for yy in range(bh):
        k = yy / max(bh - 1, 1)
        c = tuple(int(fill2[i] * (1 - k) + fill[i] * k) for i in range(3))
        bd.line([(0, yy), (bw, yy)], fill=c + (255,))
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, bw - 1, bh - 1], radius, fill=255)
    img.paste(body, (x0, y0), mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius, outline=border + (255,), width=max(3, size // 22))
    # text with soft shadow
    y = y0 + pad_y - int(size * 0.02)
    for l in lines:
        lw = d.textlength(l, font=font)
        x = x0 + (bw - lw) / 2
        d.text((x + 3, y + 4), l, font=font, fill=(60, 0, 80, 160))
        d.text((x, y), l, font=font, fill=(255, 255, 255, 255))
        y += line_h
    img.save(out)
    return out
