"""Keep only the given spans and splice them in one ffmpeg pass.

Each span is trimmed by timestamps (works for variable frame rate too) and the pieces go through
`concat`, which starts every piece of picture and sound together, so drift cannot pile up.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Sequence, Tuple

from .codec import encode
from .ffmpeg import MediaError, ensure_file
from .graph import graph_args
from .probe import probe


def _graph(spans: Sequence[Tuple[float, float]], video: bool, audio: bool) -> str:
    parts, pads = [], []
    for i, (a, b) in enumerate(spans):
        if video:
            parts.append("[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}]".format(a=a, b=b, i=i))
            pads.append("[v{}]".format(i))
        if audio:
            parts.append("[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[a{i}]".format(a=a, b=b, i=i))
            pads.append("[a{}]".format(i))
    parts.append("{}concat=n={}:v={}:a={}{}{}".format(
        "".join(pads), len(spans), int(video), int(audio),
        "[vout]" if video else "", "[aout]" if audio else ""))
    return ";\n".join(parts)


def cut_spans(src, spans: List[Tuple[float, float]], out) -> Path:
    """Writes `out` with only `spans` of `src` (seconds), H.264 yuv420p + AAC, one encode."""
    src, out = ensure_file(src), Path(out)
    spans = [(float(a), float(b)) for a, b in spans if float(b) > float(a)]
    if not spans:
        raise MediaError("Нечего склеивать: список отрезков пуст.")
    info = probe(src)
    video, audio = info["has_video"], info["has_audio"]
    maps = (["-map", "[vout]"] if video else []) + (["-map", "[aout]"] if audio else [])
    post = maps + (["-c:a", "aac", "-b:a", "192k"] if audio else [])
    post += ["-movflags", "+faststart"]
    kbps = min(max(info["video_kbps"] or 8000, 2000), 50000)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aiediting-") as tmp:
        pre = ["-i", src] + graph_args(_graph(spans, video, audio), Path(tmp))
        encode(pre, post, out, kbps=kbps, video=video)
    return out
