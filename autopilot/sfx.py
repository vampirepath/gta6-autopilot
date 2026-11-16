"""Sound effects, synthesised in code (no copyright issues): whoosh, pop, click, boom, riser, ding."""
import wave
from pathlib import Path

import numpy as np

from .common import ROOT

SFX_DIR = ROOT / "assets" / "sfx"
SR = 48000


def _save(name: str, x: np.ndarray):
    x = np.clip(x / (np.abs(x).max() + 1e-9) * 0.9, -1, 1)
    st = np.stack([x, x], 1)
    with wave.open(str(SFX_DIR / f"{name}.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def _env(n, a, r):
    e = np.ones(n)
    a, r = int(a * SR), int(r * SR)
    e[:a] = np.linspace(0, 1, a)
    e[-r:] *= np.linspace(1, 0, r) ** 2
    return e


def _sweep_noise(dur, f0, f1, q=6.0, seed=0):
    """Band-pass filtered noise whose centre frequency sweeps f0 -> f1."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    fc = np.geomspace(f0, f1, n)
    y1 = y2 = 0.0
    x1 = x2 = 0.0
    for i in range(n):  # simple resonant biquad band-pass, coefficients per sample
        w0 = 2 * np.pi * fc[i] / SR
        alpha = np.sin(w0) / (2 * q)
        b0, a0, a1, a2 = alpha, 1 + alpha, -2 * np.cos(w0), 1 - alpha
        y = (b0 * noise[i] - b0 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1, y2, y1 = x1, noise[i], y1, y
        out[i] = y
    return out


def build():
    SFX_DIR.mkdir(parents=True, exist_ok=True)
    t = lambda d: np.arange(int(d * SR)) / SR
    # whoosh: noise sweep up then down
    d = 0.45
    w = _sweep_noise(d, 300, 4500, q=3, seed=1) * np.sin(np.pi * t(d) / d) ** 2
    _save("whoosh", w)
    # pop: short pitch-dropping sine blip
    d = 0.12
    tt = t(d)
    f = 900 * np.exp(-tt * 25) + 300
    _save("pop", np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 40))
    # click / camera shutter: two noise ticks
    d = 0.16
    n = np.random.default_rng(2).standard_normal(int(d * SR))
    e = np.exp(-t(d) * 120) + 0.7 * np.exp(-np.clip(t(d) - 0.07, 0, None) * 140) * (t(d) > 0.07)
    _save("click", n * e)
    # boom: deep sine drop + noise thump
    d = 1.4
    tt = t(d)
    f = 120 * np.exp(-tt * 3) + 38
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.2)
    boom += 0.25 * np.random.default_rng(3).standard_normal(len(tt)) * np.exp(-tt * 30)
    _save("boom", boom)
    # riser: rising noise + tone
    d = 1.2
    tt = t(d)
    r = _sweep_noise(d, 200, 6000, q=4, seed=4) * (tt / d) ** 2
    r += 0.3 * np.sin(2 * np.pi * np.cumsum(np.geomspace(200, 1200, len(tt))) / SR) * (tt / d) ** 3
    _save("riser", r)
    # ding: bright bell for numbers / money
    d = 0.9
    tt = t(d)
    ding = sum(a * np.sin(2 * np.pi * f * tt) for f, a in [(1320, 1), (2640, .4), (3960, .2)]) * np.exp(-tt * 6)
    _save("ding", ding)


def build_more():
    """Extra variety so transitions don't all sound the same."""
    t = lambda d: np.arange(int(d * SR)) / SR
    rng = np.random.default_rng(7)
    # whoosh variants: short/long, up/down, airy
    for i, (d, f0, f1, q) in enumerate([(0.30, 600, 6000, 2.5), (0.55, 4000, 400, 3), (0.40, 200, 2500, 5), (0.25, 1500, 9000, 1.5)], 1):
        w = _sweep_noise(d, f0, f1, q=q, seed=10 + i) * np.sin(np.pi * t(d) / d) ** (1.5 + i * 0.3)
        _save(f"whoosh{i}", w)
    # swish (very short)
    d = 0.16
    _save("swish", _sweep_noise(d, 2000, 8000, q=2, seed=21) * np.sin(np.pi * t(d) / d))
    # impacts: punchy low hits
    for i, (f, dec) in enumerate([(70, 6), (55, 4), (90, 9)], 1):
        d = 0.9
        tt = t(d)
        hit = np.sin(2 * np.pi * np.cumsum(f * np.exp(-tt * 4) + 30) / SR) * np.exp(-tt * dec)
        hit += 0.4 * rng.standard_normal(len(tt)) * np.exp(-tt * 45)
        _save(f"impact{i}", np.tanh(hit * 2))
    # typing (article on screen)
    d = 0.9
    ty = np.zeros(int(d * SR))
    for k in range(9):
        p0 = int((0.03 + k * 0.09 + rng.uniform(-0.02, 0.02)) * SR)
        n = int(0.025 * SR)
        ty[p0:p0 + n] += rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 260) * rng.uniform(0.5, 1)
    _save("typing", ty)
    # cash register / coins (money)
    d = 0.8
    tt = t(d)
    cash = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * k) for f, k in [(2093, 9), (2637, 11), (3136, 13)])
    cash[: int(0.03 * SR)] += rng.standard_normal(int(0.03 * SR)) * 0.8
    _save("cash", cash)
    # glitch (for twists / leaks)
    d = 0.35
    g = np.sign(np.sin(2 * np.pi * 180 * t(d))) * (rng.random(int(d * SR)) > 0.3)
    g = g * np.repeat(rng.random(int(d * 40) + 1), int(SR / 40) + 1)[: int(d * SR)]
    _save("glitch", g)
    # radar ping (maps)
    d = 1.0
    tt = t(d)
    _save("ping", np.sin(2 * np.pi * 1760 * tt) * np.exp(-tt * 5) + 0.5 * np.sin(2 * np.pi * 880 * tt) * np.exp(-tt * 4))
    # shutter
    d = 0.2
    n = rng.standard_normal(int(d * SR))
    e = np.exp(-t(d) * 90) + 0.8 * np.exp(-np.clip(t(d) - 0.09, 0, None) * 110) * (t(d) > 0.09)
    _save("shutter", n * e)


VARIANTS = {
    "whoosh": ["whoosh", "whoosh1", "whoosh2", "whoosh3", "whoosh4", "swish"],
    "impact": ["impact1", "impact2", "impact3", "boom"],
}


def pick(kind: str) -> str:
    import random
    return random.choice(VARIANTS.get(kind, [kind]))


def path(name: str) -> Path:
    p = SFX_DIR / f"{name}.wav"
    if not p.exists():
        build()
        build_more()
    return p


if __name__ == "__main__":
    build()
    build_more()
    print("built", sorted(x.name for x in SFX_DIR.glob("*.wav")))
