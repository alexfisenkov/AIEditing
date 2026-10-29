"""Text blocks on a rounded translucent panel, drawn on a transparent frame-sized layer."""
from __future__ import annotations

from typing import Dict, List, Tuple

from .design import color
from .errors import need


def wrap(fnt, text: str, max_px: int, max_lines: int) -> List[str]:
    """Words into lines no wider than max_px; the last allowed line ends with … when cut."""
    lines: List[str] = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            trial = (line + " " + word).strip()
            if fnt.getlength(trial) <= max_px or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .,") + "…"
    while lines and fnt.getlength(lines[-1]) > max_px and len(lines[-1]) > 2:
        lines[-1] = lines[-1][:-2] + "…"
    return lines


def block_size(rows: List[Tuple[object, str]], gap: int) -> Tuple[int, int]:
    """Width and height of rows [(font, text)] stacked with `gap` between them."""
    widths, height = [], 0
    for fnt, text in rows:
        ascent, descent = fnt.getmetrics()
        widths.append(int(fnt.getlength(text)))
        height += ascent + descent
    return max(widths or [0]), height + gap * max(0, len(rows) - 1)


def draw(design, s: Dict, frame_size, box, pad, rows, colors: List[str], gap: int, radius: int):
    """RGBA layer of frame_size: the panel `box` (x, y, w, h), rows of text inside at `pad` (x, y)."""
    image, image_draw = need("PIL.Image"), need("PIL.ImageDraw")
    x, y, w, h = box
    layer = image.new("RGBA", tuple(frame_size), (0, 0, 0, 0))
    pen = image_draw.Draw(layer)
    if s.get("bg_alpha", 0) > 0:
        line = color(design, s["line"], s.get("line_alpha", 0)) if s.get("line") else None
        pen.rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=radius,
                              fill=color(design, s["bg"], s["bg_alpha"]),
                              outline=line, width=max(1, frame_size[1] // 720) if line else 0)
    text_layer = image.new("RGBA", tuple(frame_size), (0, 0, 0, 0))
    ink = image_draw.Draw(text_layer)
    stroke = int(s.get("stroke", 0) * rows[0][0].size) if rows else 0
    ty = y + pad[1]
    for (fnt, text), name in zip(rows, colors):
        tx = x + (w - int(fnt.getlength(text))) // 2 if s.get("align") == "center" else x + pad[0]
        ink.text((tx, ty), text, font=fnt, fill=color(design, name),
                 stroke_width=stroke, stroke_fill=color(design, s.get("stroke_color", "night")))
        ascent, descent = fnt.getmetrics()
        ty += ascent + descent + gap
    return image.alpha_composite(layer, text_layer)
