"""The reedit step: a long 16:9 video re-edited into 9:16 clips by the overlay kit's vertical mode.

The model makes the clips (`design/overlay-kit/vertical.md`), so the pipeline only agrees which stretches they are and
hands over what is measured: those stretches and the words, both in seconds of the source. It makes no video itself.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from .bands import clean_name, name_key
from .errors import PipelineError
from .graphics import WIDE, WORDS, complete_words
from .speed import rate_of
from .timeline import length
from .vertical_plan import OWN, _kept
from .vertical_source import stretches
from .words import spoken

SPANS = "отрывки.json"
APART = ("vertical", "bands", "graphics", "find_secrets", "blur_regions")  # each works on a video the pipeline makes; here it makes none
PARTS = ("lead", "before", "word", "after")


def no_call(ctx) -> bool:
    """`params.cta_parts: null` is the person's «без призыва». A missing or blank one is a question nobody answered."""
    return "cta_parts" in ctx.params and ctx.params["cta_parts"] is None


def call_times(ctx) -> Tuple[float, float]:
    """(cta_lead, cta_tail): how long before the end of the speech the call comes and how long it stands after it."""
    if no_call(ctx):
        return 0.0, 0.0
    return float(ctx.p("cta_lead", 2.0)), float(ctx.p("cta_tail", 4.0))


def _refuse(ctx) -> None:
    """What cannot work is refused before the questions and the recognition."""
    from ..media.vertical import shown_size

    together = [s for s in APART if ctx.has(s)]
    if together:
        raise PipelineError("Перемонтаж — отдельный путь: шаг reedit не ставят вместе с {}.".format(", ".join(together)))
    w, h = shown_size(ctx.info)
    if not h or abs(w / h - 16 / 9) >= WIDE:
        raise PipelineError("Перемонтаж делается из ролика 16:9, здесь кадр {}x{}.".format(w, h))
    parts = ctx.params.get("cta_parts")
    if no_call(ctx):
        return
    if not isinstance(parts, dict) or not any(str(parts.get(k) or "").strip() for k in PARTS):
        raise PipelineError("Призыв не решён: задайте params.cta_parts (lead, before, word, after) словами самого человека, "
                            "а если он сказал «без призыва» — params.cta_parts=null.")


def _pieces(ctx) -> List[Dict]:
    """The clips of the answer, renumbered: the kit's scene of a clip is the file c<N>.tsx, whatever the answer called it."""
    pieces = []
    for item in stretches(ctx):
        keep = _kept(ctx, item)
        if keep:
            pieces.append(dict({k: item[k] for k in OWN if item.get(k)}, id="c{}".format(len(pieces) + 1), start=keep[0][0],
                               end=keep[-1][1], said=item.get("said") or "", keep=keep))
    if not pieces:
        raise PipelineError("Нечего монтировать: ни один отрывок не выбран.")
    return pieces


def _names(ctx, pieces: List[Dict]) -> Dict[str, str]:
    names = {p["id"]: clean_name(p.get("name") or "") or clean_name("{}-{}".format(ctx.src.stem, p["id"])) for p in pieces}
    keys = [name_key(n) for n in names.values()]  # one file on the disk: the second clip would take the place of the first
    same = sorted({n for n in names.values() if keys.count(name_key(n)) > 1})
    if same:
        raise PipelineError("У двух отрывков одно имя файла: {}".format(", ".join(same)))
    return names


def plan_reedit(ctx) -> None:
    _refuse(ctx)
    complete_words(ctx)
    pieces = _pieces(ctx)
    _names(ctx, pieces)
    ctx.pieces = pieces


def _spans(ctx) -> Dict:
    lead, tail = call_times(ctx)
    parts = ctx.p("cta_parts", {})
    return {"rate": rate_of(ctx.p("speed", 1.0)), "cta_lead": lead, "cta_tail": tail,
            "cta": None if no_call(ctx) else {k: str(parts.get(k) or "") for k in PARTS},
            "safe": str(ctx.p("safe", "reels")), "source_seconds": round(float(ctx.info["duration"]), 3),
            "spans": {p["id"]: [[round(a, 3), round(b, 3)] for a, b in p["keep"]] for p in ctx.pieces},
            "names": _names(ctx, ctx.pieces)}


def _notes(ctx, spans: Dict) -> None:
    rate, already = spans["rate"], float(ctx.p("source_speed", 1.0))
    if rate != 1.0 or already != 1.0:
        ctx.note("Речь выйдет на {:.2f}: исходник уже ускорен в {:g}, к файлу ещё {:g}".format(rate * already, already, rate))
    for piece in ctx.pieces:
        total = length(piece["keep"]) / rate + spans["cta_tail"]
        if total > float(ctx.p("max_seconds", 60)):
            ctx.note("{}: готовый ролик выйдет на {:.0f} с вместе с хвостом, больше params.max_seconds".format(piece["id"], total))
    if ctx.p("cta") and spans["cta"] is not None and not spans["cta"]["word"]:
        ctx.note("В params.cta_parts нет слова, которое пишет зритель (word), а в params.cta призыв есть: сверьте их")
    if spans["cta"] is None:
        ctx.note("Ролики без призыва: так решил человек")


def hand_over(ctx) -> Path:
    """`<issue folder>/отрывки.json` and `слова-таймкоды.txt`: what the model builds the clips from."""
    spans = _spans(ctx)
    path = ctx.outdir / SPANS
    path.write_text(json.dumps(spans, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    words = spoken(ctx.transcript())
    (ctx.outdir / WORDS).write_text("".join("{:7.2f} {}\n".format(w["start"], str(w["text"]).strip()) for w in words), encoding="utf-8")
    _notes(ctx, spans)
    covers = int(ctx.p("covers", 0))
    ctx.report["handover"] = ("Отрывки согласованы ({}), ролики ещё не собраны{}: они делаются по design/overlay-kit/vertical.md "
                              "из {} и {}".format(len(ctx.pieces), ", обложки тоже ({})".format(covers) if covers else "", SPANS, WORDS))
    ctx.note(ctx.report["handover"])
    return path
