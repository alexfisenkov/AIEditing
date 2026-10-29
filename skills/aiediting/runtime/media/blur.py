"""Soft blur of chosen areas, nothing cut: still areas for a time span, moving ones along a path.

Region = {"x","y","w","h","start","end","track": bool[, "path": [{"t","x","y"}, ...]]} in pixels
of the picture as shown (rotation applied). With track and no path, the area is followed by itself.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, List

from .codec import encode
from .ffmpeg import MediaError, ensure_file
from .graph import graph_args
from .probe import probe


def _lerp_expr(path: List[Dict], key: str) -> str:
    """Piecewise-linear position over time as a flat ffmpeg expression (no deep nesting)."""
    terms = []
    for a, b in zip(path, path[1:]):
        dt = max(b["t"] - a["t"], 1e-3)
        terms.append("gte(t,{t0:.3f})*lt(t,{t1:.3f})*({v0:.1f}+({dv:.2f})*(t-{t0:.3f})/{dt:.3f})".format(
            t0=a["t"], t1=b["t"], v0=a[key], dv=b[key] - a[key], dt=dt))
    terms.append("gte(t,{:.3f})*{:.1f}".format(path[-1]["t"], path[-1][key]))
    terms.append("lt(t,{:.3f})*{:.1f}".format(path[0]["t"], path[0][key]))
    return "+".join(terms)


def _box(region: Dict, width: int, height: int) -> Dict:
    x, y = max(0, int(region["x"])) // 2 * 2, max(0, int(region["y"])) // 2 * 2
    w = min(int(region["w"]), width - x) // 2 * 2
    h = min(int(region["h"]), height - y) // 2 * 2
    if w < 2 or h < 2:
        raise MediaError("Область блюра вне кадра: {}".format(region))
    return {"x": x, "y": y, "w": w, "h": h}


def _step(i: int, region: Dict, src: Path, width: int, height: int) -> str:
    box = _box(region, width, height)
    x, y = str(box["x"]), str(box["y"])
    if region.get("track"):
        if not region.get("path"):
            from ..look.track import track_region
            region = dict(region, path=track_region(src, region))
        x, y = "'{}'".format(_lerp_expr(region["path"], "x")), "'{}'".format(_lerp_expr(region["path"], "y"))
    sigma = max(6.0, min(box["w"], box["h"]) / 4.0)
    span = "between(t,{:.3f},{:.3f})".format(float(region["start"]), float(region["end"]))
    return ("[v{i}]split=2[a{i}][b{i}];[b{i}]crop=w={w}:h={h}:x={x}:y={y},gblur=sigma={s:.1f}:steps=3[c{i}];"
            "[a{i}][c{i}]overlay=x={x}:y={y}:enable='{span}'[v{n}]").format(
        i=i, n=i + 1, w=box["w"], h=box["h"], x=x, y=y, s=sigma, span=span)


def blur_regions(src, regions: List[Dict], out) -> Path:
    """Writes `out`: the same video with every region blurred in its span; sound copied as is."""
    src, out = ensure_file(src), Path(out)
    info = probe(src)
    if not regions:
        raise MediaError("Нет ни одной области для блюра.")
    graph = ";".join(["[0:v]null[v0]"] + [_step(i, r, src, info["width"], info["height"])
                                           for i, r in enumerate(regions)])
    kbps = min(max(info["video_kbps"] or 8000, 2000), 50000)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aiediting-") as tmp:
        pre = ["-i", src] + graph_args(graph, Path(tmp))
        maps = ["-map", "[v{}]".format(len(regions)), "-map", "0:a?", "-movflags", "+faststart"]
        try:
            encode(pre, maps + ["-c:a", "copy"], out, kbps=kbps)
        except MediaError:  # a sound codec the container cannot carry: re-encode it
            encode(pre, maps + ["-c:a", "aac", "-b:a", "192k"], out, kbps=kbps)
    return out
