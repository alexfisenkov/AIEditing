"""9:16 from any source: «screen over face» stack, face close-up (with screen inserts), native vertical.

Layout = {"kind": "stack"|"face"|"native", "face": Rect|None, "screen": Rect|None,
          "room": float (crop height in face heights, 1.0 for a camera window), "inserts": [{start,end}]}
Rect = {"x","y","w","h"} in pixels of the picture as shown.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from .codec import encode
from .ffmpeg import MediaError, ensure_file
from .probe import probe

SIZE = (1080, 1920)
BACKGROUND = "0x0E0E10"  # the «night» graphite of the example design
MAX_SCREEN_SHARE = 0.6   # the screen never takes more than this share of the height in a stack
SOFT_FACE = 2.0          # a face stretched more than this many times looks soft


def _even(v: float) -> int:
    return max(2, int(round(v / 2.0)) * 2)


def shown_size(info: Dict) -> Tuple[int, int]:
    w, h = info["width"], info["height"]
    return (h, w) if info.get("rotation") in (90, 270) else (w, h)


def _crop(rect: Dict, aspect: float, frame: Tuple[int, int], room: float = 1.0) -> Dict:
    """A box of `aspect` (w/h) around the centre of `rect`, `room` rect-heights tall, inside the frame."""
    fw, fh = frame
    h = min(float(rect["h"]) * room, fh, fw / aspect)
    w = h * aspect
    cx, cy = rect["x"] + rect["w"] / 2.0, rect["y"] + rect["h"] / 2.0
    x = min(max(0.0, cx - w / 2.0), fw - w)
    y = min(max(0.0, cy - h / 2.0), fh - h)
    return {"x": int(x), "y": int(y), "w": _even(min(w, fw - int(x)) - 1), "h": _even(min(h, fh - int(y)) - 1)}


crop_box = _crop  # for other runtime modules that frame a face the same way


def _cut(r: Dict) -> str:
    return "crop={w}:{h}:{x}:{y}".format(**r)


def _screen_height(screen: Dict, size) -> int:
    return min(_even(size[0] * screen["h"] / float(screen["w"])), _even(size[1] * MAX_SCREEN_SHARE))


def _stack(label: str, layout: Dict, frame, size, out: str) -> str:
    screen = layout.get("screen") or {"x": 0, "y": 0, "w": frame[0], "h": frame[1]}
    hs = _screen_height(screen, size)
    top = _cut(_crop(screen, size[0] / float(hs), frame, 1.0))
    if not layout.get("face"):
        return "[{l}]{t},scale={w}:{h},pad={W}:{H}:0:(oh-ih)/2:color={bg},setsar=1{o}".format(
            l=label, t=top, w=size[0], h=hs, W=size[0], H=size[1], bg=BACKGROUND, o=out)
    hb = size[1] - hs
    face = _cut(_crop(layout["face"], size[0] / float(hb), frame, layout.get("room", 1.0)))
    k = label.replace(":", "")
    return ("[{l}]split=2[st{k}][fa{k}];[st{k}]{t},scale={w}:{hs},setsar=1[top{k}];"
            "[fa{k}]{f},scale={w}:{hb},setsar=1[bot{k}];[top{k}][bot{k}]vstack=2{o}").format(
        l=label, k=k, t=top, f=face, w=size[0], hs=hs, hb=hb, o=out)


def _face(label: str, layout: Dict, frame, size, out: str) -> str:
    if not layout.get("face"):
        raise MediaError("Для раскладки «лицо крупно» нужен прямоугольник лица (face).")
    box = _crop(layout["face"], size[0] / float(size[1]), frame, layout.get("room", 1.0))
    return "[{l}]{c},scale={w}:{h},setsar=1{o}".format(l=label, c=_cut(box), w=size[0], h=size[1], o=out)


def _graph(layout: Dict, frame, size) -> str:
    kind = layout.get("kind")
    if kind == "native":
        bg = str(layout.get("background") or BACKGROUND).replace("#", "0x")  # a horizontal picture keeps its shape
        return ("[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:"
                "color={bg},setsar=1[vout]").format(w=size[0], h=size[1], bg=bg)
    if kind == "stack":
        return _stack("0:v", layout, frame, size, "[vout]")
    if kind != "face":
        raise MediaError("Неизвестная раскладка 9:16 «{}»: stack, face, native".format(kind))
    inserts = [i for i in layout.get("inserts") or [] if float(i["end"]) > float(i["start"])]
    if not inserts:
        return _face("0:v", layout, frame, size, "[vout]")
    when = "+".join("between(t,{:.3f},{:.3f})".format(float(i["start"]), float(i["end"])) for i in inserts)
    return ";".join(["[0:v]split=2[fv0][sv0]", _face("fv0", layout, frame, size, "[fv]"),
                     _stack("sv0", layout, frame, size, "[sv]"),
                     "[fv][sv]overlay=0:0:enable='{}'[vout]".format(when)])


def face_upscale(frame: Tuple[int, int], layout: Dict, size=SIZE) -> Optional[float]:
    """How many times the face is stretched; above SOFT_FACE the face looks soft. None: no face shown."""
    if layout.get("kind") not in ("stack", "face") or not layout.get("face"):
        return None
    hb = size[1] if layout["kind"] == "face" else size[1] - _screen_height(
        layout.get("screen") or {"w": frame[0], "h": frame[1]}, size)
    box = _crop(layout["face"], size[0] / float(hb), frame, layout.get("room", 1.0))
    return round(hb / float(box["h"]), 2)


def vertical(src, layout: Dict, out, size=SIZE) -> Path:
    """Writes `out` as a 1080x1920 picture by `layout`; sound kept (AAC)."""
    src, out = ensure_file(src), Path(out)
    info = probe(src)
    if not info["has_video"]:
        raise MediaError("В файле нет видео: {}".format(src))
    graph = _graph(layout, shown_size(info), size)
    maps = ["-map", "[vout]", "-map", "0:a?", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    out.parent.mkdir(parents=True, exist_ok=True)
    encode(["-i", src, "-filter_complex", graph], maps, out, kbps=8000)
    return out
