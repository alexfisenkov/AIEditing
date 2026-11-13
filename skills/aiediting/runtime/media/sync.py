"""Lining up recordings of the same scene by their sound, and the loudness curve that does it.

The curve (`envelope`) is the mean level of the sound every 5 ms. Two recordings of one voice rise and fall together
whatever their microphones, so the shift at which their curves agree best is how far apart they started.
Plain Python, no numpy: a coarse search over the whole allowed shift, then a fine one around the best.
"""
from __future__ import annotations

import array
import math
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from .ffmpeg import MediaError, ensure_file, run
from .probe import probe

RATE = 200          # points of the curve per second: 5 ms, well under a frame
SAMPLE_RATE = 4000  # the sound is read this fine: the voice's level lives below 2 kHz
SPAN = 300.0        # s of each recording compared: enough to be sure, quick to read
MAX_SHIFT = 60.0    # s: recorders started further apart than this are not searched
COARSE = 10         # the coarse search reads every 10th point: 50 ms
AGREE = 0.3         # the curves must agree at least this well, or the shift is a guess


def envelope(path, rate: int = RATE, seconds: Optional[float] = None) -> List[float]:
    """Mean level (0…1) of the first audio stream every 1/rate s; `seconds` reads only the start."""
    path = ensure_file(path)
    if not probe(path)["has_audio"]:
        raise MediaError("В файле нет звука, свести его по звуку нельзя: {}".format(path))
    with tempfile.TemporaryDirectory(prefix="aiediting-") as tmp:
        raw = Path(tmp) / "level.raw"
        limit = ["-t", "{:.3f}".format(seconds)] if seconds else []
        run(["-i", path] + limit + ["-map", "0:a:0", "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
                                    "-f", "s16le", "-c:a", "pcm_s16le", raw])
        samples = array.array("h")
        samples.frombytes(raw.read_bytes())
    step = SAMPLE_RATE // rate
    return [sum(map(abs, samples[i:i + step])) / (32768.0 * step) for i in range(0, len(samples) - step + 1, step)]


def quietest(env: Sequence[float], a: float, b: float, rate: int = RATE) -> float:
    """The middle of the quietest point of the curve between a and b seconds (a when the window is empty)."""
    i, j = max(0, int(round(a * rate))), min(len(env), int(round(b * rate)) + 1)
    if j <= i:
        return a
    k = min(range(i, j), key=lambda n: (env[n], abs(n - (i + j) / 2.0)))
    return (k + 0.5) / rate


def _shape(env: Sequence[float]) -> List[float]:
    """Levels on a log scale: a quiet microphone and a loud one draw the same curve."""
    return [math.log10(1e-4 + e) for e in env]


def _pool(x: Sequence[float], n: int) -> List[float]:
    return [sum(x[i:i + n]) / n for i in range(0, len(x) - n + 1, n)]


def _agreement(x: Sequence[float], y: Sequence[float], lag: int, least: int) -> float:
    """Correlation of x[i + lag] with y[i] over their overlap; −1 when they overlap less than `least` points."""
    lo, hi = max(0, -lag), min(len(y), len(x) - lag)
    n = hi - lo
    if n < least:
        return -1.0
    xs, ys = x[lo + lag:hi + lag], y[lo:hi]
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum(p * q for p, q in zip(xs, ys)) - n * mx * my
    sxx = sum(p * p for p in xs) - n * mx * mx
    syy = sum(q * q for q in ys) - n * my * my
    return sxy / math.sqrt(sxx * syy) if sxx > 1e-12 and syy > 1e-12 else -1.0


def _best(x, y, lags, least) -> Tuple[int, float]:
    return max(((lag, _agreement(x, y, lag, least)) for lag in lags), key=lambda p: p[1])


def offset(ref, other, span: float = SPAN, within: float = MAX_SHIFT) -> float:
    """Seconds `other` started after `ref` (negative: before): a sound at t s of `ref` is at t − offset s of `other`."""
    x = _shape(envelope(ref, seconds=span + within))
    y = _shape(envelope(other, seconds=span + within))
    for name, curve in ((ref, x), (other, y)):
        if max(curve) - min(curve) < 0.5:
            raise MediaError("В записи {} не слышно звука, по которому её можно свести с остальными".format(Path(name).name))
    cx, cy = _pool(x, COARSE), _pool(y, COARSE)
    reach = int(within * RATE / COARSE)
    least = max(5, min(len(cx), len(cy)) // 4)
    lag, score = _best(cx, cy, range(-reach, reach + 1), least)
    lag, score = _best(x, y, range(lag * COARSE - 2 * COARSE, lag * COARSE + 2 * COARSE + 1), least * COARSE)
    if score < AGREE:
        raise MediaError("Записи {} и {} не удалось свести по звуку: общего звука не найдено (сходство {:.2f})".format(
            Path(ref).name, Path(other).name, score))
    return round(lag / float(RATE), 3)
