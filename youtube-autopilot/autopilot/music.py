"""Procedural horror background music — 100% copyright-free, numpy se generate hota hai.

Elements: low drone + heartbeat + tension pulses + wind noise.
Koi external music file nahi chahiye, koi copyright issue nahi.
"""
from __future__ import annotations

import numpy as np
import wave
from pathlib import Path

SR = 44100


def _t(total: float) -> np.ndarray:
    return np.arange(int(total * SR)) / SR


def _envelope(t: np.ndarray, attack: float = 1.0, release: float = 1.5) -> np.ndarray:
    a = int(attack * SR)
    r = int(release * SR)
    env = np.ones_like(t)
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if r > 0:
        env[-r:] = np.linspace(1, 0, r)
    return env


def _drone(t: np.ndarray) -> np.ndarray:
    # 55Hz + 82.5Hz (A1/E2) detuned sines, slow tremolo
    f1, f2 = 55.0, 82.5
    trem = 0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)
    a = 0.16 * trem * (np.sin(2 * np.pi * f1 * t) + 0.6 * np.sin(2 * np.pi * f2 * t + 0.5))
    # sub swell every 8s
    swell = 1.0 + 0.35 * np.sin(2 * np.pi * t / 16.0)
    return a * swell


def _heartbeat(t: np.ndarray, bpm: float = 52.0) -> np.ndarray:
    # lub-dub: 50Hz thump with fast decay, twice per beat
    beat = 60.0 / bpm
    out = np.zeros_like(t)
    n = int(t[-1] / beat) + 1
    thump = 0.0016 * np.exp(-np.linspace(0, 28, int(0.22 * SR))) * np.sin(
        2 * np.pi * 48 * np.linspace(0, 0.22, int(0.22 * SR)))
    for i in range(n):
        s = i * beat
        i0 = int(s * SR)
        if i0 + len(thump) < len(out):
            out[i0:i0 + len(thump)] += thump * 0.9
        i1 = i0 + int(0.42 * beat * SR)  # 'dub' 0.42 beat baad
        if i1 + len(thump) < len(out):
            out[i1:i1 + len(thump)] += thump * 0.55
    return out


def _tension(t: np.ndarray) -> np.ndarray:
    # rising tone every ~20s (creepy tension), quiet
    out = np.zeros_like(t)
    period = 21.0
    n = int(t[-1] / period) + 1
    for i in range(n):
        s = i * period
        dur = min(6.0, t[-1] - s)
        if dur <= 0:
            break
        tt = np.linspace(0, dur, int(dur * SR))
        f = 220 + 620 * (tt / dur) ** 1.6  # riser
        tone = 0.05 * (tt / dur) * np.sin(2 * np.pi * f * tt + 2 * np.pi * 30 * tt * tt * 0.5)
        i0 = int(s * SR)
        out[i0:i0 + len(tone)] += tone
    return out


def _wind(t: np.ndarray) -> np.ndarray:
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(len(t))
    # simple one-pole lowpass
    filt = np.empty_like(noise)
    alpha = 0.06
    acc = 0.0
    for i in range(len(noise)):
        acc += alpha * (noise[i] - acc)
        filt[i] = acc
    am = 0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t + 1.3)
    return 0.05 * filt * am


def make_music(duration: float, out_path: Path, cfg: dict | None = None) -> Path:
    """Duration seconds ki horror music WAV banakar save karo."""
    cfg = cfg or {}
    t = _t(duration)
    mix = np.zeros_like(t)
    if cfg.get("drone", True):
        mix += _drone(t)
    if cfg.get("heartbeat", True):
        mix += _heartbeat(t)
    if cfg.get("tension", True):
        mix += _tension(t)
    mix += _wind(t)
    mix *= _envelope(t)
    # normalize to -14 dBFS peak-ish
    peak = np.max(np.abs(mix)) or 1.0
    mix = mix / peak * 0.55
    stereo = np.stack([mix, mix], axis=1)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out_path
