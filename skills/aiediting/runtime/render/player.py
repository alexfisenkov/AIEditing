"""The teaser's player: a Play button on black, and a progress bar with the time of the whole video, frame by frame."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Sequence, Tuple

from .design import color, load_design, spec
from .errors import need
from .fill import fill
from .fonts import font

SHARP = 4  # Pillow draws shapes without smoothing: drawn larger, then reduced
STRIP, SOLID = 104, 72  # the bar's strip and its solid part, in a 1080 frame


def frames_pattern(folder: Path) -> str:
    """The folder's numbered frames as ffmpeg reads them; a % in the folder's name is not a number."""
    return str(folder).replace("%", "%%") + os.sep + "%05d.png"


def _button(d: Dict, s: Dict, side: int):
    """A ring with the triangle inside, `side` pixels, transparent around."""
    image, pen = need("PIL.Image"), need("PIL.ImageDraw")
    big = side * SHARP
    layer = image.new("RGBA", (big, big), (0, 0, 0, 0))
    pen.Draw(layer).ellipse([SHARP, SHARP, big - SHARP, big - SHARP], outline=color(d, s["ring"], s["ring_alpha"]),
                            width=big // 40)
    mask = image.new("L", (big, big), 0)
    pen.Draw(mask).polygon([(big * 0.40, big * 0.29), (big * 0.40, big * 0.71), (big * 0.73, big * 0.5)], fill=255)
    layer.paste(fill(d, (big, big), s["icon"]), (0, 0), mask)
    return layer.resize((side, side), image.LANCZOS)


def _ease(t: float) -> float:
    return 1 - (1 - min(max(t, 0.0), 1.0)) ** 3


def play_frames(design, size: Tuple[int, int], folder: Path, fps: int, black: float, press: float, end: float) -> None:
    """Black, the button comes up, it is pressed at `press` (dips, as under a finger), cut at `end`."""
    image = need("PIL.Image")
    d = load_design(design)
    s = spec(d, "teaser")
    button = _button(d, s, int(s["icon_size"] * size[1]))
    folder.mkdir(parents=True, exist_ok=True)
    for k in range(int(round(end * fps))):
        t = k / float(fps)
        frame = image.new("RGB", size, (0, 0, 0))
        grow = _ease((t - black) / 0.3)
        dip = 1.0 - 0.1 * max(0.0, 1.0 - abs(t - press - 0.05) / 0.07)
        side = int(button.size[0] * (0.8 + 0.2 * grow) * dip)
        if t >= black and side > 0:
            shown = button.resize((side, side), image.BICUBIC)
            shown.putalpha(shown.getchannel("A").point(lambda a, g=grow: int(a * g)))
            frame.paste(shown, ((size[0] - side) // 2, (size[1] - side) // 2), shown)
        frame.save(folder / "{:05d}.png".format(k), compress_level=1)


def stamp(t: float) -> str:
    t = int(max(0.0, t))
    return "{}:{:02d}".format(t // 60, t % 60) if t < 3600 else "{}:{:02d}:{:02d}".format(t // 3600, t // 60 % 60, t % 60)


def _panel(width: int, height: int, solid: int):
    """A player's bar: solid black at the bottom, so it closes what the finished video has there, soft above it."""
    image = need("PIL.Image")
    ramp = image.new("L", (1, height))
    soft = height - solid
    for y in range(height):
        ramp.putpixel((0, y), 255 if y >= soft else int(255 * (y / float(max(1, soft))) ** 1.5))
    black = image.new("RGBA", (width, height), (0, 0, 0, 255))
    black.putalpha(ramp.resize((width, height)))
    return black


def _fast_mark(pen, x: int, y: int, h: int, ink) -> int:
    """▶▶ drawn as shapes: returns the x after it."""
    for k in (0, 1):
        left = x + k * int(h * 0.75)
        pen.polygon([(left, y), (left, y + h), (left + int(h * 0.75), y + h // 2)], fill=ink)
    return x + int(h * 1.5) + h // 2


def strip_frames(design, width: int, height: int, moments: Sequence[Dict], total: float, folder: Path) -> Dict:
    """One PNG per frame of the teaser's body. moments: [{"t": time in the full video, "rate": how fast it runs}]."""
    image, pen = need("PIL.Image"), need("PIL.ImageDraw")
    d = load_design(design)
    s = spec(d, "teaser")
    tall, solid = int(STRIP * height / 1080.0), int(SOLID * height / 1080.0)
    base = _panel(width, tall, solid)
    margin, thick = int(width * 0.021), max(4, int(height * 0.0056))
    fnt = font(d, s["font"], s["weight"], int(s["text_size"] * height))
    ink = color(d, s["text"])
    ascent, descent = fnt.getmetrics()
    middle = tall - solid // 2
    y_text, y_bar = middle - (ascent + descent) // 2, middle - thick // 2
    tail = " / " + stamp(round(total))
    # a room for the time and for the mark of a fast-forward, the same on every frame: the bar does not jump
    start = margin + int(fnt.getlength(stamp(total) + tail)) + int(ascent * 3.4) + margin
    long = width - margin - start
    r, g, b, _ = color(d, s["track"])  # over black, opaque: Pillow writes alpha as it is, and the video would show through
    pen.Draw(base).rounded_rectangle([start, y_bar, width - margin, y_bar + thick], radius=thick // 2,
                                     fill=tuple(int(c * s["track_alpha"]) for c in (r, g, b)) + (255,))
    bar = fill(d, (width, thick), s["bar"])
    folder.mkdir(parents=True, exist_ok=True)
    for k, m in enumerate(moments):
        frame = base.copy()
        x = start + int(long * min(1.0, m["t"] / float(total)))
        frame.paste(bar.crop((0, 0, max(1, x - start), thick)), (start, y_bar))
        draw = pen.Draw(frame)
        draw.ellipse([x - thick, y_bar - thick // 2, x + thick, y_bar + thick + thick // 2], fill=ink)
        draw.text((margin, y_text), stamp(m["t"]) + tail, font=fnt, fill=ink)
        if m["rate"] >= 2.0:
            at = margin + int(fnt.getlength(stamp(total) + tail)) + margin // 2
            after = _fast_mark(draw, at, y_text + descent + ascent // 6, ascent - descent, ink)
            draw.text((after, y_text), "×{:g}".format(round(m["rate"])), font=fnt, fill=ink)
        frame.save(folder / "{:05d}.png".format(k), compress_level=1)
    return {"pattern": frames_pattern(folder), "y": height - tall}
