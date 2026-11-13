"""Sound files of a working folder -> src/data/sfx.json (only files that exist) and the optional music pad.

Two ways to call a sound: by an old name (`files`) or by a role (`roles`, from the catalogs: the person's own
`public/sfx/own/catalog.json` first, then the kit's `public/sfx/catalog.json`)."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import sfxcat
from .common import TEMPLATE, ToolError, warn, write_atomic

AUDIO = {".wav", ".mp3", ".m4a", ".aac", ".ogg"}
# The names a scene may use; the same list is VOL in template/src/kit/Sound.tsx (a test keeps them equal)
NAMES = ["whoosh-soft", "mouse-click", "switch", "shutter-modern", "page-turn", "ding", "pop-soft", "tick", "riser-1s"]
OWN = "own"  # public/sfx/own: the person's sounds, measured into their own catalog


def _drop_stem(folder: Path, stem: str) -> None:
    for old in folder.glob(stem + ".*"):
        if old.suffix.lower() in AUDIO:
            old.unlink()


def _copy_roles(source: Path, own: Path) -> int:
    copied = 0
    for role in sfxcat.ROLES:
        for file in sorted((source / role).glob("*")) if (source / role).is_dir() else []:
            if file.is_file() and file.suffix.lower() in sfxcat.AUDIO:
                (own / role).mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(file), str(own / role / file.name))
                copied += 1
    return copied


def add_sfx(work: Path, source: Path) -> Tuple[int, int]:
    """Copy the person's sounds: files named as in NAMES over the shipped ones, role subfolders (`whoosh/…`) into
    public/sfx/own, then measure them into its catalog. Returns (copied, ignored)."""
    source = Path(source).expanduser()
    if not source.is_dir():
        raise ToolError("--sfx: нет папки {}".format(source))
    dst = work / "public" / "sfx"
    own = dst / OWN
    if own.is_dir():
        shutil.rmtree(str(own))
    own.mkdir(parents=True)
    copied = ignored = 0
    for file in sorted(source.iterdir()):
        if file.suffix.lower() not in AUDIO or not file.is_file():
            continue
        if file.stem not in NAMES:
            warn("звук «{}» не используется: имя не из набора ({}), а звуки по ролям лежат в подпапках с именем роли ({}).".format(
                file.name, ", ".join(NAMES), ", ".join(sfxcat.ROLES)))
            ignored += 1
            continue
        _drop_stem(dst, file.stem)
        shutil.copyfile(str(file), str(dst / file.name))
        shutil.copyfile(str(file), str(own / file.name))
        copied += 1
    copied += _copy_roles(source, own)
    try:
        sfxcat.write(own)
    except ToolError as exc:
        warn("свои звуки не измерены, по ролям их не будет: {}".format(exc))
    return copied, ignored


def add_music(work: Path, music: Path) -> None:
    music = Path(music).expanduser()
    if not music.is_file() or music.suffix.lower() not in AUDIO:
        raise ToolError("--music: нужен звуковой файл ({}), а передано: {}".format("/".join(sorted(AUDIO)), music))
    folder = work / "public" / "music"
    folder.mkdir(parents=True, exist_ok=True)
    _drop_stem(folder, "pad")
    shutil.copyfile(str(music), str(folder / ("pad" + music.suffix.lower())))


def _shipped_unchanged(sfx: Path, rel: str) -> bool:
    """A top-level shipped sound replaced by the person's own file under the same name is no longer what was measured."""
    if "/" in rel:
        return True
    mine, ours = sfx / rel, TEMPLATE / "public" / "sfx" / rel
    return not ours.is_file() or mine.stat().st_size == ours.stat().st_size


def roles(sfx: Path) -> Dict[str, List[Dict]]:
    """role -> [{file, dur_ms, peak_ms, level_db}]: own sounds first, then the kit's; only files that exist."""
    out: Dict[str, List[Dict]] = {}
    for folder, prefix in ((sfx / OWN, "sfx/{}/".format(OWN)), (sfx, "sfx/")):
        for row in sfxcat.read(folder):
            if (folder / row["file"]).is_file() and (folder != sfx or _shipped_unchanged(sfx, row["file"])):
                out.setdefault(row["role"], []).append({"file": prefix + row["file"], "dur_ms": int(row.get("dur_ms") or 0),
                                                        "peak_ms": int(row.get("peak_ms") or 0),
                                                        "level_db": float(row.get("level_db") or 0.0)})
    return out


def write_manifest(work: Path) -> Dict:
    """src/data/sfx.json lists what is really on disk, so a scene never points at a missing file."""
    files: Dict[str, str] = {}
    folder = work / "public" / "sfx"
    if folder.is_dir():
        for file in sorted(folder.iterdir()):
            if file.is_file() and file.suffix.lower() in AUDIO and file.stem in NAMES:
                files[file.stem] = "sfx/" + file.name
    music: Optional[str] = None
    mfolder = work / "public" / "music"
    if mfolder.is_dir():
        pad = next((f for f in sorted(mfolder.iterdir()) if f.stem == "pad" and f.suffix.lower() in AUDIO), None)
        music = "music/" + pad.name if pad else None
    data = {"files": files, "music": music, "roles": roles(folder)}
    write_atomic(work / "src" / "data" / "sfx.json", json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return data
