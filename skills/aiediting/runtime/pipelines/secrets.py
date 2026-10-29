"""Secret-looking places go to the person; only what they tick (or draw themselves) is blurred."""
from __future__ import annotations

from typing import Dict, List

QUESTION = ("Что закрыть блюром? Поставьте blur: true у нужных candidates (у кого нет rect — найдено в "
            "речи, укажите область сами) и добавьте свои области в extra: {x,y,w,h,start,end,track}.")


def _frame_count(ctx) -> int:
    return int(ctx.p("secret_frames", max(6, min(60, ctx.info["duration"] // 10))))


def plan_find(ctx) -> None:
    from ..look import find_secrets
    from .layout import _snapshots

    n = _frame_count(ctx)
    shots = _snapshots(ctx, ctx.src, "frames-secrets", n) if ctx.info["has_video"] else []
    ctx.candidates = find_secrets(shots, ctx.transcript(), ocr=ctx.p("ocr", "auto"))


def _region(c: Dict, step: float, total: float) -> Dict:
    """Seen on snapshots i..j: closed from the snapshot before (where it was not) to the one after."""
    rect = c["rect"]
    start, end = float(c.get("start") or 0.0), float(c.get("end") or total)
    if c.get("source") == "ocr":
        start, end = max(0.0, start - step), min(total, end + step)
    elif end - start < step:  # a time from speech with a box drawn by the person: the stretch around it
        start, end = max(0.0, start - step / 2), min(total, end + step / 2)
    return {"x": rect["x"], "y": rect["y"], "w": rect["w"], "h": rect["h"], "start": start, "end": end,
            "track": bool(c.get("track")), "what": "{}: {}".format(c.get("kind", ""), c.get("text", ""))}


def plan_blur(ctx) -> None:
    items = [dict(c, id="s{}".format(i + 1), blur=False) for i, c in enumerate(ctx.candidates)]
    ok, data = ctx.ask("secrets", QUESTION, {"candidates": items, "extra": []})
    if not ok:
        return
    total, step = ctx.info["duration"], ctx.info["duration"] / max(1, _frame_count(ctx))
    regions: List[Dict] = []
    for c in data.get("candidates", []):
        if not c.get("blur"):
            continue
        if not c.get("rect"):
            ctx.note("«{}» отмечено, но области на кадре нет — не закрыто; добавьте её в extra".format(
                c.get("text")))
            continue
        regions.append(_region(c, step, total))
    for e in data.get("extra", []):
        regions.append(dict(e, start=float(e.get("start", 0.0)), end=float(e.get("end", total)),
                            track=bool(e.get("track")), what=e.get("what", "своя область")))
    ctx.regions = _check_tracks(ctx, regions)


def _check_tracks(ctx, regions: List[Dict]) -> List[Dict]:
    """A moving area is followed first and shown as frames before anything is written."""
    moving = [r for r in regions if r["track"] and not r.get("path")]
    if not moving:
        return regions
    from ..look import track_region
    from .preview import boxes_on_frames

    for r in moving:
        r["path"] = track_region(ctx.src, r)
    shots = boxes_on_frames(ctx, moving)
    ok, _ = ctx.ask("blur_track", "Так закрывается движущаяся область? Рамки — где пройдёт блюр.",
                    {"frames": shots})
    if ok:
        return regions
    ctx.note("Движущиеся области не закрыты: ведение по кадрам не одобрено")
    return [r for r in regions if not r["track"]]
