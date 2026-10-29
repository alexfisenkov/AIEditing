"""Fonts: the design system's own files first, then a system font that has Cyrillic."""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import List, Tuple

from .design import load_design
from .errors import RenderError, need


def _system_fonts() -> List[Path]:
    windir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    return [Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/Library/Fonts/Arial Unicode.ttf"),
            windir / "segoeui.ttf", windir / "arial.ttf",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]


def font_file(design, role: str) -> Tuple[Path, bool]:
    """(file, exact) — exact is False when a fallback stands in for the role's own font."""
    d = load_design(design)
    spec = d.get("font", {}).get(role)
    if spec:
        own = Path(d["root"]) / spec.get("file", "")
        if spec.get("file") and own.is_file():
            return own, True
        if spec.get("fallback") and spec["fallback"] != role:
            return font_file(d, spec["fallback"])[0], False
    for path in _system_fonts():
        if path.is_file():
            return path, False
    raise RenderError("Нет шрифта для «{}»: положите .ttf в fonts/ дизайн-системы.".format(role))


def font(design, role: str, weight: str, size: int):
    """A Pillow font of `size` px; variable fonts get the named weight (Medium, Bold...)."""
    image_font = need("PIL.ImageFont")
    path, _exact = font_file(design, role)
    loaded = image_font.truetype(io.BytesIO(path.read_bytes()), max(6, int(size)))
    try:
        loaded.set_variation_by_name(weight)
    except (OSError, ValueError, AttributeError):
        pass  # a static font: its own weight it is
    return loaded
