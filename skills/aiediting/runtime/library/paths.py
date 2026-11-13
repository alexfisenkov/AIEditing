"""Where the person's library is: one pointer per computer, a fixed layout inside.

The pointer is `~/.aiediting/library.json` (Windows: `%LOCALAPPDATA%\\AIEditing\\library.json`);
the variable `AIEDITING_LIBRARY` names the folder directly and wins over the pointer.
"""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from typing import Dict, Optional

from . import store, templates

ENV = "AIEDITING_LIBRARY"
POINTER = "library.json"
KINDS: Dict[str, str] = {"галерея": "галерея.jsonl", "instagram": "instagram.jsonl",
                         "футажи": "футажи.jsonl", "стоки": "стоки.jsonl"}
LAYOUT: Dict[str, str] = {
    "about": "обо-мне", "documents": "обо-мне/документы", "rules": "правила.md",
    "forbidden": "чего-нельзя.md", "inventory": "опись", "progress": "опись/прогресс.json",
    "footage": "футажи", "photos": "фото", "instagram": "instagram", "stock": "стоки",
    "music": "музыка", "sounds": "звуки", "readme": "README.md",
}
FOLDERS = ("about", "documents", "inventory", "footage", "photos", "instagram", "stock", "music", "sounds")


class LibraryError(ValueError):
    """The library cannot do what was asked; the message says why and what to do, in Russian."""


def config_dir() -> Path:
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "AIEditing"
    return Path.home() / ".aiediting"


def pointer_file() -> Path:
    return config_dir() / POINTER


def wanted() -> Optional[Path]:
    """The folder the variable or the pointer names, whether it is there or not (a disk may be unplugged)."""
    env = os.environ.get(ENV, "").strip()
    if env:
        return Path(env).expanduser().resolve()
    data = store.read_json(pointer_file(), {})
    path = data.get("path") if isinstance(data, dict) else None
    return Path(path) if path else None


def find_library() -> Optional[Path]:
    path = wanted()
    return path if path is not None and path.is_dir() else None


def need_library() -> Path:
    path = find_library()
    if path is None:
        raise LibraryError("Библиотека не подключена: выберите папку командой library set <папка>")
    return path


def make_layout(library: Path) -> Path:
    """The folders and starting files; what is already there is never overwritten."""
    for key in FOLDERS:
        (library / LAYOUT[key]).mkdir(parents=True, exist_ok=True)
    files = {LAYOUT["readme"]: templates.README, LAYOUT["rules"]: templates.RULES,
             LAYOUT["forbidden"]: templates.FORBIDDEN}
    files.update({LAYOUT["about"] + "/" + name: templates.about(*text) for name, text in templates.ABOUT.items()})
    files.update({LAYOUT["inventory"] + "/" + name: "" for name in KINDS.values()})
    for rel, text in files.items():
        if not (library / rel).exists():
            store.write_text(library / rel, text)
    if not (library / LAYOUT["progress"]).exists():
        store.write_json(library / LAYOUT["progress"], {"kinds": {}})
    return library


def set_library(path: Path) -> Path:
    """Makes (or keeps) the library at `path` and points every skill on this computer at it."""
    library = Path(path).expanduser().resolve()
    make_layout(library)
    store.write_json(pointer_file(), {"path": str(library), "set": dt.date.today().isoformat()})
    return library
