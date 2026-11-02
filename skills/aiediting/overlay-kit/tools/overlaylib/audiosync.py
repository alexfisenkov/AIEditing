"""Where the speech sits in a finished file compared with the source: cross-correlation of windows (needs numpy)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Tuple

from .common import ToolError

SR = 4000  # 0.25 ms per sample, refined below to a fraction of that
QUIET = 0.004  # windows quieter than this (share of full scale, rms) carry no speech to match


def _np():
    try:
        import numpy
        return numpy
    except ImportError:
        raise ToolError("Для этой команды нужен numpy (он уже есть в окружении AIEditing: ~/.aiediting/venv).")


def pcm(path: Path):
    np = _np()
    done = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if done.returncode != 0 or not done.stdout:
        raise ToolError("Не читается звук файла {}: {}".format(path, done.stderr.decode("utf-8", "replace").strip()[-200:]))
    return np.frombuffer(done.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def window_starts(total: float) -> List[float]:
    """Windows spread over the whole file: short files get three, long ones about one per minute."""
    win = min(8.0, total * 0.3)
    n = max(3, min(12, int(total // 60) + 3))
    span = max(0.0, total - win - 4.0)
    return [round(2.0 + span * i / max(1, n - 1), 2) for i in range(n)] if span > 0 else [0.0]


def measure(ref, test) -> List[Tuple[float, float]]:
    """[(window start, lag in seconds)] where `test` is later (+) or earlier (-) than `ref`."""
    np = _np()
    total = len(ref) / SR
    win = int(min(8.0, total * 0.3) * SR)
    out = []
    for start in window_starts(total):
        a = int(start * SR)
        w = ref[a: a + win]
        if len(w) < win or float(np.sqrt(np.mean(w * w))) < QUIET:
            continue
        lo = max(0, a - SR)
        seg = test[lo: a + win + SR]
        if len(seg) < len(w):
            continue
        n = 1 << (len(seg) + len(w) - 1).bit_length()
        corr = np.fft.irfft(np.fft.rfft(seg, n) * np.conj(np.fft.rfft(w, n)), n)[: len(seg) - len(w) + 1]
        k = int(np.argmax(corr))
        frac = 0.0
        if 0 < k < len(corr) - 1:  # parabola through the peak: sub-sample position
            y0, y1, y2 = float(corr[k - 1]), float(corr[k]), float(corr[k + 1])
            denom = y0 - 2 * y1 + y2
            frac = 0.5 * (y0 - y2) / denom if denom else 0.0
        out.append((start, (lo + k + frac - a) / SR))
    return out


def median(values: List[float]) -> float:
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2
