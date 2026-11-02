"""The whole video a little faster: frames are dropped at the same frame rate, the voice keeps its pitch."""
from __future__ import annotations

import tempfile
from pathlib import Path

from .codec import encode
from .ffmpeg import ensure_file
from .graph import graph_args
from .probe import probe


def speed_up(src, rate: float, out) -> Path:
    """Writes `out`: `src` played `rate` times faster, picture and sound together, H.264 yuv420p + AAC."""
    src, out = ensure_file(src), Path(out)
    info = probe(src)
    parts, post = [], []
    if info["has_video"]:
        fps = ",fps={:.3f}".format(info["fps"]) if info["fps"] else ""
        parts.append("[0:v]setpts=PTS/{r:.4f}{f}[vout]".format(r=rate, f=fps))
        post += ["-map", "[vout]"]
    if info["has_audio"]:
        parts.append("[0:a]atempo={r:.4f}[aout]".format(r=rate))
        post += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    post += ["-movflags", "+faststart"]
    kbps = min(max(info["video_kbps"] or 8000, 2000), 50000)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aiediting-") as tmp:
        encode(["-i", src] + graph_args(";\n".join(parts), Path(tmp)), post, out, kbps=kbps, video=info["has_video"])
    return out
