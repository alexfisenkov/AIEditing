"""Reserve copies of format skills: `~/.agents/skills/.aiediting-backups/<name>-<YYYYmmdd-HHMMSS>/`."""
from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path
from typing import List, Optional

from .paths import agents_skills, backups_dir

SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def _free(name: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = backups_dir() / "{}-{}".format(name, stamp)
    path, n = base, 2
    while path.exists():
        path, n = Path("{}-{}".format(base, n)), n + 1
    return path


def move_to_backup(name: str, current: Path) -> str:
    target = _free(name)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(current), str(target))
    return target.name


def copy_to_backup(name: str) -> str:
    current = agents_skills() / name
    if not current.is_dir():
        raise FileNotFoundError("Скилл {} не установлен в {}".format(name, agents_skills()))
    target = _free(name)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(current), str(target), ignore=SKIP)
    return target.name


def backups_of(name: str) -> List[Path]:
    """Newest first. `<name>-<date>-<time>[-n]` — the name itself may contain hyphens."""
    root = backups_dir()
    found = [p for p in root.glob(name + "-*") if p.is_dir() and p.name[len(name) + 1:][:8].isdigit()]
    return sorted(found, key=lambda p: p.name[len(name) + 1:], reverse=True)


def pick_backup(name: str, backup_id: Optional[str] = None) -> Path:
    found = backups_of(name)
    if backup_id:
        found = [p for p in found if p.name == backup_id]
    if not found:
        raise FileNotFoundError("Резервной копии {} нет в {}".format(backup_id or name, backups_dir()))
    return found[0]
