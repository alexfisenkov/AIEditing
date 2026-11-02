"""The sidecar .srt: brand fixes by the profile glossary, then a proofreading question to the person."""
from __future__ import annotations

from typing import Dict

from .speed import rate_of, scaled_words
from .words import mapped, spoken

QUESTION = ("Вычитайте субтитры (draft): ослышки, произношение, бренды, перевод. Исправления — в replace "
            "как {\"как услышано\": \"как надо\"}; они попадут в .srt и в отчёт.")


def plan_srt(ctx) -> None:
    from ..media import write_srt

    ctx.srt_glossary = dict(ctx.p("glossary", {}) or {})
    words = mapped(ctx.transcript().get("words", []), ctx.keep)
    draft = ctx.work / "черновик.srt"
    fixes = write_srt({"words": words}, draft, ctx.srt_glossary)
    ok, data = ctx.ask("srt", QUESTION, {"draft": str(draft), "fixes": fixes, "replace": {}})
    if ok:
        ctx.srt_glossary.update({str(k): str(v) for k, v in (data.get("replace") or {}).items() if k})


def write_piece_srt(ctx, keep, out) -> Dict:
    from ..media import write_srt

    words = scaled_words(mapped(ctx.transcript().get("words", []), keep), rate_of(ctx.p("speed", 1.0)))
    fixes = write_srt({"words": words}, out, ctx.srt_glossary)
    return {"path": out, "fixes": fixes, "words": len(spoken({"words": words}))}
