"""Which stretches of the source become 9:16 videos: the whole recording, or clips picked from a long one."""
from __future__ import annotations

from typing import Dict, List

from .errors import PipelineError
from .timeline import length
from .words import mapped, spoken

MODES = ("auto", "native", "clips")


def is_native(ctx) -> bool:
    """True when the recording is cut whole, as long as it is: shot vertically (auto), or the profile says so."""
    mode = ctx.p("vertical_source", "auto")
    if mode not in MODES:
        raise PipelineError("params.vertical_source: {!r}; допустимо: {}".format(mode, ", ".join(MODES)))
    if mode != "auto":
        return mode == "native"
    from ..media.vertical import shown_size

    w, h = shown_size(ctx.info)
    forced = ctx.p("layout", "auto")
    kind = forced.get("kind") if isinstance(forced, dict) else forced
    return h > w * 1.1 or kind in ("vertical", "native")


def _whole(ctx) -> List[Dict]:
    return [{"id": "v01", "start": ctx.keep[0][0], "end": ctx.keep[-1][1], "said": ""}]


def _with_margins(ctx, item: Dict) -> Dict:
    """In a format cut by words a picked clip keeps the first and last sounds its words keep inside the speech."""
    if ctx.p("word_gap") is None:
        return item
    from .seams import clip_edges
    from .wordcut import LEAD, TAIL

    start, end = clip_edges(spoken(ctx.transcript()), float(item["start"]), float(item["end"]),
                            float(ctx.p("word_lead", LEAD)), float(ctx.p("word_tail", TAIL)))
    return dict(item, start=start, end=end)


def stretches(ctx) -> List[Dict]:
    from .speed import rate_of

    seconds = float(ctx.p("max_seconds", 60))  # of the whole finished clip, not of the source
    if ctx.has("reedit"):  # its clip ends on the tail of the call, which is no speech
        from .reedit import call_times

        seconds = max(1.0, seconds - call_times(ctx)[1])
    limit = seconds * rate_of(ctx.p("speed", 1.0))
    if is_native(ctx) or (length(ctx.keep) <= limit and not ctx.has("bands")):  # with fields a clip needs its headline
        return _whole(ctx)
    from .clips import candidates

    lo, hi = (ctx.p("clips") or [5, 10])[:2]
    items = candidates(mapped(spoken(ctx.transcript()), [(0.0, ctx.info["duration"])]), max_s=limit,
                       most=int(hi))
    if len(items) < int(lo):
        ctx.note("Нашлось {} отрывков вместо {}–{}: запись короткая или речь редкая".format(len(items), lo, hi))
    ok, data = ctx.ask("clips", "Отрывки по рубрике (баллы из 10): впишите в chosen id тех, что монтировать.",
                       {"items": items, "chosen": [i["id"] for i in items[:1]]})
    chosen = set(data.get("chosen") or []) if ok else set()
    return [_with_margins(ctx, i) for i in data.get("items", []) if i["id"] in chosen]
