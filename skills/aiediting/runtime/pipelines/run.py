"""pipelines.run(): plan with the person first, then render without stopping, then the report."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, Dict, Optional

from .context import Context
from .errors import PipelineError
from .registry import PLAN, STEPS


def run(src, profile: Dict, outdir, approve: Callable[[str, dict], bool], screen: Optional[Path] = None) -> Dict:
    """Edits `src` by `profile["steps"]` into `outdir` (the only place written to); returns the Report.

    approve(key, payload) -> bool is asked before anything irreversible; it may raise to stop the run
    (a file-based approver does) — a later run with the answers resumes from the same questions.
    screen: the screen recording when camera and screen are separate tracks.
    """
    unknown = [s for s in (profile or {}).get("steps", []) if s not in PLAN]
    if unknown:
        raise PipelineError("Неизвестные шаги {}; доступны: {}".format(", ".join(unknown), ", ".join(STEPS)))
    ctx = Context(src, profile, outdir, approve, screen)
    if ctx.src == ctx.outdir or ctx.src.parent == ctx.work:
        raise PipelineError("Папка выпуска не может быть исходником")
    ctx.outdir.mkdir(parents=True, exist_ok=True)
    if ctx.p("denoise"):
        ctx.note("Шумодав в этой версии не делается — звук не очищался")
    if ctx.p("clean_speech") and ctx.src.name != "clean-speech.mov":
        ctx.note("Формат идёт от чистой речи, а на входе {}: записи подрезка и выбор дублей не коснулись. Если это не просьба «как есть», "
                 "сначала clean-speech.mov".format(ctx.src.name))
    for name in STEPS:
        if ctx.has(name) and PLAN[name] is not None:
            PLAN[name](ctx)
    from .render import render_piece

    # with a teaser and no 9:16 clips the teaser is the only result: the whole video is not made again
    whole = [] if ctx.has("teaser") and not ctx.has("vertical") else [{"id": None, "keep": ctx.keep, "layout": None}]
    pieces = ctx.pieces or whole
    if ctx.has("reedit"):  # the model makes these clips; the pipeline hands over what it agreed
        from .reedit import hand_over

        pieces = []
        hand_over(ctx)
    ctx.report["outputs"] = [render_piece(ctx, piece) for piece in pieces]
    if ctx.teaser:
        from .teaser import render_teaser

        ctx.report["outputs"].append(render_teaser(ctx))
    if ctx.has("graphics") and not ctx.has("vertical"):
        from .graphics import write_words

        write_words(ctx)
    from .report import finish
    from .subtitles import keep_final_words

    keep_final_words(ctx)
    report = finish(ctx)
    shutil.rmtree(str(ctx.work), ignore_errors=True)
    return report
