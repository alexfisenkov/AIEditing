"""What code can tell about a photo or video without looking: type, date, orientation, length.

Dates come from EXIF (Pillow, when installed) or the container tags (ffprobe); none is guessed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional, Tuple

PHOTO = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff", ".bmp", ".gif", ".dng"}
VIDEO = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".mts", ".m2ts", ".webm", ".3gp", ".mpg", ".mpeg"}
_DATE = re.compile(r"^(\d{4})[-:](\d{2})[-:](\d{2})")
_TURNED = {5, 6, 7, 8}  # EXIF orientations stored sideways


def is_media(path: Path) -> bool:
    return path.suffix.lower() in PHOTO | VIDEO


def kind_of(path: Path) -> str:
    return "видео" if path.suffix.lower() in VIDEO else "фото"


def _date(text) -> Optional[str]:
    found = _DATE.match(str(text or "").strip())
    if not found or found.group(1) == "0000":
        return None
    return "{}-{}-{}".format(*found.groups())


def orient(width: int, height: int) -> Optional[str]:
    if not width or not height:
        return None
    if abs(width - height) <= 0.02 * max(width, height):
        return "кв"
    return "гор" if width > height else "верт"


def _exif(path: Path) -> Optional[Tuple[int, int, Optional[str]]]:
    """(width, height as shown, date) from Pillow; None when Pillow is missing or cannot read the file."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(str(path)) as im:
            width, height = im.size
            exif = im.getexif()
            taken = exif.get_ifd(0x8769).get(36867) or exif.get(306)
            if exif.get(274) in _TURNED:
                width, height = height, width
            return width, height, _date(taken)
    except Exception:  # an unreadable or exotic image: ffprobe is asked instead
        return None


def _ffprobe(path: Path) -> dict:
    from ..media.ffmpeg import run

    out = run(["-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
              what="ffprobe", check=False).stdout
    try:
        return json.loads(out or "{}")
    except ValueError:
        return {}


def _video(path: Path) -> Tuple[int, int, Optional[str], Optional[float]]:
    from ..media.probe import _rotation

    data = _ffprobe(path)
    streams = data.get("streams", [])
    stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    width, height = int(stream.get("width") or 0), int(stream.get("height") or 0)
    if _rotation(stream) in (90, 270):
        width, height = height, width
    tags = dict(stream.get("tags") or {}, **(data.get("format", {}).get("tags") or {}))
    taken = tags.get("com.apple.quicktime.creationdate") or tags.get("creation_time")
    try:
        dur = round(float(data.get("format", {}).get("duration")), 2)
    except (TypeError, ValueError):
        dur = None
    return width, height, _date(taken), dur


def measure(path: Path) -> dict:
    """{"type", "date", "orient", "dur"} of one file; unknown values are None."""
    path = Path(path)
    if kind_of(path) == "видео":
        width, height, date, dur = _video(path)
    else:
        found = _exif(path)
        width, height, date, dur = found + (None,) if found else _video(path)[:3] + (None,)
    return {"type": kind_of(path), "date": date, "orient": orient(width, height), "dur": dur}
