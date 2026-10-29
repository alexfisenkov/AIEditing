"""Following a moving area: the look of the area at `start` is searched for on every next frame."""
from __future__ import annotations

import subprocess
from typing import Dict, List

from ..media.ffmpeg import ensure_file, tool
from ..media.probe import probe
from .errors import LookError, need

WORK_WIDTH = 480  # frames are compared at this width
STEP_FPS = 5.0  # positions per second; the blur moves linearly between them


def _gray_frames(np, src, start, end, size):
    w, h = size
    cmd = [tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error",
           "-ss", "{:.3f}".format(start), "-i", str(src), "-t", "{:.3f}".format(max(0.04, end - start)),
           "-vf", "fps={},scale={}:{},format=gray".format(STEP_FPS, w, h), "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    count = len(raw) // (w * h)
    if not count:
        raise LookError("Не удалось прочитать кадры {:.1f}–{:.1f} с из {}".format(start, end, src))
    return np.frombuffer(raw[:count * w * h], dtype=np.uint8).reshape(count, h, w).astype(np.float32)


def _best_shift(np, frame, template, x, y, reach):
    th, tw = template.shape
    h, w = frame.shape
    x0, y0 = max(0, x - reach), max(0, y - reach)
    x1, y1 = min(w - tw, x + reach), min(h - th, y + reach)
    area = frame[y0:y1 + th, x0:x1 + tw]
    windows = np.lib.stride_tricks.sliding_window_view(area, (th, tw))
    cost = ((windows - template) ** 2).mean(axis=(2, 3))
    j, i = np.unravel_index(int(np.argmin(cost)), cost.shape)
    return x0 + int(i), y0 + int(j)


def track_region(src, region: Dict) -> List[Dict]:
    """Path [{"t","x","y","w","h"}] of the area's top-left corner, in source pixels, STEP_FPS a second."""
    np = need("numpy", "блюр движущейся области")
    src = ensure_file(src)
    info = probe(src)
    scale = min(1.0, WORK_WIDTH / float(info["width"]))
    size = (int(info["width"] * scale) // 2 * 2, int(info["height"] * scale) // 2 * 2)
    start, end = float(region["start"]), float(region["end"])
    shots = _gray_frames(np, src, start, end, size)
    x, y = int(region["x"] * scale), int(region["y"] * scale)
    tw = max(4, min(int(region["w"] * scale), size[0] - x))
    th = max(4, min(int(region["h"] * scale), size[1] - y))
    template = shots[0][y:y + th, x:x + tw]
    reach = max(8, int(0.12 * size[0]))
    path = []
    for k, frame in enumerate(shots):
        if k:
            x, y = _best_shift(np, frame, template, x, y, reach)
        path.append({"t": round(start + k / STEP_FPS, 3), "x": round(x / scale, 1),
                     "y": round(y / scale, 1), "w": region["w"], "h": region["h"]})
    return path
