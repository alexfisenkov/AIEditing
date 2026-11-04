"""Text and shapes filled with a colour or with the design's chrome gradient."""
from __future__ import annotations

from typing import Dict, Tuple

from .design import color
from .errors import need

STOPS = (0.0, 0.4, 0.62, 1.0)  # of the chrome gradient, as in the system's own CSS


def fill(d: Dict, size: Tuple[int, int], name: str):
    """A picture of `size` in the named colour, or in the chrome gradient from top to bottom."""
    image = need("PIL.Image")
    if name != "chrome":
        return image.new("RGBA", size, color(d, name))
    stops = [color(d, c) for c in d["gradient"]["chrome"]]
    out = image.new("RGBA", (1, size[1]))
    for y in range(size[1]):
        t = y / float(max(1, size[1] - 1))
        k = next((i for i in range(len(STOPS) - 1) if t <= STOPS[i + 1]), len(STOPS) - 2)
        f = (t - STOPS[k]) / (STOPS[k + 1] - STOPS[k])
        out.putpixel((0, y), tuple(int(a + (b - a) * f) for a, b in zip(stops[k], stops[k + 1])))
    return out.resize(size)


def text(layer, d: Dict, xy: Tuple[int, int], line: str, fnt, name: str) -> None:
    """One line of text at `xy`, in the colour or the gradient `name`."""
    image, pen = need("PIL.Image"), need("PIL.ImageDraw")
    ascent, descent = fnt.getmetrics()
    w, h = max(1, int(fnt.getlength(line)) + 4), ascent + descent
    mask = image.new("L", (w, h), 0)
    pen.Draw(mask).text((0, 0), line, font=fnt, fill=255)
    layer.paste(fill(d, (w, h), name), xy, mask)
