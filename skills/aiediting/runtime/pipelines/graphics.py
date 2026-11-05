"""The graphics step: the finished video and its words in seconds of that video; the scenes go on top of it.

The model writes the scenes (`design/overlay-kit/README.md`), so the pipeline only hands over what is measured.
Time is always the finished video's, which is why this works the same with cuts and speed as without them.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .speed import rate_of, scaled_words
from .words import KEPT, cache_key, mapped, spoken

WORDS = "слова-таймкоды.txt"
WIDE = 0.02     # how far from 16:9 a frame may be, the same as the kit's check
HOLE = 6.0      # recognisers lose stretches of long recordings: a wordless stretch this long is looked at
SPOKEN = 0.4    # the part of it that has sound: more, and it is a lost stretch rather than a real pause
AROUND = 12.0   # seconds of context around a lost stretch, so the recogniser hears whole sentences


def plan_graphics(ctx) -> None:
    from ..media.vertical import shown_size

    w, h = shown_size(ctx.info)
    if ctx.has("vertical") or not h or abs(w / h - 16 / 9) >= WIDE:
        ctx.note("Графика рассчитана на кадр 16:9, здесь кадр {}x{}: её слой не делается".format(w, h))
        ctx.steps.remove("graphics")
        if ctx.p("lufs") is not None and not ctx.has("loudnorm"):  # the kit's `final` would have set it
            ctx.steps.append("loudnorm")
        return
    complete_words(ctx)


def complete_words(ctx) -> None:
    """Local whisper loses stretches of a long recording: they are heard again and join the words."""
    words = ctx.transcript()
    if ctx.profile.get("asr", {}).get("provider") == "whispercpp":
        words["words"] = sorted(words.get("words", []) + _lost_words(ctx, words), key=lambda w: w["start"])


def _holes(words: List[Dict], total: float) -> List[List[float]]:
    edges = [0.0] + [x for w in words for x in (w["start"], w["end"])] + [total]
    pairs = zip(edges[0::2], edges[1::2])
    return [[a, b] for a, b in pairs if b - a > HOLE]


def _sounding(loud, a: float, b: float) -> float:
    return sum(max(0.0, min(y, b) - max(x, a)) for x, y in loud) / (b - a)


def _lost_words(ctx, transcript: Dict) -> List[Dict]:
    """Whisper on long files drops stretches of speech; each one is heard again by itself. Free, so local only."""
    from .. import asr
    from ..media import cut_spans, speech_spans

    # a run stopped by a question comes back here: heard once is enough, for this very recording and recogniser
    if not ctx.info.get("has_audio", True):
        return []
    kept = ctx.outdir / KEPT / "дочитано-{}.json".format(cache_key(ctx.src, ctx.profile["asr"]))
    if kept.is_file():
        found = json.loads(kept.read_text(encoding="utf-8"))
        if found:
            ctx.note("Распознавание теряло куски записи, они дочитаны отдельно: {} слов".format(len(found)))
        return found
    loud = ctx.loud if ctx.loud is not None else speech_spans(ctx.src)
    found: List[Dict] = []
    for n, (a, b) in enumerate(_holes(spoken(transcript), ctx.info["duration"])):
        if _sounding(loud, a, b) <= SPOKEN:
            continue
        start = max(0.0, a - AROUND)
        ctx.work.mkdir(parents=True, exist_ok=True)
        part = cut_spans(ctx.src, [(start, min(ctx.info["duration"], b + AROUND))], ctx.work / "дочитка-{}.mp4".format(n))
        again = spoken(asr.transcribe(part, dict(ctx.profile["asr"], language=ctx.profile.get("language") or "")))
        fresh = [dict(w, start=w["start"] + start, end=w["end"] + start) for w in again]
        inside = [w for w in fresh if a <= w["start"] < b]
        found += inside
        if inside:
            ctx.note("Распознавание потеряло кусок {:.0f}–{:.0f} с, дочитан отдельно".format(a, b))
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_text(json.dumps(found, ensure_ascii=False), encoding="utf-8")
    return found


def _finished_words(ctx) -> List[Dict]:
    """The words of the finished video. Local whisper places words too loosely for a cut to carry them over: a stretched
    word falls into a cut and is lost though it is heard, so a video with cuts is heard again, and the `.srt` follows. It is
    heard before the speed-up, because a recogniser hears sped-up speech worse and makes up repeats. With nothing cut there
    is nothing to carry through: the words of the first hearing, at the new speed. A paid recogniser's times are exact: its
    words are mapped through the cuts."""
    rate = rate_of(ctx.p("speed", 1.0))
    carried = scaled_words(mapped(spoken(ctx.transcript()), ctx.keep), rate)
    if ctx.profile.get("asr", {}).get("provider") != "whispercpp" or len(ctx.keep) == 1:
        return carried
    from ..media import probe
    from .subtitles import write_final
    from .words import recognise

    final = Path(ctx.report["outputs"][0]["video"])
    slow = getattr(ctx, "before_speed", None)
    words = scaled_words(spoken(recognise(ctx, media=slow or final)), rate if slow else 1.0)
    # what this second hearing lost, the first one (with its stretches heard again) still has
    holes = _holes(words, probe(final)["duration"])
    words = sorted(words + [w for w in carried if any(a <= w["start"] < b for a, b in holes)], key=lambda w: w["start"])
    if ctx.has("write_srt"):
        ctx.report["fixes"] = write_final(ctx, words, final.with_suffix(".srt"))
    return words


def write_words(ctx) -> Path:
    """`<issue folder>/слова-таймкоды.txt`: what is said and when, in seconds of the finished video, the same text as the `.srt`."""
    from .subtitles import write_words_file

    words = _finished_words(ctx)
    path = ctx.outdir / WORDS
    write_words_file(path, words, ctx.srt_glossary, getattr(ctx, "srt_corrections", None))
    ctx.note("Графика ещё не наложена: это делается по design/overlay-kit/README.md поверх этого видео и {}".format(WORDS))
    return path
