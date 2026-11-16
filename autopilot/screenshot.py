"""'Proof' shots: a phone-sized screenshot of the source article with its headline highlighted,
like news Shorts flash on screen ("PC Gamer reports…")."""
from pathlib import Path

from .common import log

JS_CLEAN = """
() => {
  // remove cookie banners, sticky headers, popups, ads
  for (const el of document.querySelectorAll('*')) {
    const s = getComputedStyle(el);
    if ((s.position === 'fixed' || s.position === 'sticky') && el.tagName !== 'HTML' && el.tagName !== 'BODY') el.remove();
  }
  for (const sel of ['[id*=cookie]','[class*=cookie]','[id*=consent]','[class*=consent]','iframe','[class*=newsletter]','[class*=paywall]'])
    document.querySelectorAll(sel).forEach(e => e.remove());
  document.documentElement.style.overflow = 'auto'; document.body.style.overflow = 'auto';
  const h = document.querySelector('h1');
  if (h) { h.scrollIntoView({block: 'center'}); window.scrollBy(0, Math.round(window.innerHeight * 0.18)); }
  return !!h;
}
"""

JS_FIND = """
(keywords) => {
  // find the paragraph that best matches what the voiceover says, put it in view
  const kws = keywords.map(k => k.toLowerCase());
  let best = null, bestScore = 0;
  for (const el of document.querySelectorAll('article p, main p, p, li')) {
    const t = (el.innerText || '').toLowerCase();
    if (t.length < 60 || t.length > 900) continue;
    let sc = 0; for (const k of kws) if (t.includes(k)) sc += k.length > 5 ? 2 : 1;
    if (sc > bestScore) { bestScore = sc; best = el; }
  }
  const target = (best && bestScore >= 2) ? best : document.querySelector('h1');
  if (!target) return false;
  target.setAttribute('data-hl', '1');
  target.scrollIntoView({block: 'center'});
  window.scrollBy(0, -Math.round(window.innerHeight * 0.05));
  return true;
}
"""

JS_HIGHLIGHT = """
() => {
  const el = document.querySelector('[data-hl]') || document.querySelector('h1');
  if (!el) return false;
  // highlighter-marker look (like news Shorts): yellow marker behind the text
  el.style.backgroundImage = 'linear-gradient(transparent 12%, #ffe23d 12%, #ffe23d 88%, transparent 88%)';
  el.style.boxDecorationBreak = 'clone'; el.style.webkitBoxDecorationBreak = 'clone';
  el.style.color = '#000'; el.style.display = 'inline'; el.style.fontWeight = '700';
  el.style.padding = '0 4px';
  return true;
}
"""


def article_shots(url: str, out_dir: Path, keywords: list[str] | None = None) -> tuple[Path, Path] | None:
    """Returns (plain, highlighted) 1080x1920 PNGs, or None if the page can't be captured."""
    if not url or "news.google.com" in url or "reddit.com" in url:
        return None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    plain, hi = out_dir / "article.png", out_dir / "article_hi.png"
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            ctx = b.new_context(viewport={"width": 432, "height": 768}, device_scale_factor=2.5,
                                is_mobile=True, has_touch=True,
                                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                                           "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3500)
            if not page.evaluate(JS_CLEAN):
                b.close()
                return None
            page.evaluate(JS_FIND, keywords or [])
            page.wait_for_timeout(800)
            page.screenshot(path=str(plain))
            page.evaluate(JS_HIGHLIGHT)
            page.wait_for_timeout(200)
            page.screenshot(path=str(hi))
            b.close()
        return plain, hi
    except Exception as e:
        log.warning("article screenshot failed: %s", e)
        return None


def article_photo(url: str, out_dir: Path) -> Path | None:
    """The article's main image (og:image) – used only if the AI confirms it's a GTA game screenshot/artwork
    (never photos of real people, never other outlets' thumbnails with their own branding)."""
    import base64
    import json
    import re

    import requests
    from PIL import Image

    from .llm import ask
    if not url or "news.google.com" in url or "reddit.com" in url:
        return None
    try:
        html = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
        m = re.search(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)', html) or \
            re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:image', html)
        if not m:
            return None
        img_url = m.group(1).replace("&amp;", "&")
        raw = requests.get(img_url, timeout=30, headers={"User-Agent": "Mozilla/5.0", "Referer": url}).content
        p = out_dir / "photo.jpg"
        im = Image.open(__import__("io").BytesIO(raw)).convert("RGB")
        if im.width < 700:
            return None
        im.save(p, quality=90)
        small = im.copy(); small.thumbnail((512, 512))
        from io import BytesIO
        buf = BytesIO(); small.save(buf, "JPEG", quality=80)
        verdict = ask('Reply ONLY JSON {"game": true/false, "real_person": true/false, "text_heavy": true/false}. '
                      '"game": is this a video game screenshot or official game artwork (e.g. from GTA)? '
                      '"real_person": does it show a real (non-game) human photo? '
                      '"text_heavy": is it mostly text, a logo, or a thumbnail with big added text?',
                      image_jpeg_b64=base64.b64encode(buf.getvalue()).decode(), max_tokens=1024, retries=2)
        v = json.loads(re.search(r"\{.*\}", verdict, re.S).group(0))
        if v.get("game") and not v.get("real_person") and not v.get("text_heavy"):
            return p
        log.info("article photo rejected: %s", v)
    except Exception as e:
        log.warning("article photo failed: %s", e)
    return None
