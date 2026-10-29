"""Choosing the H.264 encoder: VideoToolbox on a Mac when present, libx264 everywhere else."""
from __future__ import annotations

import os
import sys
from typing import List, Optional

from .ffmpeg import MediaError, encoders, run


def codec_chain(platform: Optional[str] = None, available=None) -> List[str]:
    """Encoders to try in order. AIEDITING_VCODEC forces one encoder."""
    forced = os.environ.get("AIEDITING_VCODEC")
    if forced:
        return [forced]
    platform = platform or sys.platform
    available = encoders() if available is None else available
    chain = []
    if platform == "darwin" and "h264_videotoolbox" in available:
        chain.append("h264_videotoolbox")
    chain.append("libx264")
    return chain


def codec_args(name: str, kbps: int) -> List[str]:
    if name == "h264_videotoolbox":
        return ["-c:v", name, "-b:v", "{}k".format(kbps), "-allow_sw", "1"]
    if name == "libx264":
        return ["-c:v", name, "-preset", "veryfast", "-crf", "18"]
    return ["-c:v", name, "-b:v", "{}k".format(kbps)]


def encode(pre: List[str], post: List[str], out, kbps: int = 8000, video: bool = True) -> None:
    """Runs ffmpeg as `pre + codec + post + out`, falling back down the encoder chain.

    VideoToolbox can refuse a session (virtual machines, odd sizes); libx264 then takes over.
    """
    if not video:
        run(pre + post + [out])
        return
    errors = []
    for name in codec_chain():
        try:
            run(pre + codec_args(name, kbps) + ["-pix_fmt", "yuv420p"] + post + [out])
            return
        except MediaError as exc:
            errors.append(str(exc))
    raise MediaError("Не удалось закодировать видео ни одним кодеком:\n" + "\n".join(errors))
