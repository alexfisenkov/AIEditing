"""The look of an animated insert from the design tokens: `video.animation` over `video.card`, sizes in px."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Optional, Tuple

from .design import default_design, load_design

TEMPLATES = {"файлы": "files", "шаги": "steps", "список": "list", "число": "number"}
DEFAULTS = {"mono_font": "mono", "pad": 0.028, "row": 1.9, "number_size": 0.1, "enter": 0.5, "exit": 0.3,
            "stagger": 0.12, "fps": 30, "max_width": 0.3}
WEIGHTS = {"Thin": 100, "Light": 300, "Regular": 400, "Medium": 500, "SemiBold": 600, "Bold": 700, "Black": 900}


def spec(design) -> Dict:
    """Card settings, then the animation's own: an insert stands where a card would."""
    video = load_design(design)["video"]
    return dict(DEFAULTS, **dict(video.get("card", {}), **video.get("animation", {})))


def template_id(name: str) -> Optional[str]:
    """Template file id for a name the person sees («файлы») or its English id (files)."""
    name = str(name or "").strip().lower()
    return TEMPLATES.get(name) or (name if name in TEMPLATES.values() else None)


def template_file(design, name: str) -> Optional[Path]:
    """`animations/<id>.html` of the format's design, else of the bundled default; None if neither has it."""
    tid = template_id(name)
    if tid is None:
        return None
    for root in (Path(load_design(design)["root"]), default_design()):
        path = root / "animations" / (tid + ".html")
        if path.is_file():
            return path
    return None


def _even(v: float) -> int:
    return int(math.ceil(v / 2.0) * 2)


def box(slot: Dict, s: Dict, frame: Tuple[int, int]) -> Tuple[int, int]:
    """Width × height of the insert: the card's width share, rows by the number of items."""
    w, h = frame
    pad, title, body = s["pad"] * h, s["size"] * h, s["body_size"] * h
    items = [i for i in slot.get("items", []) if str(i).strip()]
    if template_id(slot.get("template")) == "number":
        tall = 2 * pad + s["number_size"] * h * 1.15 + body * 1.4 * max(1, min(2, len(items)))
    else:
        head = title * 1.25 + body * 0.6 if str(slot.get("title", "")).strip() else 0
        tall = 2 * pad + head + body * s["row"] * max(1, len(items))
    return _even(s["max_width"] * w), _even(min(tall, 0.7 * h))
