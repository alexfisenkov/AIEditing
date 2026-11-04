"""Plan of a 9:16 video: shot vertically / reframed from horizontal / cut from a long recording.

The plan (stretches, layout of each, soft-face warnings) goes to the person before anything is made.
"""
from __future__ import annotations

from typing import Dict, List

from .timeline import intersect, subtract
from .vertical_source import stretches
from .words import quote, spoken

OWN = ("headline", "name", "drop")  # what a clip brings from the person's answer into its piece
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
        return {"kind": kind, "face": g.get("face"), "screen": g.get("screen"), "room": g.get("room", 1.0),
                "background": g.get("background")}
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


def _kept(ctx, item: Dict) -> List:
    """What stays of a stretch: the format's cut, minus `drop`, the sentences that do not stand alone in a clip."""
    keep = intersect(ctx.keep, float(item["start"]), float(item["end"]))
    return subtract(keep, [(float(a), float(b)) for a, b in item.get("drop") or []])


def plan_vertical(ctx) -> None:
    pieces = []
    for st in stretches(ctx):
        keep = _kept(ctx, st)
        lay = _layout(ctx, keep[0][0], keep[-1][1], st["id"]) if keep else None
        if not keep:
            continue
        pieces.append(dict({k: st[k] for k in OWN if st.get(k)}, id=st["id"], start=keep[0][0], end=keep[-1][1],
                           said=st.get("said") or quote(spoken(ctx.transcript())), layout=lay,
                           warning=_warning(ctx, lay)))
    from .errors import PipelineError

    if not pieces:
        raise PipelineError("Нечего монтировать: ни один отрывок не выбран.")
    ok, data = ctx.ask("vertical", "План 9:16: у каждого куска раскладка layout.kind — stack (экран сверху, "
                       "лицо снизу), face (лицо крупно), native (как снято). Так делаем?", {"pieces": pieces})
    if not ok:
        raise PipelineError("План вертикали не утверждён — ролик не собран.")
    ctx.pieces = []
    from .bands import name_key

    # one file on the disk: the second clip would silently take the place of the first
    keys = [name_key(p["name"]) for p in data.get("pieces", []) if p.get("name")]
    same = sorted({p["name"] for p in data.get("pieces", []) if p.get("name") and keys.count(name_key(p["name"])) > 1})
    if same:
        raise PipelineError("У двух отрывков одно имя файла: {}".format(", ".join(same)))
    for p in data.get("pieces", []):
        if p.get("warning"):
            ctx.note("{}: {}".format(p["id"], p["warning"]))
        ctx.pieces.append(dict(p, keep=_kept(ctx, p)))
