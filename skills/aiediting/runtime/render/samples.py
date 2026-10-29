"""samples(): every variant of an element laid over the person's own frame, to choose from."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from .design import load_design, variants
from .errors import need
from .place import opposite_corner
from .plate import plate

EXAMPLE_TEXT = {
    "chapter": "Глава 2 · Настройка",
    "caption": "Так будут выглядеть субтитры на вашем видео",
    "card": "Главное\nКоротко, одна-две строки по делу",
}


def samples(design, frame, kind: str = "chapter", text: Optional[str] = None,
            face: Optional[Dict] = None, outdir=None) -> List[Path]:
    """PNG per variant: the frame with the element on it. A face window keeps cards off the face."""
    image = need("PIL.Image")
    d = load_design(design)
    out = Path(outdir) if outdir else Path(tempfile.mkdtemp(prefix="aiediting-samples-"))
    out.mkdir(parents=True, exist_ok=True)
    with image.open(frame) as src:
        base = src.convert("RGBA")
    shots = []
    for i, variant in enumerate(variants(d, kind)):
        where = None
        if face and kind == "card" and "where" not in variant:
            where = opposite_corner(face, base.size)
        layer_path = plate(text or EXAMPLE_TEXT.get(kind, kind), d, kind, frame_size=base.size,
                           where=where, variant=i, out=out / "layer_{}_{}.png".format(kind, i + 1))
        with image.open(layer_path) as layer:
            shot = image.alpha_composite(base, layer.convert("RGBA")).convert("RGB")
        layer_path.unlink()
        path = out / "sample_{}_{}.png".format(kind, i + 1)
        shot.save(path)
        shots.append(path)
    return shots
