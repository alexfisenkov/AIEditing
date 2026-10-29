"""A/V drift of a finished file: how far picture and sound disagree at the start and at the end."""
from __future__ import annotations

import json

from .ffmpeg import ensure_file, run


def _stream_bounds(path, selector: str):
    out = run(["-v", "error", "-select_streams", selector, "-show_entries",
               "packet=pts_time,duration_time", "-of", "json", path], what="ffprobe").stdout
    packets = [p for p in json.loads(out).get("packets", []) if p.get("pts_time") not in (None, "N/A")]
    if not packets:
        return None
    starts = [float(p["pts_time"]) for p in packets]
    ends = [float(p["pts_time"]) + float(p.get("duration_time") or 0) for p in packets]
    return min(starts), max(ends)


def drift_ms(path) -> float:
    """Largest of |start(video) − start(audio)| and |end(video) − end(audio)|, in milliseconds.

    A file with only one kind of stream has no drift (0.0).
    """
    path = ensure_file(path)
    video, audio = _stream_bounds(path, "v:0"), _stream_bounds(path, "a:0")
    if video is None or audio is None:
        return 0.0
    return round(max(abs(video[0] - audio[0]), abs(video[1] - audio[1])) * 1000.0, 1)
