"""Copyright-free background beat, generated in code (dark trap / phonk-ish loop).

Used when the music/ folder is empty. Drop your own royalty-free .mp3 files in music/
(GitHub → music folder → Add file → Upload files) and those are used instead.
"""
import wave
from pathlib import Path

import numpy as np

SR = 44100


def _kick(n):
    t = np.arange(n) / SR
    f = 150 * np.exp(-t * 28) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def _snare(n, rng):
    t = np.arange(n) / SR
    return (rng.standard_normal(n) * np.exp(-t * 22) * 0.7 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.5)


def _hat(n, rng, decay=90):
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    x = np.diff(np.concatenate([[0], x]))  # crude high-pass
    return x * np.exp(-t * decay) * 0.35


def _808(n, freq):
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t + 0.6 * np.sin(2 * np.pi * freq * 2 * t))
    return np.tanh(x * 1.6) * np.exp(-t * 1.4)


def _pad(n, freqs):
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * 0.3 * t)) for f in freqs) / len(freqs)
    a = min(n, int(0.4 * SR))
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a)
    env[-a:] = np.linspace(1, 0, a)
    return x * env


def make_beat(out: Path, seconds: float = 75, seed: int = 0, bpm: int = 140):
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    step = beat / 4                                  # 16th notes
    bar = beat * 4
    total = int(seconds * SR)
    mix = np.zeros(total + SR * 2)
    # dark minor progressions (root, chord) – A minor family
    progs = [[(55, [220, 261.6, 329.6]), (43.65, [174.6, 220, 261.6]), (49, [196, 246.9, 293.7]), (41.2, [164.8, 207.7, 246.9])],
             [(55, [220, 261.6, 329.6]), (58.27, [233.1, 277.2, 349.2]), (43.65, [174.6, 220, 261.6]), (49, [196, 246.9, 293.7])]]
    prog = progs[seed % len(progs)]
    kick_pat = [[0, 6, 10], [0, 3, 8, 11], [0, 7, 10, 14]][seed % 3]
    n_bars = int(seconds / bar) + 1
    for b in range(n_bars):
        b0 = b * bar
        root, chord = prog[b % len(prog)]
        i = int(b0 * SR)
        n = int(bar * SR)
        mix[i:i + n] += 0.10 * _pad(n, chord)[: len(mix[i:i + n])]
        mix[i:i + n] += 0.42 * _808(n, root)[: len(mix[i:i + n])]
        for s in range(16):
            t0 = int((b0 + s * step) * SR)
            if t0 >= total:
                break
            if s in kick_pat:
                k = _kick(int(0.4 * SR)); mix[t0:t0 + len(k)] += 0.8 * k[: len(mix[t0:t0 + len(k)])]
            if s in (4, 12):
                sn = _snare(int(0.3 * SR), rng); mix[t0:t0 + len(sn)] += 0.45 * sn[: len(mix[t0:t0 + len(sn)])]
            # hats: 8ths with random 32nd rolls
            if s % 2 == 0 or rng.random() < 0.25:
                hn = _hat(int(0.06 * SR), rng); mix[t0:t0 + len(hn)] += hn[: len(mix[t0:t0 + len(hn)])]
                if rng.random() < 0.12:
                    t1 = t0 + int(step / 2 * SR)
                    mix[t1:t1 + len(hn)] += 0.8 * hn[: len(mix[t1:t1 + len(hn)])]
    mix = mix[:total]
    mix = np.tanh(mix * 1.2)
    fade = int(1.5 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.85
    st = np.stack([mix, mix], 1)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    return out


if __name__ == "__main__":
    make_beat(Path("/tmp/beat.wav"), 20, seed=1)


# ---------------- Vice City synthwave (80s Miami vibe) ---------------------------
def _saw(freq, n, detune=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for d in (-detune, 0, detune):
        ph = (freq * (1 + d) * t) % 1.0
        out += 2 * ph - 1
    return out / 3


def _lp(x, a=0.15):
    """one-pole low-pass (cheap 'analog' softening)."""
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def make_synthwave(out: Path, seconds: float = 75, seed: int = 0, bpm: int = 104):
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    step = beat / 4
    bar = beat * 4
    total = int(seconds * SR)
    mix = np.zeros(total + SR * 2)
    # classic 80s progressions (Am F C G / Fm Db Ab Eb ...)
    progs = [[(110, [220, 261.6, 329.6]), (87.3, [174.6, 220, 261.6]), (130.8, [261.6, 329.6, 392]), (98, [196, 246.9, 293.7])],
             [(87.3, [174.6, 207.7, 261.6]), (69.3, [138.6, 174.6, 207.7]), (103.8, [207.7, 261.6, 311.1]), (77.8, [155.6, 196, 233.1])]]
    prog = progs[seed % len(progs)]
    n_bars = int(seconds / bar) + 1
    for b in range(n_bars):
        b0 = b * bar
        root, chord = prog[b % len(prog)]
        i0, n = int(b0 * SR), int(bar * SR)
        seg = slice(i0, i0 + n)
        L = len(mix[seg])
        # pad: detuned saws, softened
        pad = sum(_saw(f, n, 0.004) for f in chord) / 3
        env = np.minimum(1, np.arange(n) / (0.3 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.2 * SR))
        mix[seg] += 0.12 * _lp(pad * env, 0.08)[:L]
        for s in range(16):
            t0 = int((b0 + s * step) * SR)
            if t0 >= total:
                break
            # pulsing octave bass on every 8th
            if s % 2 == 0:
                bn = int(step * 2 * SR)
                f = root / 2 if (s // 2) % 2 == 0 else root
                bs = _lp(_saw(f, bn, 0.002), 0.12) * np.exp(-np.arange(bn) / SR * 6)
                mix[t0:t0 + bn] += 0.35 * bs[: len(mix[t0:t0 + bn])]
            # arpeggio (16ths) through the chord, one octave up
            an = int(step * SR)
            af = chord[s % 3] * 2
            ar = _lp(_saw(af, an, 0.003), 0.3) * np.exp(-np.arange(an) / SR * 14)
            mix[t0:t0 + an] += 0.10 * ar[: len(mix[t0:t0 + an])]
            # drums: kick 1 & 3, big gated snare 2 & 4, hats on 8ths
            if s in (0, 8) or (s == 10 and rng.random() < 0.3):
                k = _kick(int(0.35 * SR)); mix[t0:t0 + len(k)] += 0.9 * k[: len(mix[t0:t0 + len(k)])]
            if s in (4, 12):
                sn = _snare(int(0.28 * SR), rng)
                gate = np.ones(len(sn)); gate[int(0.18 * SR):] = 0     # 80s gated reverb feel
                tail = rng.standard_normal(len(sn)) * 0.25 * gate
                sn = (sn + tail) * gate
                mix[t0:t0 + len(sn)] += 0.55 * sn[: len(mix[t0:t0 + len(sn)])]
            if s % 2 == 1:
                hn = _hat(int(0.05 * SR), rng, 120); mix[t0:t0 + len(hn)] += 0.6 * hn[: len(mix[t0:t0 + len(hn)])]
    mix = np.tanh(mix[:total] * 1.1)
    fade = int(1.5 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.85
    # light stereo widening via short delay on one side
    d = int(0.012 * SR)
    left, right = mix, np.concatenate([np.zeros(d), mix[:-d]])
    st = np.stack([left, right], 1)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    return out
