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
    for name in STEPS:
        if ctx.has(name) and PLAN[name] is not None:
            PLAN[name](ctx)
    from .render import render_piece

    pieces = ctx.pieces or [{"id": None, "keep": ctx.keep, "layout": None}]
    ctx.report["outputs"] = [render_piece(ctx, piece) for piece in pieces]
    if ctx.has("graphics") and not ctx.has("vertical"):
        from .graphics import write_words

        write_words(ctx)
    from .report import finish

    report = finish(ctx)
    shutil.rmtree(str(ctx.work), ignore_errors=True)
    return report
