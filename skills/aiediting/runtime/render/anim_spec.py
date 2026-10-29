"""The look of an animated insert from the design tokens: `video.animation` over `video.card`, sizes in px.

Whatever a format's tokens lack comes from REFERENCE (the Chrome & Graphite values), so a design of
one's own never breaks an insert. Sizes are shares of the frame's short side and the width a share of
its long side: on 16:9 and on 9:16 the insert is the same, readable size.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Optional, Tuple

from .design import default_design, load_design

TEMPLATES = {"файлы": "files", "шаги": "steps", "список": "list", "число": "number"}
REFERENCE = {"font": "display", "weight": "Bold", "size": 0.034, "body_font": "text", "body_weight": "Regular",
             "mono_font": "mono", "body_size": 0.026, "number_size": 0.1, "row": 1.9, "pad": 0.028,
             "bg": "#202123", "bg_alpha": 0.82, "fg": "#FFFFFF", "body_fg": "#C7C9CC", "line": "#C7C9CC",
             "line_alpha": 0.22, "radius": 0.02, "where": "top-left", "margin": 0.045, "max_width": 0.3,
             "enter": 0.5, "exit": 0.3, "stagger": 0.12, "fps": 30}
NUMBERS = ("size", "body_size", "number_size", "row", "pad", "bg_alpha", "line_alpha", "margin", "max_width",
           "enter", "exit", "stagger")
WEIGHTS = {"Thin": 100, "Light": 300, "Regular": 400, "Medium": 500, "SemiBold": 600, "Bold": 700, "Black": 900}


def spec(design) -> Dict:
    """Reference values, then the card's, then the animation's own; a broken number falls back too."""
    video = load_design(design).get("video") or {}
    own = dict(video.get("card") or {}, **(video.get("animation") or {}))
    s = dict(REFERENCE, **{k: v for k, v in own.items() if k in REFERENCE})
    for key in NUMBERS + ("fps",):
        try:
            s[key] = float(s[key]) if key != "fps" else int(s[key])
        except (TypeError, ValueError):
            s[key] = REFERENCE[key]
    return s


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


def unit(frame: Tuple[int, int]) -> int:
    """What size shares are taken of: the short side of the frame."""
    return min(int(frame[0]), int(frame[1]))


def _even(v: float) -> int:
    return int(math.ceil(v / 2.0) * 2)


def box(slot: Dict, s: Dict, frame: Tuple[int, int]) -> Tuple[int, int]:
    """Width × height: a share of the long side (never past 90 % of the width), rows by the points."""
    w, h = frame
    u = unit(frame)
    pad, title, body = s["pad"] * u, s["size"] * u, s["body_size"] * u
    items = [i for i in slot.get("items", []) if str(i).strip()]
    if template_id(slot.get("template")) == "number":
        tall = 2 * pad + s["number_size"] * u * 1.15 + body * 1.4 * max(1, min(2, len(items)))
    else:
        head = title * 1.25 + body * 0.6 if str(slot.get("title", "")).strip() else 0
        tall = 2 * pad + head + body * s["row"] * max(1, len(items))
    return _even(min(s["max_width"] * max(w, h), 0.9 * w)), _even(min(tall, 0.7 * h))
