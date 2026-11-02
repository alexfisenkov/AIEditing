"""The main storyline of a Final Cut timeline as spans of its source, retiming included.

Only clips of one source are read; a gap, a transition or a title on the storyline keeps nothing of the source.
A clip of another kind (a compound, a multicam) cannot be told in source time: that is an error, not a guess.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Tuple

Span = Tuple[float, float]
CLIPS = {"asset-clip", "clip", "video"}
NOTHING = {"gap", "transition", "title", "audio"}


class TimelineError(ValueError):
    pass


def t(value) -> Fraction:
    return Fraction(str(value or "0s").rstrip("s"))


def _map(clip, at: Fraction) -> Fraction:
    """Clip time → media time through its timeMap, point by point."""
    points = [(t(p.get("time")), t(p.get("value"))) for p in clip.findall("timeMap/timept")]
    if len(points) < 2:
        return at
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if at <= x1 or (x1, y1) == points[-1]:
            return y0 + (at - x0) * (y1 - y0) / (x1 - x0) if x1 != x0 else y0
    return at


def _rate(clip) -> float:
    points = [(t(p.get("time")), t(p.get("value"))) for p in clip.findall("timeMap/timept")]
    return float((points[-1][1] - points[0][1]) / (points[-1][0] - points[0][0])) if len(points) > 1 and points[-1][0] != points[0][0] else 1.0


def _ref(clip) -> str:
    video = clip if clip.tag == "asset-clip" else clip.find("video")
    return "" if video is None else str(video.get("ref", ""))


def read(path) -> Dict:
    """{kept: [(a, b)], rate, total}: source seconds kept, the retime of the longest clip, the source's length."""
    path = Path(path)
    root = ET.parse(path / "Info.fcpxml" if path.is_dir() else path).getroot()
    spine = root.find(".//project/sequence/spine")
    if spine is None:
        raise TimelineError("В таймлайне нет основной дорожки: {}".format(path))
    other = sorted({c.tag for c in spine} - CLIPS - NOTHING)
    if other:
        raise TimelineError("На дорожке есть элементы, которые не свести ко времени исходника: {}".format(", ".join(other)))
    clips = [c for c in spine if c.tag in CLIPS]
    if not clips:
        raise TimelineError("На дорожке нет клипов: {}".format(path))
    length: Dict[str, Fraction] = {}
    for c in clips:
        length[_ref(c)] = length.get(_ref(c), Fraction(0)) + t(c.get("duration"))
    main = max(length, key=lambda k: length[k])
    asset = root.find(".//asset[@id='{}']".format(main))
    origin, kept, rate, longest = t(asset.get("start")) if asset is not None else Fraction(0), [], 1.0, Fraction(-1)
    for c in clips:
        if _ref(c) != main:
            continue
        start, dur = t(c.get("start")), t(c.get("duration"))
        kept.append((float(_map(c, start) - origin), float(_map(c, start + dur) - origin)))
        if dur > longest:
            rate, longest = _rate(c), dur
    total = float(t(asset.get("duration"))) if asset is not None and t(asset.get("duration")) > 0 else max(b for _, b in kept)
    return {"kept": kept, "rate": rate, "total": total}
