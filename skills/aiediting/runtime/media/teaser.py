"""The teaser's assembly: an intro, then fragments of a long video, some of them fast, a bar over them, one encode.

Sounds are synthesised here (a click, a soft rush), so the format needs no sound files and no generation.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, List, Sequence

from .codec import encode
from .ffmpeg import ensure_file
from .graph import graph_args

EDGE = 0.02  # s: each fragment's sound fades this fast, so a cut does not click
FAST = 2.0   # from this rate on a fragment is a fast-forward: its speech is only a texture under the rush
CLICK = "aevalsrc='0.7*exp(-t*70)*sin(2*PI*1400*t)':s=48000:d=0.14"
RUSH = ("anoisesrc=d={d:.3f}:c=pink:r=48000:a=0.5,highpass=f=500,lowpass=f=5000,"
        "afade=t=in:d={i:.3f},afade=t=out:st={o:.3f}:d={i:.3f}")


def _tempo(rate: float) -> str:
    """atempo takes at most 2 at a time."""
    parts = []
    while rate > 2.0:
        parts.append("atempo=2")
        rate /= 2.0
    return ",".join(parts + ["atempo={:.4f}".format(rate)])


def seconds(fragments: Sequence[Dict]) -> float:
    return sum((float(f["end"]) - float(f["start"])) / float(f.get("rate", 1.0)) for f in fragments)


def _fragment(k: int, f: Dict, fps: int, w: int, h: int) -> List[str]:
    rate = float(f.get("rate", 1.0))
    d = (float(f["end"]) - float(f["start"])) / rate
    quiet = ",volume=0.22" if rate >= FAST else ""
    return ["[{k}:v]setpts=PTS/{r:.4f},fps={fps},scale={w}:{h},setsar=1,format=yuv420p[v{k}]".format(
        k=k, r=rate, fps=fps, w=w, h=h),
        "[{k}:a]{t}{q},afade=t=in:d={e},afade=t=out:st={o:.3f}:d={e},aformat=sample_rates=48000:"
        "channel_layouts=stereo[a{k}]".format(k=k, t=_tempo(rate), q=quiet, e=EDGE, o=max(0.0, d - EDGE))]


def _rush_at(at: float, length: float, label: str) -> str:
    edge = min(0.18, length / 2.0)
    return (RUSH.format(d=length, i=edge, o=length - edge) +
            ",volume=0.5,aformat=sample_rates=48000:channel_layouts=stereo,adelay={m}:all=1[{l}]".format(
                m=int(at * 1000), l=label))


def montage(src, fragments: Sequence[Dict], intro: str, intro_seconds: float, press: float, strip: Dict, out,
            size=(1920, 1080), fps: int = 30, kbps: int = 12000) -> Path:
    """`intro` and `strip` are PNG sequences (printf patterns); the strip lies over the body only."""
    src, out = ensure_file(src), Path(out)
    inputs: List[str] = []
    for f in fragments:
        inputs += ["-ss", "{:.3f}".format(float(f["start"])), "-t", "{:.3f}".format(float(f["end"]) - float(f["start"])),
                   "-i", str(src)]
    n = len(fragments)
    inputs += ["-framerate", str(fps), "-i", intro, "-framerate", str(fps), "-i", strip["pattern"]]
    parts = ["[{}:v]fps={},format=yuv420p,setsar=1[vi]".format(n, fps),
             "anullsrc=r=48000:cl=stereo,atrim=0:{:.3f}[ai]".format(intro_seconds)]
    for k, f in enumerate(fragments):
        parts += _fragment(k, f, fps, size[0], size[1])
    joined = "[vi][ai]" + "".join("[v{k}][a{k}]".format(k=k) for k in range(n))
    parts.append(joined + "concat=n={}:v=1:a=1[vc][ac]".format(n + 1))
    parts.append("[{}:v]format=rgba,setpts=PTS-STARTPTS+{:.3f}/TB[st]".format(n + 1, intro_seconds))
    parts.append("[vc][st]overlay=0:{}:eof_action=repeat[vout]".format(strip["y"]))  # the bar stays to the last frame
    sounds = ["[ac]"]
    parts.append("{},aformat=sample_rates=48000:channel_layouts=stereo,adelay={}:all=1[click]".format(
        CLICK, int(press * 1000)))
    sounds.append("[click]")
    at = intro_seconds
    for k, f in enumerate(fragments):
        length = (float(f["end"]) - float(f["start"])) / float(f.get("rate", 1.0))
        if float(f.get("rate", 1.0)) >= FAST:
            parts.append(_rush_at(at, length, "r{}".format(k)))
            sounds.append("[r{}]".format(k))
        at += length
    parts.append("".join(sounds) + "amix=inputs={}:duration=first:normalize=0[aout]".format(len(sounds)))
    post = ["-map", "[vout]", "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-r", str(fps), "-movflags", "+faststart"]
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aiediting-") as tmp:
        encode(inputs + graph_args(";\n".join(parts), Path(tmp)), post, out, kbps=kbps)
    return out
