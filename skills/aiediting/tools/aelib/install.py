"""Format skills installed globally: `~/.agents/skills/<name>/` plus a pointer in `~/.claude/skills/`.

The previous version always goes to `~/.agents/skills/.aiediting-backups/<name>-<time>/` first.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import List, Optional

from .backups import move_to_backup, pick_backup
from .paths import agents_skills, claude_skills

SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


class InstallError(Exception):
    """Refused before anything changed; the message says why, in Russian."""


def is_format_skill(folder: Path) -> bool:
    try:
        pins = json.loads((Path(folder) / "pins.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return "aiediting" in pins and (Path(folder) / "profile.json").is_file()


def find_installed(name: str) -> Optional[Path]:
    for root in (agents_skills(), claude_skills()):
        if is_format_skill(root / name):
            return (root / name).resolve()
    return None


def _check_pointer(ptr: Path) -> None:
    if ptr.exists() and not ptr.is_symlink() and not is_format_skill(ptr):
        raise InstallError("{} — чужая папка, не скилл AIEditing; её не трогаю. Уберите или "
                           "переименуйте её сами и повторите.".format(ptr))


def _point(name: str) -> str:
    ptr = claude_skills() / name
    if ptr.is_symlink():
        ptr.unlink()
    elif ptr.exists():
        shutil.rmtree(str(ptr))
    ptr.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(os.path.join("..", "..", ".agents", "skills", name), str(ptr), target_is_directory=True)
        return "symlink"
    except (OSError, NotImplementedError):
        shutil.copytree(str(agents_skills() / name), str(ptr), ignore=SKIP)
        return "copy"


def install_skill(built) -> dict:
    built = Path(built).resolve()
    if not is_format_skill(built) or not (built / "SKILL.md").is_file():
        raise InstallError("{} — не собранный скилл формата (нет SKILL.md, profile.json или pins.json)".format(built))
    name, dst = built.name, agents_skills() / built.name
    if dst.resolve() == built:
        raise InstallError("Это уже установленная копия; соберите новую в рабочей папке и ставьте её")
    _check_pointer(claude_skills() / name)
    backup = move_to_backup(name, dst) if dst.exists() else None
    shutil.copytree(str(built), str(dst), ignore=SKIP)
    return {"name": name, "path": str(dst), "pointer": _point(name), "backup": backup}


def restore_skill(name: str, backup_id: Optional[str] = None) -> dict:
    chosen = pick_backup(name, backup_id)
    _check_pointer(claude_skills() / name)
    dst = agents_skills() / name
    saved = move_to_backup(name, dst) if dst.exists() else None
    shutil.move(str(chosen), str(dst))
    return {"name": name, "path": str(dst), "pointer": _point(name), "restored": chosen.name, "backup": saved}


def list_skills() -> List[dict]:
    out, seen = [], set()
    for root in (agents_skills(), claude_skills()):
        for folder in sorted(root.glob("*")) if root.is_dir() else []:
            real = folder.resolve()
            if real in seen or folder.name.startswith(".") or not is_format_skill(real):
                continue
            seen.add(real)
            pins = json.loads((real / "pins.json").read_text(encoding="utf-8"))
            out.append({"name": folder.name, "format": pins.get("format"), "version": pins.get("aiediting"),
                        "built_at": pins.get("built_at"), "steps": pins.get("steps", []), "path": str(real)})
    return out
