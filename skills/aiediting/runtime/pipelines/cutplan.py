"""What a lesson keeps: speech runs with a margin, minus hesitations and approved earlier takes."""
from __future__ import annotations

from typing import Dict, List

from .kept import alive, kept_words
from .timeline import Span, length, merge, removed, subtract
from .words import norm, spoken

SLIVER = 0.3  # a kept bit this short with no word in it is just leftover silence


def plan_speech(ctx) -> None:
    """Speech by loudness; a format with `word_gap` (the vertical) keeps only where words are said."""
    from ..media import speech_spans
    from .wordcut import plan_words

    spans = speech_spans(ctx.src, gap=float(ctx.p("gap", 0.5)), pad=float(ctx.p("pad", 0.12)),
                         db=float(ctx.p("db", -30)))
    if ctx.p("word_gap") is None:  # cut by words, a word cannot fall out: its times decide what stays
        ctx.loud = spans
    ctx.keep = plan_words(ctx, spans) or ctx.keep


def _fillers(ctx, words) -> List[Dict]:
    listed = {norm(t) for t in ctx.p("fillers_cut", [])}
    if not listed:
        return []
    keep = {norm(t) for t in ctx.p("fillers_keep", [])}
    return [w for w in words if norm(w["text"]) not in keep
            and (w.get("type") == "filler" or norm(w["text"]) in listed)]


def _why(piece: Span, fillers: List[Dict], takes: List[Dict]) -> str:
    a, b = piece
    for t in takes:
        if t["drop"][0] < b and a < t["drop"][1]:
            return "дубль: «{}»".format(t["said"])
    for w in fillers:
        if w["start"] < b and a < w["end"]:
            return "запинка «{}»".format(w["text"])
    return "пауза"


def _anchors(words: List[Dict], fillers: List[Dict], takes: List[Dict]) -> List[float]:
    """Middles of the words that stay: not a cut hesitation, not a word of a dropped take."""
    live = kept_words([w for w in words if w not in fillers], subtract([(0.0, 1e9)], [tuple(t["drop"]) for t in takes]))
    return [(w["start"] + w["end"]) / 2.0 for w in live]


def plan_cut(ctx) -> None:
    from .retakes import plan_retakes

    needs_words = ctx.p("fillers_cut") or ctx.p("retakes") in ("last_good", True)
    words = spoken(ctx.transcript()) if needs_words else []
    fillers = _fillers(ctx, words)
    takes = plan_retakes(ctx, words) if ctx.p("retakes") in ("last_good", True) else []
    cuts = [(w["start"], w["end"]) for w in fillers] + [tuple(t["drop"]) for t in takes]
    keep = subtract(ctx.keep, cuts)
    mids = _anchors(words, fillers, takes)
    keep = [(a, b) for a, b in keep if b - a >= SLIVER or any(alive(m, [(a, b)]) for m in mids)]
    ctx.keep = merge(keep) or ctx.keep
    total = ctx.info["duration"]
    ctx.report["cuts"] = [{"start": round(a, 3), "end": round(b, 3), "why": _why((a, b), fillers, takes)}
                          for a, b in removed(ctx.keep, total) if b - a >= 0.01]
    ctx.report["kept_seconds"] = round(length(ctx.keep), 3)
