"""Is the speaker's face whole inside the speaker's window on a rendered frame.

The window is what the presenter reported (src/kit/speakerBox.ts): a box with a corner radius, a circle when the radius is
half the box. The face is found by YuNet in the part of the frame the window covers. Pure geometry here and one detector
call, so the rules are tested without a render.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from . import face
from .common import ToolError

Box = Tuple[float, float, float, float]  # x, y, w, h in pixels of the frame
Window = Tuple[float, float, float, float, float, float]  # x, y, w, h, corner radius, how visible

NO_FACE = "НЕТ ЛИЦА В РАМКЕ"
CUT = "ЛИЦО СРЕЗАНО КРАЕМ РАМКИ"
# The detector sees only what the window shows, so a face cut by the edge comes back as its visible part, wholly inside.
# What gives it away is where that part ends: on the edge. A whole face keeps a margin of forehead, cheeks and chin.
# Measured on real frames: a cut face -0.011 and -0.006 of the window's smaller side, whole faces +0.048 to +0.111.
CLEAR = 0.01      # the face ellipse keeps at least this share of the window's smaller side from its edge
SHOWN = 0.5       # a window fainter than this is not on the screen: nothing to judge
SMALLEST = 40     # pixels: a window narrower than this is too small for the detector
POINTS = 72       # points along the face ellipse
SCORE = 0.6       # the detector's threshold, as face.py builds the track with


def is_circle(win: Window) -> bool:
    return win[4] >= min(win[2], win[3]) / 2 - 1


def inside(win: Window, px: float, py: float) -> bool:
    x, y, w, h = win[:4]
    if is_circle(win):
        r = min(w, h) / 2
        return math.hypot(px - (x + w / 2), py - (y + h / 2)) <= r
    return x <= px <= x + w and y <= py <= y + h


def clearance(win: Window, box: Box) -> float:
    """The smallest distance from the ellipse inscribed in a face box to the window's edge, as a share of the window's
    smaller side; negative when the ellipse goes beyond it."""
    x, y, w, h = win[:4]
    cx, cy, a, b = box[0] + box[2] / 2, box[1] + box[3] / 2, box[2] / 2, box[3] / 2
    worst = math.inf
    for k in range(POINTS):
        t = 2 * math.pi * k / POINTS
        px, py = cx + a * math.cos(t), cy + b * math.sin(t)
        if is_circle(win):
            gap = min(w, h) / 2 - math.hypot(px - (x + w / 2), py - (y + h / 2))
        else:
            gap = min(px - x, x + w - px, py - y, y + h - py)
        worst = min(worst, gap)
    return worst / min(w, h)


def judgeable(win: Optional[Sequence[float]]) -> bool:
    return bool(win) and len(win) >= 6 and win[5] >= SHOWN and min(win[2], win[3]) >= SMALLEST


def judge(faces: Sequence[Box], win: Window) -> Optional[str]:
    """None when a face is whole inside the window; otherwise what is wrong. `faces` are in frame pixels."""
    centred = [f for f in faces if inside(win, f[0] + f[2] / 2, f[1] + f[3] / 2)]
    if not centred:
        return NO_FACE
    best = max(centred, key=lambda f: f[2] * f[3])
    return None if clearance(win, best) >= CLEAR else CUT


def ready() -> Optional[str]:
    """None when the detector can run; otherwise the reason it cannot."""
    try:
        import cv2  # noqa: F401
    except ImportError:
        return "нет OpenCV (cv2) в этом Python"
    if not face.model_path().is_file():
        return "нет модели лица {}".format(face.model_path())
    return None


def detector() -> Tuple[Optional["Detector"], Optional[str]]:
    """(the detector, None) or (None, the reason there is none). Loading the model can fail where its path has non-ASCII letters
    on Windows: that is a reason to say, not a traceback."""
    reason = ready()
    if reason:
        return None, reason
    try:
        return Detector(), None
    except Exception as exc:  # OpenCV raises its own error types
        return None, "модель лица не загрузилась ({})".format((str(exc).splitlines() or [type(exc).__name__])[0][:80])


class Detector:
    """YuNet over the part of a frame a window covers; the faces come back in frame pixels."""

    def __init__(self) -> None:
        import cv2

        self.cv2 = cv2
        self.net = cv2.FaceDetectorYN_create(str(face.model_path()), "", (320, 320), SCORE)

    def faces(self, image_path, win: Window) -> List[Box]:
        import numpy as np  # cv2.imread cannot open a path with non-ASCII letters on Windows: read the bytes, decode them

        try:
            image = self.cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), self.cv2.IMREAD_COLOR)
        except (OSError, ValueError):
            image = None
        if image is None:
            raise ToolError("Кадр проверки лица не читается: {}".format(image_path))
        height, width = image.shape[:2]
        x0, y0 = max(0, int(math.floor(win[0]))), max(0, int(math.floor(win[1])))
        x1, y1 = min(width, int(math.ceil(win[0] + win[2]))), min(height, int(math.ceil(win[1] + win[3])))
        if x1 - x0 < SMALLEST or y1 - y0 < SMALLEST:
            return []
        crop = image[y0:y1, x0:x1]
        self.net.setInputSize((x1 - x0, y1 - y0))
        _, found = self.net.detect(crop)
        if found is None:
            return []
        return [(float(f[0]) + x0, float(f[1]) + y0, float(f[2]), float(f[3])) for f in found if f[2] > 0 and f[3] > 0]
