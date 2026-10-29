"""Animated inserts of one piece: made by HyperFrames, laid where a card goes — the corner opposite the face.

One insert that fails (tokens, fonts, the renderer) is left out with a note; the video is made anyway.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .report import stamp

FAILS = (KeyError, OSError, TypeError, ValueError)


def _covers(x: int, y: int, size, face) -> bool:
    return bool(face) and x < face["x"] + face["w"] and face["x"] < x + size[0] and \
        y < face["y"] + face["h"] and face["y"] < y + size[1]


def _one(ctx, item: Dict, design, s: Dict, spot: str, face, frame, folder: Path) -> Optional[Dict]:
    from ..render import animation
    from ..render.place import place

    clip = animation(item, design, frame, folder, item["end"] - item["start"])
    x, y = place(design, frame, clip["size"], spot, s["margin"])
    if _covers(x, y, clip["size"], face):
        ctx.note("Анимация «{}» {} не помещается мимо лица — не показана".format(item.get("template"),
                                                                                 stamp(item["start"])))
        return None
    return {"video": clip["video"], "x": x, "y": y, "start": item["start"], "end": item["end"]}


def layers(ctx, piece: Dict, items: List[Dict], frame, folder: Path) -> List[Dict]:
    """[{video, x, y, start, end}] for overlay_png; each insert made is also listed in the report."""
    from ..render import RenderError
    from ..render.anim_spec import spec
    from .cards import where
    from .overlays import _face

    layout = piece.get("layout")
    spot = where(ctx, frame, layout)
    if spot == "none":
        ctx.note("Анимации не показаны: профиль не кладёт графику поверх экрана (cards.on_screen = none)")
        return []
    out = []
    for k, item in enumerate(items):
        try:
            design = ctx.design(vertical=bool(layout))
            s = spec(design)
            made = _one(ctx, item, design, s, spot or s["where"], _face(ctx, layout, frame), frame,
                        folder / "{:03d}".format(k))
        except (RenderError,) + FAILS as exc:
            ctx.note("Анимация «{}» {} не сделана: {}".format(item.get("template"), stamp(item["start"]), exc))
            continue
        if made:
            out.append(made)
            ctx.report.setdefault("animations", []).append(
                {"at": item["start"], "end": item["end"], "template": item.get("template"),
                 "title": item.get("title", ""), "text": item.get("text", ""), "piece": piece.get("id")})
    return out
