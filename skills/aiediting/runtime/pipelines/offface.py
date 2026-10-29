"""A picture laid over a 9:16 piece must not cover the face: shrink it until it stays off, or leave it out."""
from __future__ import annotations

import copy
from typing import Callable, Dict, Optional

SHRINK, TRIES = 0.8, 4


def _covers(box, face: Dict) -> bool:
    x0, y0, x1, y1 = box
    return x0 < face["x"] + face["w"] and face["x"] < x1 and y0 < face["y"] + face["h"] and face["y"] < y1


def _drawn(path):
    """(x0, y0, x1, y1) of what is actually drawn on a transparent PNG; None if nothing is."""
    from PIL import Image

    with Image.open(str(path)) as img:
        return img.getchannel("A").getbbox() if "A" in img.getbands() else img.getbbox()


def _smaller(design: Dict, kind: str) -> Dict:
    d = copy.deepcopy(design)
    spec = d["video"][kind]
    for key in ("size", "body_size"):
        if key in spec:
            spec[key] = float(spec[key]) * SHRINK
    return d


def off_face(render: Callable[[Dict], object], design: Dict, kind: str, face: Optional[Dict]):
    """render(design) -> PNG path. The first picture whose drawn part misses `face`; None if none does."""
    for _ in range(TRIES + 1):
        path = render(design)
        box = _drawn(path) if face is not None else None
        if box is None or not _covers(box, face):
            return path
        design = _smaller(design, kind)
    return None
