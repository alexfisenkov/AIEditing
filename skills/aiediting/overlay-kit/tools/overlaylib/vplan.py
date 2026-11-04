"""What `vertical-check` and `vertical-final` both start from: the set is in place, the data and the scenes agree, the types hold."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import remotion, vinit, vspans
from .common import ToolError, work_dir
from .media import duration_of


def load_plan(work_arg: str, wanted: Optional[List[str]]) -> Tuple[Path, Dict, List[str]]:
    """(working folder, spans.json, clips to handle). Every reason to stop is a ToolError with what to do."""
    work = work_dir(work_arg)
    remotion.ready(work)
    vertical = work / "src" / "vertical"
    if not (vertical / "VRoot.tsx").is_file():
        raise ToolError("В {} нет набора для вертикали. Сначала: overlay.py vertical-init {}".format(work, work))
    data = vspans.load(vertical / "spans.json")
    vinit.verify_source(work, data)
    scenes = vinit.write_clips_index(work)
    vinit.install_helper(work)
    spans = vspans.clip_ids(data)
    no_scene = [c for c in spans if c not in scenes]
    no_spans = [c for c in scenes if c not in spans]
    if no_scene or no_spans:
        raise ToolError("spans.json и сцены не сходятся. Клипы без сцены: {}. Сцены без клипа в spans.json: {}.".format(
            ", ".join(no_scene) or "нет", ", ".join(no_spans) or "нет"))
    ids = list(dict.fromkeys(wanted or spans))
    unknown = [c for c in ids if c not in spans]
    if unknown:
        raise ToolError("Нет клипа {}. Есть: {}.".format(", ".join(unknown), ", ".join(spans)))
    vspans.check_against_source(data, duration_of(work / "public" / "clips" / "source.mp4"), ids)
    return work, data, ids


def typecheck(work: Path) -> None:
    remotion.typecheck(work)
