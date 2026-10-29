"""Which layout the source has; asked when the guess is shaky. `look` is imported only here, lazily."""
from __future__ import annotations

from typing import Dict, Optional

KINDS = ("face_full", "screen_face_window", "separate_tracks", "vertical", "screen_only")
SURE = 0.6


def _snapshots(ctx, src, name: str, n: int, start=None, end=None):
    from ..look import frames

    folder = ctx.work / name
    found = sorted(folder.glob("frame_*.png")) if folder.is_dir() else []
    if found:
        return found
    if start is None:
        return frames(src, n, folder)
    from ..media import cut_spans  # a piece: snapshots of just that stretch, times shifted back
    piece = cut_spans(src, [(start, end)], ctx.work / (name + ".mp4"))
    return frames(piece, n, folder)


def guess(ctx, start: Optional[float] = None, end: Optional[float] = None, tag: str = "all") -> Dict:
    """LayoutGuess for the source (or one stretch of it); without OpenCV faces are not searched."""
    from ..look import LookError, detect_layout

    shots = _snapshots(ctx, ctx.src, "frames-layout-" + tag, 5, start, end)
    if ctx.screen is not None and start is None:
        shots = [shots, _snapshots(ctx, ctx.screen, "frames-screen", 5)]
    try:
        return dict(detect_layout(shots), degraded=False)
    except LookError as exc:
        ctx.note("Раскладка определялась без поиска лица: {}".format(exc))
    try:
        return dict(detect_layout(shots, detector=lambda _p: []), degraded=True)
    except LookError:
        flat = shots[0] if shots and isinstance(shots[0], list) else shots
        return {"kind": None, "face": None, "confidence": 0.0, "frames": flat, "degraded": True}


def plan_layout(ctx) -> None:
    forced = ctx.p("layout", "auto")
    if isinstance(forced, dict):
        ctx.layout = dict(forced)
        return
    if forced in KINDS:
        ctx.layout = {"kind": forced, "face": ctx.p("face"), "screen": ctx.p("screen"), "confidence": 1.0}
        return
    g = guess(ctx)
    frames = [str(f.get("frame") if isinstance(f, dict) else f) for f in g.get("frames", [])]
    layout = {"kind": g.get("kind"), "face": g.get("face"), "confidence": g.get("confidence", 0.0)}
    if g.get("degraded") or layout["confidence"] < SURE or layout["kind"] is None:
        ok, data = ctx.ask("layout", "Какая здесь раскладка? Поправьте kind ({}) и face {{x,y,w,h}}, "
                           "если я ошибся.".format(", ".join(KINDS)), dict(layout, frames=frames))
        if ok:
            layout.update({k: data.get(k, layout.get(k)) for k in ("kind", "face", "screen")})
    ctx.layout = layout
