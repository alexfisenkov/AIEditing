"""The fields around a horizontal picture in 9:16: a large headline above it, a call to action right below it."""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .design import color, load_design, spec
from .errors import need
from .fill import text as draw_text
from .fonts import font
from .lines import GLUE, fit


def _headline(layer, d: Dict, s: Dict, words: str, top: int, bottom: int, side: int) -> None:
    width, _ = layer.size
    fnt, lines, step = fit(d, s, words, width - 2 * side, bottom - top, layer.size[1])
    y = top + (bottom - top - step * len(lines)) // 2
    for line in lines:
        shown = line.replace(GLUE, " ")
        draw_text(layer, d, ((width - int(fnt.getlength(shown))) // 2, y), shown, fnt, s.get("fill", "white"))
        y += step


def _runs(d: Dict, s: Dict, line: str, size: int) -> List[Tuple[str, object, str]]:
    """A line as (text, font, colour): the word in «» is what the viewer has to write, so it stands out."""
    runs = []
    for part in re.split(r"(«[^»]+»)", line):
        if part:
            quoted = part.startswith("«")
            runs.append((part, font(d, s["accent_font"], s["accent_weight"], int(size * s.get("accent_scale", 1.0)))
                         if quoted else font(d, s["font"], s["weight"], size), s["accent"] if quoted else s["fg"]))
    return runs


def _cta(layer, d: Dict, s: Dict, words: str, top: int, side: int) -> None:
    pen = need("PIL.ImageDraw")
    width, height = layer.size
    rows = re.split(r"(?<=[?!.])\s+", words.strip(), maxsplit=1)
    size = int(s["size"] * height)
    while True:
        small = font(d, s["font"], s["lead_weight"], size)
        tail = _runs(d, s, rows[-1], size)
        wide = max([small.getlength(rows[0])] * (len(rows) > 1) + [sum(f.getlength(t) for t, f, _ in tail)])
        pad_x, pad_y = int(size * s["pad_x"]), int(size * s["pad_y"])
        if wide + 2 * pad_x <= width - 2 * side or size < 20:
            break
        size -= 1
    step = int(size * s.get("line", 1.3))
    box_w, box_h = int(wide) + 2 * pad_x, step * len(rows) + 2 * pad_y
    x = (width - box_w) // 2
    pen.Draw(layer).rounded_rectangle([x, top, x + box_w - 1, top + box_h - 1], radius=int(s["radius"] * height),
                                      fill=color(d, s["bg"]), outline=color(d, s["line_color"], s["line_alpha"]),
                                      width=2)
    y = top + pad_y
    if len(rows) > 1:
        draw_text(layer, d, ((width - int(small.getlength(rows[0]))) // 2, y), rows[0], small, s["lead_fg"])
        y += step
    at = (width - int(sum(f.getlength(t) for t, f, _ in tail))) // 2
    base = max(f.getmetrics()[0] for _, f, _ in tail)
    for part, fnt, name in tail:
        draw_text(layer, d, (at, y + base - fnt.getmetrics()[0]), part, fnt, name)
        at += int(fnt.getlength(part))


def band(headline: str, cta: str, design, frame_size=(1080, 1920), picture_height: int = 608,
         out: Optional[Path] = None) -> Path:
    """A frame-sized PNG: the fields of a centred picture. Text stays clear of what the platforms cover on top;
    the call to action sits right under the picture, because the bottom of the frame is covered by their captions."""
    image = need("PIL.Image")
    d = load_design(design)
    s = spec(d, "band")
    width, height = (int(v) for v in frame_size)
    layer = image.new("RGBA", (width, height), (0, 0, 0, 0))
    picture_top = (height - int(picture_height)) // 2
    side, gap = int(s["side"] * width), int(s["gap"] * height)
    safe = d["video"].get("safe_zone_vertical", {})
    if headline.strip():
        _headline(layer, d, s["headline"], headline, int(safe.get("top", 0.12) * height), picture_top - gap, side)
    if cta.strip():
        _cta(layer, d, s["cta"], cta, picture_top + int(picture_height) + gap, side)
    if out is None:
        handle, name = tempfile.mkstemp(prefix="aiediting-band-", suffix=".png")
        os.close(handle)
        out = name
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    layer.save(out)
    return out
