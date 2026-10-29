"""Animated inserts of one piece: made by HyperFrames, laid where a card goes — the corner opposite the face."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .report import stamp


def _covers(x: int, y: int, size, face) -> bool:
    return bool(face) and x < face["x"] + face["w"] and face["x"] < x + size[0] and \
        y < face["y"] + face["h"] and face["y"] < y + size[1]


def layers(ctx, piece: Dict, items: List[Dict], frame, folder: Path) -> List[Dict]:
    """[{video, x, y, start, end}] for overlay_png; each insert is also listed in the report."""
    from ..render import RenderError, animation
    from ..render.anim_spec import spec
    from ..render.place import place
    from .cards import where
    from .overlays import _face

    layout = piece.get("layout")
    design = ctx.design(vertical=bool(layout))
    s = spec(design)
    spot = where(ctx, frame, layout)
    if spot == "none":
        ctx.note("Анимации не показаны: профиль не кладёт графику поверх экрана (cards.on_screen = none)")
        return []
    spot, face, out = spot or s.get("where", "top-left"), _face(ctx, layout, frame), []
    for k, item in enumerate(items):
        name = "«{}» {}".format(item.get("template"), stamp(item["start"]))
        try:
            clip = animation(item, design, frame, folder / "{:03d}".format(k), item["end"] - item["start"])
        except RenderError as exc:
            ctx.note("Анимация {} не сделана: {}".format(name, exc))
            continue
        x, y = place(design, frame, clip["size"], spot, float(s.get("margin", 0.045)))
        if _covers(x, y, clip["size"], face):
            ctx.note("Анимация {} не помещается мимо лица — не показана".format(name))
            continue
        out.append({"video": clip["video"], "x": x, "y": y, "start": item["start"], "end": item["end"]})
        ctx.report.setdefault("animations", []).append(
            {"at": item["start"], "end": item["end"], "template": item.get("template"), "title": item.get("title", ""),
             "text": item.get("text", ""), "where": spot, "piece": piece.get("id")})
    return out
