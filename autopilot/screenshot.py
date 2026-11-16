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

JS_HIGHLIGHT = """
() => {
  const h = document.querySelector('h1');
  if (!h) return false;
  h.style.background = '#000'; h.style.color = '#fff';
  h.style.boxDecorationBreak = 'clone'; h.style.webkitBoxDecorationBreak = 'clone';
  h.style.display = 'inline'; h.style.padding = '2px 6px'; h.style.lineHeight = '1.45';
  return true;
}
"""


def article_shots(url: str, out_dir: Path) -> tuple[Path, Path] | None:
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
