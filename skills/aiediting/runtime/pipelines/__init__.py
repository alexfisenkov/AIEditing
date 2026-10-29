"""Format pipelines: a profile names the steps, the pipeline plans with the person, then edits.

    run(src, profile, outdir, approve, screen=None) -> Report
    Report = {"output", "srt", "cuts", "blurred", "fixes", "drift_ms", "outputs", "exports",
              "chapters", "clips", "motion", "words_lost", "notes", "decisions", "report"}
`look` and `render` are imported lazily, inside the steps that need them.
"""
from .errors import PipelineError
from .registry import STEPS, step_names
from .run import run

__all__ = ["PipelineError", "STEPS", "run", "step_names"]
