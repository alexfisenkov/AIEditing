"""A large headline into lines: words kept with their neighbours, as even as they can be, as big as they fit."""
from __future__ import annotations

from typing import Dict, List, Tuple

from .fonts import font

GLUE = " "


def tokens(text: str) -> List[str]:
    """Words to wrap: a dash stays with the word before it, a short word with the word after it."""
    out: List[str] = []
    hold = ""
    for word in text.split():
        if word in ("—", "–") and out:
            out[-1] += GLUE + word
        elif len(word) <= 2:
            hold += word + GLUE
        else:
            out.append(hold + word)
            hold = ""
    return out + ([hold.rstrip(GLUE)] if hold else [])


def _greedy(fnt, words: List[str], width: float) -> List[str]:
    lines: List[str] = []
    for word in words:
        trial = (lines[-1] + " " + word) if lines else word
        if lines and fnt.getlength(trial) <= width:
            lines[-1] = trial
        else:
            lines.append(word)
    return lines


def balanced(fnt, words: List[str], width: float) -> List[str]:
    """As few lines as `width` allows, then as even as they can be: no lone word on the last line."""
    best = _greedy(fnt, words, width)
    narrower = width
    while narrower > width * 0.5:
        narrower -= width * 0.02
        lines = _greedy(fnt, words, narrower)
        if len(lines) > len(best):
            break
        best = lines
    return best


def fit(d: Dict, s: Dict, text: str, width: int, room: int, unit: int) -> Tuple[object, List[str], int]:
    """(font, lines, line step): the largest size whose lines fit `width` × `room`, down to `min_size`."""
    words, size = tokens(text), int(s["size"] * unit)
    while True:
        fnt = font(d, s["font"], s["weight"], size)
        lines = balanced(fnt, words, width)
        step = int(size * s.get("line", 1.16))
        fits = (len(lines) <= s.get("max_lines", 4) and len(lines) * step <= room
                and max(fnt.getlength(x) for x in lines) <= width)
        if fits or size <= int(s.get("min_size", 0.02) * unit):
            return fnt, lines, step
        size -= 2
