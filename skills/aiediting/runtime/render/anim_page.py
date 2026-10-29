"""One HyperFrames project for one insert: a template of the design filled with the slot and the tokens."""
from __future__ import annotations

import html
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from .anim_spec import REFERENCE, WEIGHTS
from .design import color, load_design
from .errors import RenderError
from .fonts import font_file

_ITEM = re.compile(r"<!--item-->(.*?)<!--/item-->", re.S)
ROLES = (("display", "font"), ("text", "body_font"), ("mono", "mono_font"))


def _rgba(design, s: Dict, role: str, alpha: float) -> str:
    """A colour of the format's palette by its name; a name the palette lacks → the reference colour."""
    try:
        r, g, b, a = color(design, s.get(role) or REFERENCE[role], alpha)
    except RenderError:
        r, g, b, a = color(design, REFERENCE[role], alpha)
    return "rgba({},{},{},{:.3f})".format(r, g, b, a / 255.0)


def _fonts(design, s: Dict, assets: Path) -> List[str]:
    """@font-face for the three roles, the files copied next to the page (no font is fetched)."""
    rules = []
    for css, key in ROLES:
        path, _exact = font_file(design, s.get(key, css))
        assets.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(path), str(assets / path.name))
        rules.append('@font-face{{font-family:"ae-{}";src:url("assets/fonts/{}");font-weight:100 900;}}'
                     .format(css, path.name))
    return rules


def _vars(design, s: Dict, size: Tuple[int, int], u: int, seconds: float, title: str = "") -> str:
    """Tokens as CSS variables; `u` px is what size shares are taken of (the frame's short side).

    A long figure («200 тысяч») gets a smaller size so that it fits the panel's width."""
    px = lambda share: "{:.1f}px".format(float(share) * u)  # noqa: E731
    fits = (size[0] - 2 * s["pad"] * u) / max(1.0, 0.68 * len(title)) / u
    radius = size[1] / 2.0 if s.get("radius") == "pill" else float(s.get("radius", 0)) * u
    pairs = {"bg": _rgba(design, s, "bg", s["bg_alpha"]), "fg": _rgba(design, s, "fg", 1.0),
             "body-fg": _rgba(design, s, "body_fg", 1.0), "line": _rgba(design, s, "line", s["line_alpha"]),
             "radius": "{:.1f}px".format(radius), "pad": px(s["pad"]), "title-size": px(s["size"]),
             "body-size": px(s["body_size"]), "number-size": px(min(s["number_size"], fits)), "row": str(s["row"]),
             "title-weight": str(WEIGHTS.get(s.get("weight"), 700)),
             "body-weight": str(WEIGHTS.get(s.get("body_weight"), 400)),
             "ease": load_design(design).get("motion", {}).get("ease", "ease-out"),
             "enter": "{:.2f}s".format(s["enter"]), "exit": "{:.2f}s".format(s["exit"]),
             "out-at": "{:.2f}s".format(max(s["enter"], seconds - s["exit"]))}
    return ":root{" + "".join("--{}:{};".format(k, v) for k, v in pairs.items()) + "}"


def page(template: Path, slot: Dict, design, s: Dict, size: Tuple[int, int], u: int,
         seconds: float, folder: Path) -> Path:
    """Writes `folder/index.html` (+ assets/fonts) and returns the folder."""
    raw = template.read_text(encoding="utf-8")
    row = _ITEM.search(raw)
    items = [str(i).strip() for i in slot.get("items", []) if str(i).strip()]
    rows = "".join(row.group(1).replace("{{n}}", str(k + 1)).replace("{{text}}", html.escape(t))
                   .replace("{{delay}}", "{:.2f}s".format(s["enter"] * 0.6 + k * s["stagger"]))
                   for k, t in enumerate(items)) if row else ""
    title = str(slot.get("title", "")).strip()
    style = "\n".join(_fonts(design, s, folder / "assets" / "fonts") + [_vars(design, s, size, u, seconds, title)])
    text = _ITEM.sub(lambda _m: rows, raw)
    for key, value in (("style", style), ("w", size[0]), ("h", size[1]), ("seconds", "{:.3f}".format(seconds)),
                       ("title", html.escape(title))):
        text = text.replace("{{" + key + "}}", str(value))
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "index.html").write_text(text, encoding="utf-8")
    return folder
