"""tokens.json of a design folder -> src/data/design.json (and the font files the video needs).

A block "overlay" in tokens.json is taken as it is; whatever it leaves out is derived from the ordinary
color / gradient / radius tokens (see README, "Design"). Fonts come from the ordinary "font" block: families the
template already carries as woff2 use those, other families use the file named in tokens.json.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .common import ToolError, warn, write_atomic

COLOR_KEYS = ["white", "muted", "faint", "graphite", "graphiteSoft", "deep", "card", "silver", "silverLight", "paper", "ink", "line", "ok"]
TEXT_KEYS = ["chrome", "bg", "glass", "hair", "rim", "shadow", "shine"]
RADIUS_KEYS = ["block", "card", "inner", "pill"]
DEFAULT_RADIUS = {"block": 26, "card": 22, "inner": 15, "pill": 999}
CHROME_STOPS = [0, 40, 62, 100]  # where the four stops of the chrome gradient sit, as in the reference look
SHADOW = "0 40px 90px rgba(0,0,0,.55)"
LINE = "rgba(255,255,255,.14)"

_LATIN_WIDE = "U+0000-03FF,U+2000-206F,U+20AC"
_CYR = "U+0400-04FF,U+2116"
# Families whose woff2 files ship in template/public/fonts: (file, weight range, unicode-range)
TEMPLATE_FONTS: Dict[str, List[Tuple[str, str, str]]] = {
    "Unbounded": [("fonts/unbounded-cyrillic-wght-normal.woff2", "200 900", _CYR), ("fonts/unbounded-latin-wght-normal.woff2", "200 900", _LATIN_WIDE)],
    "Onest": [("fonts/onest-cyrillic-wght-normal.woff2", "100 900", _CYR), ("fonts/onest-latin-wght-normal.woff2", "100 900", _LATIN_WIDE)],
    "JetBrains Mono": [("fonts/jetbrains-mono-cyrillic-wght-normal.woff2", "100 800", "U+0400-04FF"),
                       ("fonts/jetbrains-mono-latin-wght-normal.woff2", "100 800", "U+0000-03FF,U+2000-206F")],
}
STACKS = {"display": "system-ui,sans-serif", "text": "-apple-system,sans-serif", "mono": "ui-monospace,monospace"}
DEFAULT_FAMILY = {"display": "Unbounded", "text": "Onest", "mono": "JetBrains Mono"}
FORMATS = {".woff2": "woff2", ".woff": "woff", ".ttf": "truetype", ".otf": "opentype"}


def load_tokens(design: Path) -> Tuple[Dict, Path]:
    path = Path(design).expanduser()
    file = path / "tokens.json" if path.is_dir() else path
    try:
        return json.loads(file.read_text(encoding="utf-8")), file.parent
    except (OSError, ValueError) as exc:
        raise ToolError("Не читается дизайн-система {}: {}".format(file, exc))


def _rgb(value: str) -> Tuple[int, int, int]:
    h = value.strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", h):
        raise ToolError("Цвет должен быть вида #RRGGBB, а в дизайне: «{}»".format(value))
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _hex(rgb: Tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _derive(tokens: Dict) -> Tuple[Dict, Dict]:
    """Colours and surfaces from the ordinary tokens; whatever cannot be derived is simply absent."""
    color, gradient = tokens.get("color", {}), tokens.get("gradient", {})
    pick = lambda *names: next((color[n] for n in names if n in color), None)  # noqa: E731
    out_c, out_t = {}, {}
    pairs = {"white": pick("white"), "graphite": pick("graphite"), "graphiteSoft": pick("graphite-soft"), "deep": pick("night", "deep"),
             "silver": pick("silver"), "silverLight": pick("silver-light"), "paper": pick("paper"), "ink": pick("ink"),
             "ok": pick("ok"), "faint": pick("faint")}
    out_c.update({k: v for k, v in pairs.items() if v})
    if "silver" in out_c:
        out_c["muted"] = out_c["silver"]  # the ordinary muted token is for light pages: unreadable on the dark stage
    if "graphite" in out_c and "graphiteSoft" in out_c:
        a, b = _rgb(out_c["graphite"]), _rgb(out_c["graphiteSoft"])
        out_c["card"] = _hex(tuple((x + y + 1) // 2 for x, y in zip(a, b)))  # type: ignore[arg-type]
    out_c["line"] = LINE
    chrome = gradient.get("chrome")
    if isinstance(chrome, list) and len(chrome) >= 2:
        stops = CHROME_STOPS if len(chrome) == 4 else [round(100 * i / (len(chrome) - 1)) for i in range(len(chrome))]
        out_t["chrome"] = "linear-gradient(180deg,{})".format(",".join("{} {}%".format(c, p) for c, p in zip(chrome, stops)))
    dark = gradient.get("dark-surface")
    if isinstance(dark, list) and len(dark) == 2:
        out_t["bg"] = "linear-gradient(165deg,{} 0%,{} 100%)".format(dark[0], dark[1])
        (r1, g1, b1), (r2, g2, b2) = _rgb(dark[0]), _rgb(dark[1])
        out_t["glass"] = "linear-gradient(165deg,rgba({},{},{},.92),rgba({},{},{},.94))".format(r1, g1, b1, r2, g2, b2)
    if "silver" in out_c:
        r, g, b = _rgb(out_c["silver"])
        out_t["hair"] = "linear-gradient(90deg,transparent,rgba({},{},{},.55),transparent)".format(r, g, b)
        out_t["rim"] = "0 0 0 1px rgba({},{},{},.2), inset 0 1px 0 rgba(255,255,255,.08)".format(r, g, b)
    if all(k in out_c for k in ("silver", "silverLight", "white")):
        out_t["shine"] = "linear-gradient(100deg,{s} 0%,{l} 30%,{w} 42%,{l} 54%,{s} 100%)".format(
            s=out_c["silver"], l=out_c["silverLight"], w=out_c["white"])
    out_t["shadow"] = SHADOW
    return out_c, out_t


def overlay_block(tokens: Dict) -> Tuple[Dict, Dict, Dict, bool]:
    """(colors, surfaces, radius, had_overlay): the overlay block over what is derived."""
    colors, surfaces = _derive(tokens)
    radius = dict(DEFAULT_RADIUS)
    radius.update({k: v for k, v in tokens.get("radius", {}).items() if k in RADIUS_KEYS})
    block = tokens.get("overlay")
    if isinstance(block, dict):
        colors.update({k: v for k, v in block.get("color", {}).items() if k in COLOR_KEYS})
        surfaces.update({k: block[k] for k in TEXT_KEYS if isinstance(block.get(k), str)})
        radius.update({k: v for k, v in block.get("radius", {}).items() if k in RADIUS_KEYS})
    missing = [k for k in COLOR_KEYS if k not in colors] + [k for k in TEXT_KEYS if k not in surfaces]
    if missing:
        raise ToolError("В дизайне не хватает значений для наложений: {}. Добавьте блок \"overlay\" в tokens.json "
                        "(форма — в README, раздел Design) или недостающие обычные токены.".format(", ".join(missing)))
    return colors, surfaces, radius, isinstance(block, dict)


def _faces_for(role: str, spec: Dict, root: Path, work: Path, tokens: Dict, tried: Tuple[str, ...] = ()) -> Tuple[str, List[Dict]]:
    """(family, @font-face entries) for one role; `tried`: roles already followed, fallbacks may point at each other."""
    family = spec.get("family") or DEFAULT_FAMILY[role]
    if family in TEMPLATE_FONTS:
        return family, [{"family": family, "src": s, "format": "woff2", "weight": w, "range": r} for s, w, r in TEMPLATE_FONTS[family]]
    file = spec.get("file")
    path = (root / file) if file else None
    if path is not None and path.is_file() and path.suffix.lower() in FORMATS:
        dst_name = "design-{}{}".format(role, path.suffix.lower())
        (work / "public" / "fonts").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(path), str(work / "public" / "fonts" / dst_name))
        return family, [{"family": family, "src": "fonts/" + dst_name, "format": FORMATS[path.suffix.lower()], "weight": "100 900", "range": None}]
    fallback = spec.get("fallback")
    if fallback and fallback != role and fallback not in tried and fallback in tokens.get("font", {}):
        warn("шрифт «{}» ({}) не найден, берётся шрифт роли «{}».".format(family, role, fallback))
        return _faces_for(fallback, tokens["font"][fallback], root, work, tokens, tried + (role,))
    warn("шрифт «{}» ({}): файла нет, останется системный запасной.".format(family, role))
    return family, []


def check(design: Path) -> None:
    """Fail on a broken or incomplete design before anything is written."""
    tokens, _ = load_tokens(design)
    overlay_block(tokens)


def build(design: Path, work: Path, logo: Optional[str]) -> str:
    tokens, root = load_tokens(design)
    colors, surfaces, radius, had_overlay = overlay_block(tokens)
    families: Dict[str, str] = {}
    faces: List[Dict] = []
    seen = set()
    for role in ("display", "text", "mono"):
        spec = tokens.get("font", {}).get(role) or {}
        family, entries = _faces_for(role, spec, root, work, tokens)
        families[role] = family
        for e in entries:
            key = (e["family"], e["src"])
            if key not in seen:
                seen.add(key)
                faces.append(e)
    data = {
        "name": tokens.get("name") or root.name,
        "C": {k: colors[k] for k in COLOR_KEYS},
        "CHROME": surfaces["chrome"], "BG": surfaces["bg"], "GLASS": surfaces["glass"], "HAIR": surfaces["hair"],
        "FONT": {role: "'{}',{}".format(families[role], STACKS[role]) for role in STACKS},
        "R": {k: radius[k] for k in RADIUS_KEYS},
        "RIM": surfaces["rim"], "SHADOW": surfaces["shadow"], "SHINE": surfaces["shine"],
        "families": families, "fonts": faces, "logo": logo,
    }
    write_atomic(work / "src" / "data" / "design.json", json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return "{} ({})".format(data["name"], "блок overlay" if had_overlay else "выведен из обычных токенов")
