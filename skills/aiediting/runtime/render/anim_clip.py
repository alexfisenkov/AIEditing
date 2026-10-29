"""animation(): one insert («файлы», «шаги», «список», «число») as a clip with alpha, made by HyperFrames."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

from . import hyperframes
from .anim_page import page
from .anim_spec import box, spec, template_file
from .errors import RenderError


def animation(slot: Dict, design, frame_size: Tuple[int, int], folder, seconds: float) -> Dict:
    """slot = {template, title, items}; the clip lasts `seconds`, entry and exit inside them, no sound.

    Returns {"video": Path (.mov, ProRes 4444 with alpha), "size": (w, h)}; the caller places it.
    """
    template = template_file(design, slot.get("template"))
    if template is None:
        raise RenderError("Нет шаблона анимации «{}» в дизайн-системе (design/animations/)".format(
            slot.get("template")))
    if seconds < 1.0:
        raise RenderError("Анимации «{}» дано {:.2f} с — слишком мало".format(slot.get("template"), seconds))
    s = spec(design)
    frame = tuple(int(v) for v in frame_size)
    size = box(slot, s, frame)
    folder = Path(folder)
    project = page(template, slot, design, s, size, frame[1], seconds, folder / "project")
    clip = hyperframes.render_mov(project, folder / "insert.mov", int(s.get("fps", 30)))
    return {"video": clip, "size": size}
