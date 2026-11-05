"""The finished file in the format the profile asks for: `params.delivery`, one last encode of the whole video.

{"codec": "hevc", "kbps": 1700, "audio_kbps": 128} gives what a person's Compressor preset gives: H.265 Main,
8 bits 4:2:0, a player-friendly hvc1 tag, Rec. 709, AAC 48 kHz stereo. libx265 comes first: at such a low bitrate
VideoToolbox through ffmpeg overshoots the rate and loses the small text on a screen.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from .ffmpeg import MediaError, encoders, run
from .probe import probe

COLOR = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
# ffmpeg 9 lets the output options above reach only the matrix: the frames carry the rest, with no change to a pixel
FRAMES = "format=yuv420p,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709"


def _chain(available=None) -> List[str]:
    forced = os.environ.get("AIEDITING_VCODEC")
    if forced:
        return [forced]
    available = encoders() if available is None else available
    return [c for c in ("libx265", "hevc_videotoolbox") if c in available]


def _args(name: str, kbps: int) -> List[str]:
    args = ["-c:v", name, "-b:v", "{}k".format(kbps), "-tag:v", "hvc1"]
    if name == "libx265":
        return args + ["-preset", "medium", "-x265-params", "log-level=error"]
    if name == "hevc_videotoolbox":
        return args + ["-profile:v", "main", "-allow_sw", "1"]
    return args


def deliver(src, out, spec: Optional[Dict] = None) -> str:
    """Encodes `src` into `out` by `spec` (see above); raises MediaError when no encoder can do it."""
    spec, info = dict(spec or {}), probe(src)
    kbps, audio_kbps = int(spec.get("kbps", 1700)), int(spec.get("audio_kbps", 128))
    audio = ["-c:a", "aac", "-b:a", "{}k".format(audio_kbps), "-ar", "48000", "-ac", "2"] if info["has_audio"] else []
    errors = []
    for name in _chain():
        try:
            run(["-i", src, "-map", "0:v:0", "-map", "0:a:0?", "-vf", FRAMES] + COLOR + _args(name, kbps) +
                audio + ["-map_metadata", "-1", "-movflags", "+faststart", out])
            return str(out)
        except MediaError as exc:
            errors.append(str(exc))
    raise MediaError("Не удалось закодировать выпуск в H.265:\n" + ("\n".join(errors) or "в ffmpeg нет кодека H.265"))
