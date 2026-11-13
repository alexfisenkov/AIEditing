"""Keep only the given spans and splice them in one ffmpeg pass.

Each span is trimmed by timestamps (works for variable frame rate too) and the pieces go through
`concat`, which starts every piece of picture and sound together, so drift cannot pile up.
Every seam of the sound gets a few milliseconds of fade on both sides: no click, and not a sample longer or shorter.
`cut_program` does the same from several files: each piece from its camera, with its crop, the sound from one file.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .codec import encode
from .ffmpeg import MediaError, ensure_file
from .graph import graph_args
from .probe import probe

EDGE = 0.005  # s of fade on each side of a seam: 10 ms of transition, too short to hear, long enough to kill a click


def _fades(i: int, n: int, dur: float) -> str:
    """Fade-in at a piece's start and fade-out at its end, except at the very start and end of the result."""
    d = min(EDGE, dur / 3.0)
    parts = []
    if i > 0:
        parts.append("afade=t=in:st=0:d={:.4f}".format(d))
    if i < n - 1:
        parts.append("afade=t=out:st={:.4f}:d={:.4f}".format(max(0.0, dur - d), d))
    return "".join("," + p for p in parts)


def _graph(spans: Sequence[Tuple[float, float]], video: bool, audio: bool) -> str:
    parts, pads = [], []
    for i, (a, b) in enumerate(spans):
        if video:
            parts.append("[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}]".format(a=a, b=b, i=i))
            pads.append("[v{}]".format(i))
        if audio:
            parts.append("[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS{f}[a{i}]".format(
                a=a, b=b, i=i, f=_fades(i, len(spans), b - a)))
            pads.append("[a{}]".format(i))
    parts.append("{}concat=n={}:v={}:a={}{}{}".format(
        "".join(pads), len(spans), int(video), int(audio),
        "[vout]" if video else "", "[aout]" if audio else ""))
    return ";\n".join(parts)


def _encode(inputs: List[Path], graph: str, out: Path, video: bool, audio: bool, kbps: int) -> Path:
    maps = (["-map", "[vout]"] if video else []) + (["-map", "[aout]"] if audio else [])
    post = maps + (["-c:a", "aac", "-b:a", "192k"] if audio else []) + ["-movflags", "+faststart"]
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aiediting-") as tmp:
        pre = [x for p in inputs for x in ("-i", p)] + graph_args(graph, Path(tmp))
        encode(pre, post, out, kbps=kbps, video=video)
    return out


def cut_spans(src, spans: List[Tuple[float, float]], out, kbps=None) -> Path:
    """Writes `out` with only `spans` of `src` (seconds), H.264 yuv420p + AAC, one encode.

    `kbps` overrides the source's own bitrate where the result is encoded again later."""
    src, out = ensure_file(src), Path(out)
    spans = [(float(a), float(b)) for a, b in spans if float(b) > float(a)]
    if not spans:
        raise MediaError("Нечего склеивать: список отрезков пуст.")
    info = probe(src)
    video, audio = info["has_video"], info["has_audio"]
    kbps = kbps or min(max(info["video_kbps"] or 8000, 2000), 50000)
    return _encode([src], _graph(spans, video, audio), out, video, audio, kbps)


def _look(crop: Optional[Dict], w: int, h: int, fps: float, dur: float) -> str:
    """The frame of one piece: filled to w×h, then a still crop (`zoom`, `y`: 0 top … 0.5 middle … 1 bottom of the
    room left) or a slow push from `zoom` to `to` over the piece."""
    fill = "scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1".format(w=w, h=h)
    if not crop:
        return fill
    z, y = float(crop.get("zoom", 1.0)), float(crop.get("y", 0.5))
    if crop.get("to") is not None:
        frames = max(1, int(round(dur * fps)))
        return fill + ",zoompan=z='{z:.4f}+({t:.4f}-{z:.4f})*min(on/{n},1)':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)*{y:.3f}'" \
                      ":d=1:s={w}x{h}:fps={fps:.3f},setsar=1".format(z=z, t=float(crop["to"]), n=frames, y=y, w=w, h=h, fps=fps)
    if z <= 1.0:
        return fill
    return fill + ",crop=w=iw/{z:.4f}:h=ih/{z:.4f}:x=(iw-ow)/2:y=(ih-oh)*{y:.3f},scale={w}:{h},setsar=1".format(
        z=z, y=y, w=w, h=h)


def cut_program(inputs: List, pieces: List[Dict], out, kbps=None) -> Path:
    """One video from pieces of several files: piece = {"input", "start", "end", "crop", "sound": [input, start]}.

    The picture of each piece comes from its input (seconds of that file) filled to the size of input 0; the sound of
    the same length from `sound`. Picture and sound of a piece start together, as in `cut_spans`."""
    inputs = [ensure_file(p) for p in inputs]
    out = Path(out)
    pieces = [p for p in pieces if float(p["end"]) > float(p["start"])]
    if not pieces:
        raise MediaError("Нечего склеивать: список отрезков пуст.")
    main = probe(inputs[0])
    w, h, fps = main["width"] // 2 * 2, main["height"] // 2 * 2, main["fps"] or 25.0
    audio = all(probe(inputs[int(p["sound"][0])])["has_audio"] for p in pieces)
    parts, pads = [], []
    for i, p in enumerate(pieces):
        a, b = float(p["start"]), float(p["end"])
        parts.append("[{n}:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS,fps={fps:.3f},{look}[v{i}]".format(
            n=int(p["input"]), a=a, b=b, fps=fps, look=_look(p.get("crop"), w, h, fps, b - a), i=i))
        pads.append("[v{}]".format(i))
        if audio:
            s = float(p["sound"][1])
            parts.append("[{n}:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS{f}[a{i}]".format(
                n=int(p["sound"][0]), a=s, b=s + b - a, f=_fades(i, len(pieces), b - a), i=i))
            pads.append("[a{}]".format(i))
    parts.append("{}concat=n={}:v=1:a={}[vout]{}".format("".join(pads), len(pieces), int(audio), "[aout]" if audio else ""))
    kbps = kbps or min(max(main["video_kbps"] or 8000, 2000), 50000)
    return _encode(inputs, ";\n".join(parts), out, True, audio, kbps)
