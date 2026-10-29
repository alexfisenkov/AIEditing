"""Snapshots of a source video: n frames from the middles of n equal parts."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import List, Optional

from ..media.ffmpeg import MediaError, ensure_file, run
from ..media.probe import probe

_TIME = re.compile(r"_t(\d+(?:\.\d+)?)s\.png$")


def frame_time(path) -> Optional[float]:
    """Seconds into the source for a file made by `frames`, None for any other picture."""
    m = _TIME.search(Path(path).name)
    return float(m.group(1)) if m else None


def frames(src, n: int, outdir=None) -> List[Path]:
    """PNG snapshots (rotation applied, full size). Default folder: a fresh temporary one."""
    src = ensure_file(src)
    info = probe(src)
    if not info["has_video"]:
        raise MediaError("В файле нет видео: {}".format(src))
    n = max(1, int(n))
    out = Path(outdir) if outdir else Path(tempfile.mkdtemp(prefix="aiediting-frames-"))
    out.mkdir(parents=True, exist_ok=True)
    step = info["duration"] / n
    shots = []
    for i in range(n):
        t = step * (i + 0.5)
        path = out / "frame_{:03d}_t{:.3f}s.png".format(i + 1, t)
        run(["-ss", "{:.3f}".format(t), "-i", src, "-frames:v", "1", "-an", path])
        if not path.is_file():
            raise MediaError("Не удалось снять кадр {:.1f} с из {}".format(t, src))
        shots.append(path)
    return shots
