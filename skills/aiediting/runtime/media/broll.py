"""Inserts laid over a finished-cut video: a clip without its sound, a photo with a slow push-in. The length never changes."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from .codec import encode
from .ffmpeg import ensure_file
from .graph import graph_args
from .probe import probe
from .vertical import shown_size

PUSH = 0.035  # a photo grows by this much over its window: 3–4 %, enough to feel, not enough to see


def _fit(src: str, size: str) -> str:
    return "{}scale={s}:force_original_aspect_ratio=increase,crop={s}".format(src, s=size)


def _window(items: List[Dict], total: float) -> List[Dict]:
    """The inserts in time order, clipped to the video; one that is left with under a tenth of a second is dropped."""
    out = []
    for i in sorted(items, key=lambda x: float(x["start"])):
        a, b = max(0.0, float(i["start"])), min(float(total), float(i["end"]))
        if b - a >= 0.1:
            out.append(dict(i, start=a, end=b))
    return out


def _inputs(item: Dict) -> List:
    if item.get("kind") == "photo":
        return ["-i", ensure_file(item["file"])]
    return ["-ss", "{:.3f}".format(float(item.get("from") or 0.0)), "-t", "{:.3f}".format(item["end"] - item["start"]),
            "-i", ensure_file(item["file"])]


def _branch(item: Dict, k: int, size: Dict, fps: float) -> str:
    w, h, rate = size["w"], size["h"], "{:.3f}".format(fps)
    shift = "setpts=PTS-STARTPTS+{:.3f}/TB".format(item["start"])
    if item.get("kind") == "photo":
        frames = max(2, int(round((item["end"] - item["start"]) * fps)))
        wide = _fit("[{}:v]".format(k), "{}:{}".format(w * 2, h * 2))  # a bigger still, so the push-in does not shake
        push = "zoompan=z='1+{p}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={w}x{h}:fps={r}".format(
            p=PUSH, n=frames, w=w, h=h, r=rate)
        return "{},{},setsar=1,format=yuv420p,{}[b{}]".format(wide, push, shift, k)
    return "{},setsar=1,fps={},format=yuv420p,{}[b{}]".format(_fit("[{}:v]".format(k), "{}:{}".format(w, h)), rate, shift, k)


def lay_broll(video, items: List[Dict], out, info: Optional[Dict] = None) -> Path:
    """Writes `out`: `video` with each insert over its window. Items are seconds of `video`:
    {"start", "end", "file", "from", "kind": "video"|"photo"|"stock"}. Sound of `video` is copied, an insert's is never used.
    No usable inserts: `video` itself, nothing written."""
    video, out = ensure_file(video), Path(out)
    info = info or probe(video)
    items = _window(items, info["duration"])
    if not items:
        return video
    w, h = shown_size(info)
    size, fps = {"w": w, "h": h}, info["fps"] or 25.0
    parts, last = [], "[0:v]"
    for k, item in enumerate(items, 1):
        parts.append(_branch(item, k, size, fps))
        parts.append("{}[b{}]overlay=enable='between(t,{:.3f},{:.3f})':eof_action=pass[v{}]".format(
            last, k, item["start"], item["end"], k))
        last = "[v{}]".format(k)
    pre = ["-i", video]
    for item in items:
        pre += _inputs(item)
    post = ["-map", last, "-map", "0:a?", "-c:a", "copy", "-t", "{:.3f}".format(info["duration"]),
            "-movflags", "+faststart"]
    out.parent.mkdir(parents=True, exist_ok=True)
    kbps = min(max(info["video_kbps"] or 8000, 2000), 50000)
    with tempfile.TemporaryDirectory(prefix="aiediting-") as tmp:
        encode(pre + graph_args(";\n".join(parts), Path(tmp)), post, out, kbps=kbps)
    return out
