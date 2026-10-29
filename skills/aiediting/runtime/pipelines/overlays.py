"""Chapters, cards and captions as pictures from the design layer, laid over the piece in its own time."""
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
    """PNG for each item: [{png, start, end, fade}] ready for overlay_png."""
    from ..render import plate
    from .cards import where

    design = _at_seam(ctx, ctx.design(vertical=bool(piece.get("layout"))), piece.get("layout"), frame)
    spot = where(ctx, frame)
    pngs = []
    for k, item in enumerate(items):
        place = spot if item["kind"] == "card" else None
        if place == "none":
            continue
        fade = float(design["video"].get(item["kind"], {}).get("fade", 0.15 if item["kind"] == "caption" else 0.3))
        path = plate(item["text"], design, item["kind"], frame_size=frame, where=place,
                     out=folder / "{}-{:03d}.png".format(item["kind"], k))
        pngs.append({"png": path, "x": 0, "y": 0, "start": item["start"], "end": item["end"],
                     "fade": 0.0 if item["kind"] == "caption" else fade})
    return pngs
