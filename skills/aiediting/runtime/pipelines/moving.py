"""Rendering approved movement: zoom on the face, or the screen beside the camera (one encode)."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

ZOOM = 1.2
CAMERA_SHARE = 0.34  # of the width, when the screen comes in beside the camera


def _when(spans) -> str:
    return "+".join("between(t,{:.3f},{:.3f})".format(a, b) for a, b in spans)


def _face(layout: Dict, w: int, h: int) -> Dict:
    return (layout or {}).get("face") or {"x": w // 4, "y": h // 4, "w": w // 2, "h": h // 2}


def _graph(kind: str, layout: Dict, w: int, h: int, spans) -> str:
    from ..media.vertical import BACKGROUND, crop_box

    if kind == "zoom":
        face = _face(layout, w, h)
        box = crop_box({"x": face["x"] + face["w"] / 2 - 1, "y": face["y"] + face["h"] / 2 - 1, "w": 2,
                        "h": 2}, w / float(h), (w, h), room=h / ZOOM / 2.0)
        move = "[z]crop={w}:{h}:{x}:{y},scale={W}:{H},setsar=1[m]".format(W=w, H=h, **box)
        return "[0:v]split=2[b][z];{};[b][m]overlay=0:0:enable='{}'[vout]".format(move, _when(spans))
    cw = int(w * CAMERA_SHARE) // 2 * 2
    sw = w - cw
    cam = crop_box(_face(layout, w, h), cw / float(h), (w, h), room=2.5)
    return ("[0:v]split=2[b][c];[c]crop={cw0}:{ch0}:{cx}:{cy},scale={cw}:{H},setsar=1[cam];"
            "[1:v]scale={sw}:{H}:force_original_aspect_ratio=decrease,pad={sw}:{H}:(ow-iw)/2:(oh-ih)/2:"
            "color={bg},setsar=1[scr];[scr][cam]hstack=2[side];[b][side]overlay=0:0:enable='{e}'[vout]").format(
        cw0=cam["w"], ch0=cam["h"], cx=cam["x"], cy=cam["y"], cw=cw, H=h, sw=sw, bg=BACKGROUND, e=_when(spans))


def apply_motion(video: Path, items: List[Dict], layout: Dict, out: Path, screen: Optional[Path] = None) -> Path:
    """items: [{start, end, move: zoom|side}] in this video's time."""
    from ..media import probe
    from ..media.codec import encode
    from ..media.vertical import shown_size

    w, h = shown_size(probe(video))
    kind = items[0]["move"]
    spans = [(float(i["start"]), float(i["end"])) for i in items]
    inputs = ["-i", video] + (["-i", screen] if kind == "side" else [])
    maps = ["-map", "[vout]", "-map", "0:a?", "-c:a", "copy", "-movflags", "+faststart"]
    encode(inputs + ["-filter_complex", _graph(kind, layout, w, h, spans)], maps, out, kbps=8000)
    return out
