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
