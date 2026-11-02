"""Sound files of a working folder -> src/data/sfx.json (only files that exist) and the optional music pad."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple

from .common import ToolError, warn, write_atomic

AUDIO = {".wav", ".mp3", ".m4a", ".aac", ".ogg"}
# The names a scene may use; the same list is VOL in template/src/kit/Sound.tsx (a test keeps them equal)
NAMES = ["whoosh-soft", "mouse-click", "switch", "shutter-modern", "page-turn", "ding", "pop-soft", "tick", "riser-1s"]


def _drop_stem(folder: Path, stem: str) -> None:
    for old in folder.glob(stem + ".*"):
        if old.suffix.lower() in AUDIO:
            old.unlink()


def add_sfx(work: Path, source: Path) -> Tuple[int, int]:
    """Copy the person's sounds over the shipped ones, by name. Returns (copied, ignored)."""
    source = Path(source).expanduser()
    if not source.is_dir():
        raise ToolError("--sfx: нет папки {}".format(source))
    dst = work / "public" / "sfx"
    dst.mkdir(parents=True, exist_ok=True)
    copied = ignored = 0
    for file in sorted(source.iterdir()):
        if file.suffix.lower() not in AUDIO or not file.is_file():
            continue
        if file.stem not in NAMES:
            warn("звук «{}» не используется: имя не из набора ({}). Назовите файл одним из этих имён.".format(file.name, ", ".join(NAMES)))
            ignored += 1
            continue
        _drop_stem(dst, file.stem)
        shutil.copyfile(str(file), str(dst / file.name))
        copied += 1
    return copied, ignored


def add_music(work: Path, music: Path) -> None:
    music = Path(music).expanduser()
    if not music.is_file() or music.suffix.lower() not in AUDIO:
        raise ToolError("--music: нужен звуковой файл ({}), а передано: {}".format("/".join(sorted(AUDIO)), music))
    folder = work / "public" / "music"
    folder.mkdir(parents=True, exist_ok=True)
    _drop_stem(folder, "pad")
    shutil.copyfile(str(music), str(folder / ("pad" + music.suffix.lower())))


def write_manifest(work: Path) -> Dict:
    """src/data/sfx.json lists what is really on disk, so a scene never points at a missing file."""
    files: Dict[str, str] = {}
    folder = work / "public" / "sfx"
    if folder.is_dir():
        for file in sorted(folder.iterdir()):
            if file.suffix.lower() in AUDIO and file.stem in NAMES:
                files[file.stem] = "sfx/" + file.name
    music: Optional[str] = None
    mfolder = work / "public" / "music"
    if mfolder.is_dir():
        pad = next((f for f in sorted(mfolder.iterdir()) if f.stem == "pad" and f.suffix.lower() in AUDIO), None)
        music = "music/" + pad.name if pad else None
    data = {"files": files, "music": music}
    write_atomic(work / "src" / "data" / "sfx.json", json.dumps(data, indent=2) + "\n")
    return data
