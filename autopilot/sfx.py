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


def path(name: str) -> Path:
    p = SFX_DIR / f"{name}.wav"
    if not p.exists():
        build()
    return p


if __name__ == "__main__":
    build()
    print("built", sorted(x.name for x in SFX_DIR.glob("*.wav")))
