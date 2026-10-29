"""File passport via ffprobe: duration, size, fps, rotation, streams."""
from __future__ import annotations

import json
from typing import Any, Dict

from .ffmpeg import MediaError, ensure_file, run


def _fps(rate: str) -> float:
    try:
        num, _, den = rate.partition("/")
        return float(num) / float(den or 1) if float(den or 1) else 0.0
    except ValueError:
        return 0.0


def _rotation(stream: Dict[str, Any]) -> int:
    rot = stream.get("tags", {}).get("rotate")
    for side in stream.get("side_data_list", []) or []:
        if "rotation" in side:
            rot = side["rotation"]
    try:
        return int(float(rot or 0)) % 360
    except ValueError:
        return 0


def probe(path) -> Dict[str, Any]:
    """Probe = {duration, width, height, fps, rotation, has_audio, has_video, video_kbps, audio_duration}."""
    path = ensure_file(path)
    out = run(["-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
              what="ffprobe").stdout
    try:
        data = json.loads(out)
    except ValueError:
        raise MediaError("ffprobe вернул нечитаемый ответ для {}".format(path))
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"
                  and not s.get("disposition", {}).get("attached_pic")), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(data.get("format", {}).get("duration") or 0.0)
    kbps = int(float((video or {}).get("bit_rate") or 0) / 1000)
    return {
        "duration": duration,
        "width": int((video or {}).get("width") or 0),
        "height": int((video or {}).get("height") or 0),
        "fps": _fps((video or {}).get("avg_frame_rate") or "0/1"),
        "rotation": _rotation(video or {}),
        "has_audio": audio is not None,
        "has_video": video is not None,
        "video_kbps": kbps,
        "audio_duration": float((audio or {}).get("duration") or duration if audio else 0.0),
    }
