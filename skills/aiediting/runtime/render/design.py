"""A design system on disk: a folder with tokens.json (+ fonts/). Colours are named, sizes are shares."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from .errors import RenderError

_HERE = Path(__file__).resolve().parent.parent.parent  # skill root: runtime/ sits inside it


def default_design() -> Path:
    """A format skill's own design/ first; inside AIEditing — the Chrome & Graphite example."""
    own = _HERE / "design"
    return own if (own / "tokens.json").is_file() else own / "chrome-graphite"


def load_design(design: Union[str, Path, Dict, None] = None) -> Dict:
    """tokens.json as a dict with "root" (the folder, for fonts). A loaded dict passes through."""
    if isinstance(design, dict):
        return design
    root = Path(design) if design else default_design()
    tokens = root / "tokens.json" if root.is_dir() else root
    try:
        data = json.loads(tokens.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RenderError("Не читается дизайн-система {}: {}".format(tokens, exc))
    data["root"] = tokens.parent
    return data


def variants(design, kind: str) -> List[Dict]:
    """Variants of an element to show a human (at least one: the element as specified)."""
    d = load_design(design)
    return d["video"].get("variants", {}).get(kind) or [{"name": kind}]


def spec(design, kind: str, variant: Optional[Union[int, str, Dict]] = None) -> Dict:
    """Settings of one element (chapter/caption/card), with a variant's overrides on top."""
    d = load_design(design)
    if kind not in d.get("video", {}):
        raise RenderError("В дизайн-системе нет элемента «{}»".format(kind))
    base = dict(d["video"][kind])
    if isinstance(variant, dict):
        return dict(base, **variant)
    if variant is not None:
        options = variants(d, kind)
        found = options[variant] if isinstance(variant, int) else next(
            (v for v in options if v.get("name") == variant), None)
        if found is None:
            raise RenderError("Нет варианта «{}» у элемента «{}»".format(variant, kind))
        base.update(found)
    return base


def color(design, name: str, alpha: float = 1.0) -> Tuple[int, int, int, int]:
    """RGBA from a palette name (or a literal #RRGGBB)."""
    value = load_design(design)["color"].get(name, name)
    if not (isinstance(value, str) and value.startswith("#") and len(value) == 7):
        raise RenderError("Цвет «{}» не задан в дизайн-системе".format(name))
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5)) + (int(round(255 * alpha)),)
