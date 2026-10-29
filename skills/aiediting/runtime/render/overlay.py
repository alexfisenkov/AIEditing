"""overlay_png(): lay PNG pictures (plates, chapters, captions) and clips with alpha over a video.

Text is never drawn by ffmpeg (many builds lack drawtext): render.plate makes the pictures.
Overlay = {"png": path, "x": 0, "y": 0, "start": s, "end": s, "fade": 0.25}; frame-sized plates go at 0,0.
A clip (an animated insert) is {"video": path, "x", "y", "start", "end"}: played from its first frame at
`start`, its own entry and exit inside it, its sound (if any) never taken.
"""
from __future__ import annotations

import math
import tempfile
from pathlib import Path
from typing import Dict, List

# media re-exports overlay_png, so media's modules are imported inside the functions (no import cycle).


def _clip(i: int, item: Dict) -> str:
    return "[{k}:v]format=rgba,setpts=PTS-STARTPTS+{s:.3f}/TB".format(k=i + 1, s=float(item["start"]))


def _layer(i: int, item: Dict, fps: float) -> str:
    from ..media.ffmpeg import MediaError

    start, end = float(item["start"]), float(item["end"])
    if end <= start:
        raise MediaError("Картинка {} показывается 0 секунд: {}–{}".format(_src(item), start, end))
    if item.get("video"):
        return _place(_clip(i, item), i, item, start, end)
    fade = max(0.0, min(float(item.get("fade", 0.25)), (end - start) / 2))
    frames = int(math.ceil((end - start) * fps)) + 1
    chain = ("[{k}:v]format=rgba,loop=loop=-1:size=1:start=0,trim=end_frame={n},"
             "setpts=N/{fps:.3f}/TB+{s:.3f}/TB").format(k=i + 1, n=frames, fps=fps, s=start)
    if fade:
        chain += ",fade=t=in:st={s:.3f}:d={f:.3f}:alpha=1,fade=t=out:st={o:.3f}:d={f:.3f}:alpha=1".format(
            s=start, f=fade, o=end - fade)
    return _place(chain, i, item, start, end)


def _src(item: Dict):
    return item.get("video") or item["png"]


def _place(chain: str, i: int, item: Dict, start: float, end: float) -> str:
    return ("{c}[o{i}];[v{i}][o{i}]overlay=x={x}:y={y}:eof_action=pass:"
            "enable='between(t,{s:.3f},{e:.3f})'[v{n}]").format(
        c=chain, i=i, n=i + 1, x=int(item.get("x", 0)), y=int(item.get("y", 0)), s=start, e=end)


def overlay_png(src, pngs: List[Dict], out) -> Path:
    """Writes `out` with every picture shown in its span (soft fade in and out); sound copied."""
    from ..media.codec import encode
    from ..media.ffmpeg import MediaError, ensure_file
    from ..media.graph import graph_args
    from ..media.probe import probe

    src, out = ensure_file(src), Path(out)
    if not pngs:
        raise MediaError("Нет ни одной картинки для наложения.")
    info = probe(src)
    fps = info["fps"] if 1 <= info["fps"] <= 240 else 25.0
    inputs = ["-i", src]
    for item in pngs:
        inputs += ["-i", ensure_file(_src(item))]
    graph = ";".join(["[0:v]null[v0]"] + [_layer(i, item, fps) for i, item in enumerate(pngs)])
    kbps = min(max(info["video_kbps"] or 8000, 2000), 50000)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aiediting-") as tmp:
        pre = inputs + graph_args(graph, Path(tmp))
        maps = ["-map", "[v{}]".format(len(pngs)), "-map", "0:a?", "-movflags", "+faststart"]
        try:
            encode(pre, maps + ["-c:a", "copy"], out, kbps=kbps)
        except MediaError:  # a sound codec the container cannot carry: re-encode it
            encode(pre, maps + ["-c:a", "aac", "-b:a", "192k"], out, kbps=kbps)
    return out
