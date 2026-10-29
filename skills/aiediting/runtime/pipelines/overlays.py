"""Chapters, cards and captions as pictures from the design layer, laid over the piece in its own time.

Animated inserts travel in the same list (kind "animation") but are made by anim_layer, not drawn here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .timeline import map_range


def specs(ctx, piece: Dict) -> List[Dict]:
    """Every overlay of the piece in output time (captions only for burned-in subtitles)."""
    out = []
    for o in ctx.overlays:
        span = map_range(o["start"], o["end"], piece["keep"])
        if span and span[1] - span[0] > 0.2:
            out.append(dict(o, start=span[0], end=span[1]))
    if ctx.p("captions") == "burned":
        from .captions import cues
        from .words import mapped

        out += cues(mapped(ctx.transcript().get("words", []), piece["keep"]), ctx.p("glossary", {}) or {})
    return out


def _at_seam(ctx, design: Dict, layout, frame) -> Dict:
    """In a «screen over face» stack captions sit on the seam, not on the face."""
    if not layout or layout.get("kind") != "stack" or not layout.get("face"):
        return design
    from ..media.vertical import _screen_height, shown_size

    w, h = shown_size(ctx.info)
    screen = layout.get("screen") or {"w": w, "h": h}
    seam = _screen_height(screen, frame) / float(frame[1])
    cap = dict(design["video"]["caption"])
    half = cap["size"] * (1.18 + 2 * cap.get("pad_y", 0.2)) / 2.0
    cap.update(where="top", margin=0.0)
    safe = dict(design["video"].get("safe_zone_vertical", {}), top=max(0.0, seam - half))
    return dict(design, video=dict(design["video"], caption=cap, safe_zone_vertical=safe))


def draw(ctx, piece: Dict, items: List[Dict], frame, folder: Path) -> List[Dict]:
    """PNG for each item: [{png, start, end, fade}] ready for overlay_png; a card never lands on the face."""
    from ..render import plate
    from .cards import where
    from .offface import off_face

    layout = piece.get("layout")
    base = ctx.design(vertical=bool(layout))
    seam = _at_seam(ctx, base, layout, frame)  # only captions move to the seam; cards keep the safe zone
    spot, face = where(ctx, frame, layout), _face(ctx, layout, frame)
    pngs = []
    for k, item in enumerate(items):
        kind = item["kind"]
        design = seam if kind == "caption" else base
        place = spot if kind == "card" else None
        if place == "none":
            continue
        fade = float(design["video"].get(kind, {}).get("fade", 0.15 if kind == "caption" else 0.3))
        out = folder / "{}-{:03d}.png".format(kind, k)
        path = off_face(lambda d: plate(item["text"], d, kind, frame_size=frame, where=place, out=out),
                        design, kind, face if kind == "card" else None)
        if path is None:
            ctx.note("Карточка «{}» не помещается мимо лица — не показана".format(item["text"].split("\n")[0]))
            continue
        pngs.append({"png": path, "x": 0, "y": 0, "start": item["start"], "end": item["end"],
                     "fade": 0.0 if kind == "caption" else fade})
    return pngs


def _face(ctx, layout, frame):
    if not layout:
        return None
    from ..media.vertical import shown_size
    from .placement import face_in_vertical

    return face_in_vertical(layout, shown_size(ctx.info), frame)
