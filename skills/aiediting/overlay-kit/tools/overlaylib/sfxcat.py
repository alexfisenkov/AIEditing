"""Catalog of a sound folder: role, length, the moment of the peak and its level, measured from the files.

Works for any folder — the kit's `template/public/sfx` and the person's own sounds alike. A sound's role is its
subfolder (`whoosh/whoosh-01.ogg`) or, at the top, one of the old names of `src/kit/Sound.tsx` (`pop-soft.wav`).
The peak is the loudest 10 ms of the envelope: a cue by role starts `peak_ms` early so the peak lands on the event.
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from array import array
from pathlib import Path
from typing import Dict, List, Optional

from .common import ToolError, write_atomic

AUDIO = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".opus"}
CATALOG = "catalog.json"
RATE = 16000
WINDOW = RATE // 100  # 10 ms
ROLES = ["whoosh-soft", "whoosh", "whoosh-big", "drop", "rise", "reverse", "hit", "sub", "ui-appear", "tick", "tap", "shutter",
         "notify", "done", "error", "sparkle", "typing", "transition", "glitch", "ding", "pop", "click", "ambience"]
# the old names a scene may still use (sounds.NAMES) and the role each one plays
OLD_ROLE = {"whoosh-soft": "whoosh-soft", "mouse-click": "click", "switch": "click", "shutter-modern": "shutter",
            "page-turn": "transition", "ding": "ding", "pop-soft": "pop", "tick": "tick", "riser-1s": "rise"}


def role_of(folder: Path, path: Path) -> Optional[str]:
    rel = path.relative_to(folder).parts
    if len(rel) == 1:
        return OLD_ROLE.get(path.stem)
    return rel[0] if len(rel) == 2 and rel[0] in ROLES else None


def _files(folder: Path) -> List[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO)


def left_out(folder: Path) -> List[str]:
    """Sound files of the folder that have no role and so are not in its catalog."""
    folder = Path(folder)
    return [str(p.relative_to(folder)).replace("\\", "/") for p in _files(folder) if role_of(folder, p) is None]


def _samples(path: Path) -> array:
    if not shutil.which("ffmpeg"):
        raise ToolError("Нет программы ffmpeg: без неё каталог звуков не построить")
    done = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(path), "-ac", "1",
                           "-ar", str(RATE), "-f", "s16le", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          stdin=subprocess.DEVNULL)
    if done.returncode != 0:
        raise ToolError("Звук {} не читается: {}".format(path.name, done.stderr.decode("utf-8", "replace").strip()[-200:]))
    data = array("h")
    data.frombytes(done.stdout[: len(done.stdout) // 2 * 2])
    return data


def measure(path: Path) -> Dict[str, float]:
    """dur_ms, peak_ms (the middle of the loudest 10 ms) and level_db (sample peak, dBFS) of one file."""
    data = _samples(Path(path))
    best, at = -1.0, 0
    for start in range(0, max(1, len(data)), WINDOW):
        chunk = data[start:start + WINDOW]
        energy = sum(s * s for s in chunk) / max(1, len(chunk))
        if energy > best:
            best, at = energy, start
    top = max((abs(s) for s in data), default=0)
    dur = int(round(len(data) * 1000 / RATE))
    peak = min(dur, int(round((at + min(WINDOW, len(data) - at) / 2) * 1000 / RATE)))
    level = round(20 * math.log10(top / 32768.0), 1) if top else -96.0
    return {"dur_ms": dur, "peak_ms": peak, "level_db": level}


def build(folder) -> Dict:
    """{"sounds": [{role, file, dur_ms, peak_ms, level_db}]} in the order of ROLES; a role's top-level file comes first."""
    folder = Path(folder).expanduser()
    if not folder.is_dir():
        raise ToolError("Нет папки звуков: {}".format(folder))
    rows = []
    for path in _files(folder):
        role = role_of(folder, path)
        if role is not None:
            rel = str(path.relative_to(folder)).replace("\\", "/")
            rows.append(dict({"role": role, "file": rel}, **measure(path)))
    rows.sort(key=lambda r: (ROLES.index(r["role"]), "/" in r["file"], r["file"]))
    return {"sounds": rows}


def write(folder) -> Path:
    """catalog.json beside the sounds; returns its path."""
    folder = Path(folder).expanduser()
    data = build(folder)
    path = folder / CATALOG
    write_atomic(path, json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    return path


def read(folder: Path) -> List[Dict]:
    """The rows of a folder's catalog.json, or [] when it has none."""
    path = Path(folder) / CATALOG
    if not path.is_file():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8")).get("sounds") or []
    except (ValueError, AttributeError):
        raise ToolError("{} испорчен: постройте его заново (overlay.py sfxcat {})".format(path, folder))
    return [r for r in rows if isinstance(r, dict) and r.get("role") in ROLES and r.get("file")]
