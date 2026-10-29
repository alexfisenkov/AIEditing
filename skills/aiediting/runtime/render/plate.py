"""plate(): one element of the design layer as a frame-sized transparent PNG, ready to lay over video."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .design import load_design, spec
from .fonts import font
from .panel import block_size, draw, wrap
from .place import SPOTS, place
from .errors import RenderError

KINDS = ("chapter", "caption", "card")


def _rows(d: Dict, s: Dict, kind: str, text: str, height: int, max_px: int) -> Tuple[List, List[str], int]:
    size = int(s["size"] * height)
    main = font(d, s["font"], s["weight"], size)
    if kind != "card":
        lines = wrap(main, text, max_px, int(s.get("max_lines", 1)))
        return [(main, line) for line in lines], [s["fg"]] * len(lines), int(0.18 * size)
    title, _, body = text.partition("\n")
    rows = [(main, line) for line in wrap(main, title, max_px, 2)]
    colors = [s["fg"]] * len(rows)
    if body.strip():
        small = font(d, s["body_font"], s["body_weight"], int(s["body_size"] * height))
        lines = wrap(small, body, max_px, int(s.get("max_lines", 3)))
        rows += [(small, line) for line in lines]
        colors += [s.get("body_fg", s["fg"])] * len(lines)
    return rows, colors, int(0.3 * size)


def plate(text: str, design, kind: str, frame_size=(1920, 1080), where: Optional[str] = None,
          out=None, variant=None) -> Path:
    """Chapter plate, caption or card ("Title\\nbody") as a PNG of frame_size; position is baked in.

    where: bottom | top | center | top-left | top-right | bottom-left | bottom-right.
    """
    if kind not in KINDS:
        raise RenderError("Неизвестный элемент «{}»: {}".format(kind, ", ".join(KINDS)))
    d = load_design(design)
    s = spec(d, kind, variant)
    spot = where or s["where"]
    if spot not in SPOTS:
        raise RenderError("Неизвестное место «{}»: {}".format(spot, ", ".join(SPOTS)))
    width, height = (int(v) for v in frame_size)
    size = int(s["size"] * height)
    pad = (int(s["pad_x"] * size), int(s["pad_y"] * size))
    rows, colors, gap = _rows(d, s, kind, " ".join(text.split(" ")).strip(), height,
                              int(s.get("max_width", 0.8) * width) - 2 * pad[0])
    text_w, text_h = block_size(rows, gap)
    box_w, box_h = text_w + 2 * pad[0], text_h + 2 * pad[1]
    radius = box_h // 2 if s.get("radius") == "pill" else int(float(s.get("radius", 0)) * height)
    x, y = place(d, (width, height), (box_w, box_h), spot, s["margin"])
    layer = draw(d, s, (width, height), (x, y, box_w, box_h), pad, rows, colors, gap, radius)
    if out is None:
        handle, name = tempfile.mkstemp(prefix="aiediting-{}-".format(kind), suffix=".png")
        os.close(handle)
        out = name
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    layer.save(out)
    return out
