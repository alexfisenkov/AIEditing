"""Finding a round camera window (OBS-style circle) on a frame by its outline.

A real window has an unbroken edge along a whole circle and calm pixels just inside and outside it;
text and icons give edges too, but never a closed ring with quiet sides.
"""
from __future__ import annotations

import math
from typing import Dict, Optional

from .errors import need

WORK_WIDTH = 320  # frames are analysed at this width
EDGE = 30  # brightness step (0..255) that counts as an edge
MIN_SCORE = 0.65


def _edges(np, gray):
    e = np.zeros(gray.shape, dtype=bool)
    e[:, 1:] |= np.abs(np.diff(gray, axis=1)) > EDGE
    e[1:, :] |= np.abs(np.diff(gray, axis=0)) > EDGE
    grown = e.copy()  # tolerate a pixel of error in position
    grown[1:, :] |= e[:-1, :]
    grown[:-1, :] |= e[1:, :]
    grown[:, 1:] |= e[:, :-1]
    grown[:, :-1] |= e[:, 1:]
    return grown.astype(np.float32)


def _ring(np, padded, pad, shape, r, samples=48):
    h, w = shape
    acc = np.zeros(shape, dtype=np.float32)
    for k in range(samples):
        a = 2 * math.pi * k / samples
        dy, dx = int(round(r * math.sin(a))), int(round(r * math.cos(a)))
        acc += padded[pad + dy:pad + dy + h, pad + dx:pad + dx + w]
    return acc / samples


def find_circle(path) -> Optional[Dict]:
    """{"x","y","w","h","score"} of the best round window in pixels of the frame, or None."""
    np, image = need("numpy", "раскладка кадра"), need("PIL.Image", "раскладка кадра")
    with image.open(path) as img:
        full_w, full_h = img.size
        scale = WORK_WIDTH / float(full_w)
        small = img.convert("L").resize((WORK_WIDTH, max(1, int(full_h * scale))), image.BOX)
    gray = np.asarray(small, dtype=np.int16)
    edges = _edges(np, gray)
    h, w = edges.shape
    pad = int(0.32 * min(h, w)) + 6
    padded = np.pad(edges, pad)
    ys, xs = np.mgrid[0:h, 0:w]
    best = None
    for r in range(max(6, int(0.06 * min(h, w))), int(0.30 * min(h, w)) + 1, 2):
        score = _ring(np, padded, pad, (h, w), r) - np.minimum(
            _ring(np, padded, pad, (h, w), r - 3), _ring(np, padded, pad, (h, w), r + 3))
        inside = (xs - r >= -2) & (ys - r >= -2) & (xs + r < w + 2) & (ys + r < h + 2)
        score = np.where(inside, score, -1.0)
        i = int(np.argmax(score))
        if score.flat[i] >= MIN_SCORE:  # the largest qualifying ring wins: a head outline sits inside
            best = (float(score.flat[i]), r, i % w, i // w)
    if best is None:
        return None
    s, r, cx, cy = best
    return {"x": int((cx - r) / scale), "y": int((cy - r) / scale),
            "w": int(2 * r / scale), "h": int(2 * r / scale), "score": round(s, 3)}
