"""The person's own rules (general and per format) and the list of what never to show.

`правила.md`: a «## Общие» section and one «## Формат: <имя>» section per format, a dated line per
remark, the newest at the bottom. `чего-нельзя.md`: one dated line per person or thing.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import List, Optional

from . import store, templates
from .paths import LAYOUT, LibraryError

GENERAL = "Общие"
_BULLET = re.compile(r"^- (?:\d{4}-\d{2}-\d{2}(?: · [^:]*)?: )?(.+)$")


def _heading(fmt: Optional[str]) -> str:
    return "## " + ("Формат: {}".format(fmt.strip()) if fmt and fmt.strip() else GENERAL)


def _sections(text: str) -> List[List[str]]:
    """[[heading, line, …], …]; the part before the first heading has the heading ""."""
    parts = [[""]]
    for line in text.splitlines():
        if line.startswith("## "):
            parts.append([line.rstrip()])
        else:
            parts[-1].append(line)
    return parts


def _join(parts: List[List[str]]) -> str:
    blocks = ["\n".join(p).strip("\n") if p[0] else "\n".join(p[1:]).strip("\n") for p in parts]
    return "\n\n".join(b for b in blocks if b) + "\n"


def _append_under(text: str, heading: str, line: str) -> str:
    parts = _sections(text)
    for part in parts:
        if part[0] == heading:
            while len(part) > 1 and not part[-1].strip():
                part.pop()
            part.append(line)
            break
    else:  # the general section goes first, right after the title
        parts.insert(1 if heading == _heading(None) else len(parts), [heading, "", line])
    return _join(parts)


def _clean(text: str, what: str) -> str:
    text = " ".join(str(text or "").split())
    if not text:
        raise LibraryError("Пустое {} не записываю".format(what))
    return text


def add_rule(library: Path, text: str, fmt: Optional[str] = None, video: Optional[str] = None,
             today: Optional[dt.date] = None) -> str:
    """Adds one dated rule under the format's section (or the general one); returns the line written."""
    text = _clean(text, "правило")
    path = Path(library) / LAYOUT["rules"]
    body = path.read_text(encoding="utf-8") if path.is_file() else templates.RULES
    day = (today or dt.date.today()).isoformat()
    line = "- {}{}: {}".format(day, " · " + " ".join(video.split()) if video else "", text)
    store.write_text(path, _append_under(body, _heading(fmt), line))
    return line


def rules_text(library: Path, fmt: Optional[str]) -> str:
    """The general rules and those of `fmt`, as they are written; "" when there are none."""
    path = Path(library) / LAYOUT["rules"]
    if not path.is_file():
        return ""
    keep = {_heading(None), _heading(fmt)}
    parts = [p for p in _sections(path.read_text(encoding="utf-8")) if p[0] in keep and any(l.strip() for l in p[1:])]
    return _join(parts) if parts else ""


def forbidden(library: Path) -> List[str]:
    path = Path(library) / LAYOUT["forbidden"]
    if not path.is_file():
        return []
    found = (_BULLET.match(line.strip()) for line in path.read_text(encoding="utf-8").splitlines())
    return [m.group(1).strip() for m in found if m]


def forbid(library: Path, what: str) -> str:
    """Adds a person or thing never to show; a repeat (in any case) is not written twice."""
    what = _clean(what, "запрет")
    known = forbidden(library)
    if what.casefold() in {w.casefold() for w in known}:
        return what
    path = Path(library) / LAYOUT["forbidden"]
    body = path.read_text(encoding="utf-8") if path.is_file() else templates.FORBIDDEN
    sep = "\n" if known else "\n\n"
    store.write_text(path, body.rstrip("\n") + sep + "- {}: {}\n".format(dt.date.today().isoformat(), what))
    return what
