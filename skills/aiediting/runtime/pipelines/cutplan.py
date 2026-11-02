"""What a lesson keeps: speech runs with a margin, minus hesitations and approved earlier takes."""
from __future__ import annotations

from typing import Dict, List

from .kept import alive, kept_words
from .timeline import Span, length, merge, removed, subtract
from .words import norm, spoken

SLIVER = 0.3  # a kept bit this short with no word in it is just leftover silence
LONGEST_NOISE = 3.0  # seconds: a longer loud piece without words is left in, it may be a demo with its sound
NEAR_LOST = 1.5      # seconds around a word that lost its place: a loud piece there may be that word


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


def _why(piece: Span, fillers: List[Dict], takes: List[Dict], unvoiced=()) -> str:
    a, b = piece
    for t in takes:
        if t["drop"][0] < b and a < t["drop"][1]:
            return "{}: «{}»".format(t.get("why", "дубль"), t["said"])
    for w in fillers:
        if w["start"] < b and a < w["end"]:
            return "запинка «{}»".format(w["text"])
    return "звук без слов" if any(x < b and a < y for x, y in unvoiced) else "пауза"


def _anchors(words: List[Dict], fillers: List[Dict], takes: List[Dict]) -> List[float]:
    """Middles of the words that stay: not a cut hesitation, not a word of a dropped take."""
    live = kept_words([w for w in words if w not in fillers], subtract([(0.0, 1e9)], [tuple(t["drop"]) for t in takes]))
    return [(w["start"] + w["end"]) / 2.0 for w in live]


def _voiced(keep: List[Span], words: List[Dict], fillers: List[Dict], takes: List[Dict]):
    """(`keep` without loud pieces where nobody says anything, the pieces taken out): a click, a breath.

    A long piece may be a demo with its own sound; a piece near a word that lost its place may be that word."""
    drops = [tuple(t["drop"]) for t in takes]
    said = [w for w in words if w not in fillers and not any(a <= (w["start"] + w["end"]) / 2.0 < b for a, b in drops)]
    lost = [w for w in said if not alive((w["start"] + w["end"]) / 2.0, keep)]
    stay, out = [], []
    for a, b in keep:
        if any(w["start"] < b and a < w["end"] for w in said) or b - a > LONGEST_NOISE or \
                any(a - NEAR_LOST < w["start"] < b + NEAR_LOST for w in lost):
            stay.append((a, b))
        else:
            out.append((a, b))
    return stay, out


def plan_cut(ctx) -> None:
    from .editing import plan_editing
    from .retakes import plan_retakes
    from .seams import tidy, widened

    needs_words = ctx.p("fillers_cut") or ctx.p("wordless") == "cut" or ctx.p("editor") or \
        ctx.p("retakes") in ("last_good", True)
    words = spoken(ctx.transcript()) if needs_words else []
    fillers = _fillers(ctx, words)
    takes = plan_retakes(ctx, words) if ctx.p("retakes") in ("last_good", True) else []
    takes += plan_editing(ctx, words, takes)
    takes = widened(words, takes)
    tidy(words, takes)
    cuts =[(w["start"], w["end"]) for w in fillers] + [tuple(t["drop"]) for t in takes]
    keep = subtract(ctx.keep, cuts)
    mids = _anchors(words, fillers, takes)
    keep = [(a, b) for a, b in keep if b - a >= SLIVER or any(alive(m, [(a, b)]) for m in mids)]
    unvoiced: List[Span] = []
    if ctx.p("wordless") == "cut" and words:
        keep, unvoiced = _voiced(keep, words, fillers, takes)
    ctx.keep = merge(keep) or ctx.keep
    total = ctx.info["duration"]
    ctx.report["cuts"] = [{"start": round(a, 3), "end": round(b, 3), "why": _why((a, b), fillers, takes, unvoiced)}
                          for a, b in removed(ctx.keep, total) if b - a >= 0.01]
    ctx.report["kept_seconds"] = round(length(ctx.keep), 3)
