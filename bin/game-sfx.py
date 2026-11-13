#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
"""Synthesise a game sound effect from code, so we own the sample outright.

    game-sfx.py RECIPE OUT.wav [--seconds S] [--seed N] [--pitch X]

Recipes: click (a metal snap, a hammer or trigger), sizzle (a fuse or pan
hiss with crackle, swelling toward the end), boom (a black-powder or cannon
bang with a long rumble), pew (a laser shot). Writes 44.1 kHz mono 16-bit
WAV. The same arguments always give the same file, so a sound is a command
line, not a recording. Filtered noise and pitch sweeps, no samples, no
third-party licence.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

RATE = 44100


def t(seconds: float) -> np.ndarray:
    return np.arange(int(seconds * RATE)) / RATE


def noise(seconds: float, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).uniform(-1, 1, int(seconds * RATE))


def band(x: np.ndarray, lo: float | None, hi: float | None) -> np.ndarray:
    if lo and hi:
        sos = butter(4, [lo, hi], "bandpass", fs=RATE, output="sos")
    elif lo:
        sos = butter(4, lo, "highpass", fs=RATE, output="sos")
    else:
        sos = butter(4, hi, "lowpass", fs=RATE, output="sos")
    return sosfilt(sos, x)


def norm(x: np.ndarray, peak: float) -> np.ndarray:
    return x * (peak / max(1e-9, np.abs(x).max()))


def fade(x: np.ndarray, ms: float = 5) -> np.ndarray:
    n = int(ms / 1000 * RATE)
    x[-n:] *= np.linspace(1, 0, n)
    x[:n] *= np.linspace(0, 1, n)
    return x


def click(seconds: float, seed: int, pitch: float) -> np.ndarray:
    d = t(seconds)
    tick = band(noise(seconds, seed), 2500 * pitch, min(9000 * pitch, 20000)) * np.exp(-d * 120)
    tick2 = np.roll(band(noise(seconds, seed + 1), 1500 * pitch, 6000 * pitch) * np.exp(-d * 160), int(0.025 * RATE)) * 0.6
    ring = np.sin(2 * np.pi * 2300 * pitch * d) * np.exp(-d * 45) * 0.25
    return fade(norm(tick + tick2 + ring, 0.7))


def sizzle(seconds: float, seed: int, pitch: float) -> np.ndarray:
    d = t(seconds)
    rng = np.random.default_rng(seed)
    hiss = band(noise(seconds, seed + 1), 3000 * pitch, min(12000 * pitch, 20000)) * (0.25 + 0.35 * d / seconds)
    pops = np.zeros_like(d)
    for at in rng.uniform(0, seconds, int(seconds * 45)):
        i = int(at * RATE)
        n = min(len(d) - i, int(0.012 * RATE))
        pops[i:i + n] += rng.uniform(0.3, 1.0) * np.exp(-np.arange(n) / (0.002 * RATE)) * rng.choice([-1, 1])
    pops = band(pops, 800, 9000)
    flutter = 1 + 0.3 * np.sin(2 * np.pi * 11 * d)
    return fade(norm((hiss + pops * 0.8) * flutter, 0.6), 30)


def boom(seconds: float, seed: int, pitch: float) -> np.ndarray:
    d = t(seconds)
    crack = band(noise(seconds, seed), 1500, 10000) * np.exp(-d * 60)
    body = band(noise(seconds, seed + 1), 60 * pitch, 1200 * pitch) * np.exp(-d * 6)
    thump = np.sin(2 * np.pi * (55 + 60 * np.exp(-d * 25)) * pitch * d) * np.exp(-d * 9)
    tail = band(noise(seconds, seed + 2), 40, 400) * np.exp(-d * 2.2) * 0.5
    x = np.tanh(2.2 * norm(crack * 0.9 + body * 0.8 + thump * 1.2 + tail, 1.0))  # soft clip for weight
    return fade(norm(x, 0.95), 40)


def pew(seconds: float, seed: int, pitch: float) -> np.ndarray:
    d = t(seconds)
    f = (1800 * np.exp(-d * 9 * 0.32 / seconds) + 180) * pitch
    tone = np.tanh(3 * np.sin(2 * np.pi * np.cumsum(f) / RATE)) * np.exp(-d * 9 * 0.32 / seconds)
    sparkle = band(noise(seconds, seed), 5000, 12000) * np.exp(-d * 40) * 0.3
    return fade(norm(tone + sparkle, 0.8))


def swish(seconds: float, seed: int, pitch: float) -> np.ndarray:
    d = t(seconds)
    swell = np.sin(np.pi * d / seconds) ** 3
    air = band(noise(seconds, seed), 700 * pitch, 5000 * pitch) * swell
    return fade(norm(air, 0.6))


def toot(seconds: float, seed: int, pitch: float) -> np.ndarray:
    d = t(seconds)
    f = 233 * pitch * (1 + 0.012 * np.sin(2 * np.pi * 5.5 * d))  # B-flat, with vibrato
    phase = np.cumsum(f) / RATE
    brass = sum(np.sin(2 * np.pi * n * phase) / n ** 0.7 for n in range(1, 9))
    swell = np.minimum(d / 0.06, 1) * np.exp(-np.maximum(d - seconds * 0.6, 0) * 12)
    return fade(norm(band(np.tanh(1.5 * brass) * swell, None, 3000), 0.7))


RECIPES = {"click": (click, 0.18), "sizzle": (sizzle, 1.5), "boom": (boom, 2.2), "pew": (pew, 0.32), "swish": (swish, 0.25), "toot": (toot, 0.7)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("recipe", choices=sorted(RECIPES))
    ap.add_argument("out", type=Path)
    ap.add_argument("--seconds", type=float, help="length; each recipe has a sensible default")
    ap.add_argument("--seed", type=int, default=1, help="a different seed is a different take of the same sound")
    ap.add_argument("--pitch", type=float, default=1.0, help="above 1 is higher and smaller, below 1 deeper and bigger")
    a = ap.parse_args()
    make, default = RECIPES[a.recipe]
    x = make(a.seconds or default, a.seed, a.pitch)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(a.out, RATE, (x * 32767).astype(np.int16))
    print(f"{a.out} {len(x) / RATE:.2f} s")


if __name__ == "__main__":
    main()
