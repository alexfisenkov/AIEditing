"""Plan of a 9:16 video: shot vertically / reframed from horizontal / cut from a long recording.

The plan (stretches, layout of each, soft-face warnings) goes to the person before anything is made.
"""
from __future__ import annotations

from typing import Dict, List

from .timeline import intersect, length
from .words import mapped, quote, spoken

FACE_ROOM = 2.8  # a detected face box is just the face: show head and shoulders
WINDOW_ROOM = 0.8  # inside a round camera window, so its rim does not show in the corners
TO_9x16 = {"screen_face_window": "stack", "screen_only": "stack", "face_full": "face",
           "vertical": "native", "separate_tracks": "face"}


def _layout(ctx, start: float, end: float, tag: str) -> Dict:
    from ..media.vertical import shown_size

    if shown_size(ctx.info)[1] > shown_size(ctx.info)[0] * 1.1:
        return {"kind": "native", "face": None, "screen": None}
    forced = ctx.p("layout", "auto")
    if isinstance(forced, dict) or forced not in (None, "auto"):
        g = forced if isinstance(forced, dict) else {"kind": forced, "face": ctx.p("face")}
    else:
        from .layout import guess
        g = guess(ctx, start, end, tag)
    kind = g.get("kind")
    if kind in ("stack", "face", "native"):
        return {"kind": kind, "face": g.get("face"), "screen": g.get("screen"), "room": g.get("room", 1.0)}
    prefer = ctx.p("vertical_layout")  # "stack" | "face": the profile's choice for a camera window
    out = {"kind": prefer if kind == "screen_face_window" and prefer in ("stack", "face") else
           TO_9x16.get(kind, "stack"), "face": g.get("face"), "screen": g.get("screen")}
    out["room"] = FACE_ROOM if kind == "face_full" else WINDOW_ROOM
    return out


def _warning(ctx, layout: Dict):
    from ..media.vertical import SOFT_FACE, face_upscale, shown_size

    up = face_upscale(shown_size(ctx.info), layout)
    if up and up > SOFT_FACE:
        return "мягкое лицо: окно камеры растянуто в {:.1f} раза — лицо будет нерезким".format(up)
    return None


def _stretches(ctx) -> List[Dict]:
    limit = float(ctx.p("max_seconds", 60))
    if length(ctx.keep) <= limit:
        return [{"id": "v01", "start": ctx.keep[0][0], "end": ctx.keep[-1][1], "said": ""}]
    from .clips import candidates

    lo, hi = (ctx.p("clips") or [5, 10])[:2]
    items = candidates(mapped(spoken(ctx.transcript()), [(0.0, ctx.info["duration"])]), max_s=limit,
                       most=int(hi))
    if len(items) < int(lo):
        ctx.note("Нашлось {} отрывков вместо {}–{}: запись короткая или речь редкая".format(len(items), lo, hi))
    ok, data = ctx.ask("clips", "Отрывки по рубрике (баллы из 10): впишите в chosen id тех, что монтировать.",
                       {"items": items, "chosen": [i["id"] for i in items[:1]]})
    chosen = set(data.get("chosen") or []) if ok else set()
    return [i for i in data.get("items", []) if i["id"] in chosen]


def plan_vertical(ctx) -> None:
    pieces = []
    for st in _stretches(ctx):
        keep = intersect(ctx.keep, float(st["start"]), float(st["end"]))
        lay = _layout(ctx, keep[0][0], keep[-1][1], st["id"]) if keep else None
        if not keep:
            continue
        pieces.append({"id": st["id"], "start": keep[0][0], "end": keep[-1][1], "said": st.get("said") or
                       quote(spoken(ctx.transcript())), "layout": lay, "warning": _warning(ctx, lay)})
    from .errors import PipelineError

    if not pieces:
        raise PipelineError("Нечего монтировать: ни один отрывок не выбран.")
    ok, data = ctx.ask("vertical", "План 9:16: у каждого куска раскладка layout.kind — stack (экран сверху, "
                       "лицо снизу), face (лицо крупно), native (как снято). Так делаем?", {"pieces": pieces})
    if not ok:
        raise PipelineError("План вертикали не утверждён — ролик не собран.")
    ctx.pieces = []
    for p in data.get("pieces", []):
        if p.get("warning"):
            ctx.note("{}: {}".format(p["id"], p["warning"]))
        ctx.pieces.append(dict(p, keep=intersect(ctx.keep, float(p["start"]), float(p["end"]))))
