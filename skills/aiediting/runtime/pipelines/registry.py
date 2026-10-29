"""The steps a profile may name, in the order the pipeline plans them (profile order does not matter).

Names are the runtime functions they stand for (catalog/steps.json), plus `motion` and `verify_words`.
Planning asks every question first; rendering then runs without stopping.
"""
from __future__ import annotations

import importlib
from typing import Callable, Dict, List, Optional


def _lazy(module: str, name: str) -> Callable:
    def call(ctx):
        return getattr(importlib.import_module("." + module, __package__), name)(ctx)
    return call


def _heavy(ctx) -> None:
    for step in ("graphics", "behind_head"):
        if ctx.has(step):
            ctx.note("Шаг «{}» в этой версии не делается (тяжёлый слой HyperFrames/Remotion) — пропущен".format(step))


# name -> planning function or None (a step that only renders, see render.py)
PLAN: Dict[str, Optional[Callable]] = {
    "detect_layout": _lazy("layout", "plan_layout"),
    "find_secrets": _lazy("secrets", "plan_find"),
    "blur_regions": _lazy("secrets", "plan_blur"),
    "speech_spans": _lazy("cutplan", "plan_speech"),
    "cut_spans": _lazy("cutplan", "plan_cut"),
    "motion": _lazy("motion", "plan_motion"),
    "vertical": _lazy("vertical_plan", "plan_vertical"),
    "plate": _lazy("plates", "plan_plates"),
    "animations": _lazy("animations", "plan_animations"),  # after plate: an insert replaces a card
    "overlay_png": None,
    "music": _lazy("music", "plan_music"),
    "write_srt": _lazy("subtitles", "plan_srt"),
    "loudnorm": None,
    "drift_ms": None,
    "verify_words": None,
    "export_platforms": None,
    "graphics": _heavy,
    "behind_head": _heavy,
}

STEPS: List[str] = list(PLAN)


def step_names() -> List[str]:
    return list(STEPS)
