"""Making one finished video from the plan: cut → blur → movement → 9:16 → pictures → music → loudness."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict

from .aftercare import after, fit_audio
from .speed import rate_of
from .timeline import map_range, to_out


def _full(ctx, keep) -> bool:
    return len(keep) == 1 and keep[0][0] <= 0.05 and keep[0][1] >= ctx.info["duration"] - 0.05


def _regions(ctx, keep):
    out = []
    for r in ctx.regions:
        span = map_range(r["start"], r["end"], keep)
        if not span:
            continue
        item = dict(r, start=span[0], end=span[1])
        if r.get("path"):
            item["path"] = [dict(p, t=to_out(p["t"], keep)) for p in r["path"] if to_out(p["t"], keep) is not None]
        out.append(item)
    return out


def _moves(ctx, keep):
    spans = [(m, map_range(m["start"], m["end"], keep)) for m in ctx.motion]
    return [dict(m, start=s[0], end=s[1]) for m, s in spans if s and s[1] - s[0] > 0.3]


def name_of(ctx, piece: Dict) -> Path:
    stem = ctx.src.stem + ("-" + piece["id"] if piece.get("id") else "")
    out = ctx.outdir / (stem + ".mp4")
    return ctx.outdir / (stem + "-монтаж.mp4") if out == ctx.src else out


def render_piece(ctx, piece: Dict) -> Dict:
    from .. import media
    from .moving import apply_motion
    from .overlays import draw, specs

    keep, tmp = piece["keep"], ctx.work / (piece.get("id") or "whole")
    tmp.mkdir(parents=True, exist_ok=True)
    cur, screen, done = ctx.src, ctx.screen, {"id": piece.get("id")}
    if not _full(ctx, keep):
        cur = media.cut_spans(cur, keep, tmp / "1-склейка.mp4")
        if screen is not None and ctx.motion:
            screen = media.cut_spans(screen, keep, tmp / "1-экран.mp4")
    regions = _regions(ctx, keep) if ctx.has("blur_regions") else []
    if regions:
        cur = media.blur_regions(cur, regions, tmp / "2-блюр.mp4")
        ctx.report["blurred"] += [dict(r, piece=piece.get("id")) for r in regions]
    moves = _moves(ctx, keep) if ctx.has("motion") else []
    if moves:
        cur = apply_motion(cur, moves, ctx.layout, tmp / "3-движение.mp4", screen)
        ctx.report["motion"] += moves
    if piece.get("layout"):
        cur = media.vertical(cur, piece["layout"], tmp / "4-вертикаль.mp4")
    pictures = ctx.has("plate") or ctx.has("overlay_png")  # captions and plates only with their own steps
    items = [i for i in specs(ctx, piece) if pictures or i["kind"] == "animation"] \
        if pictures or ctx.has("animations") else []
    if items:
        from ..media.vertical import shown_size
        from .anim_layer import layers

        frame, moving = shown_size(media.probe(cur)), [i for i in items if i["kind"] == "animation"]
        still = [i for i in items if i["kind"] != "animation"]
        pngs = draw(ctx, piece, still, frame, tmp / "плашки") if still else []
        pngs += layers(ctx, piece, moving, frame, tmp / "анимации") if moving else []
        cur = media.overlay_png(cur, pngs, tmp / "5-плашки.mp4") if pngs else cur
    rate = rate_of(ctx.p("speed", 1.0))
    if rate != 1.0:  # after the pictures, so they speed up with the voice; before the music, which stays as it is
        cur = media.speed_up(cur, rate, tmp / "5-скорость.mp4")
    lufs = float(ctx.p("lufs", -16))
    if ctx.has("music") and ctx.music and media.probe(cur)["has_audio"]:
        from .music import mix

        accents = [i["start"] / rate for i in items if i["kind"] in ("card", "chapter")]
        cur = mix(cur, ctx.music, accents, lufs, tmp / "6-музыка.mp4")
    if ctx.has("loudnorm") and media.probe(cur)["has_audio"]:
        cur = fit_audio(media.loudnorm(cur, tmp / "7-громкость.mp4", lufs=lufs), tmp / "8-ровно.mp4")
    final = name_of(ctx, piece)
    if Path(cur) == ctx.src:
        shutil.copyfile(str(cur), str(final))  # nothing changed the picture: a copy, never the source
    else:
        shutil.move(str(cur), str(final))
    done.update(video=final, duration=round(media.probe(final)["duration"], 3))
    return after(ctx, piece, final, done)
