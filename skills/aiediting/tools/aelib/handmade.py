"""What a profile does not describe: a `монтаж-*` skill written by hand or by someone else, and the parts of a built skill
added after its build. None of it is thrown away by a refinement; it is opened, changed with the person and kept.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from .assemble import KIT_MARK, kit_changes, text_hash
from .backups import move_to_backup, pick_backup
from .formats import PREFIX
from .install import SKIP, InstallError, is_format_skill
from .paths import agents_skills, backups_dir, claude_skills

BUILT = {"SKILL.md", "profile.json", "pins.json", "runtime", "schema", "tools", "design", "catalog"}  # what a build makes
AS_INSTALLED = "SKILL.как-установлен.md"  # beside the draft: a SKILL.md edited by hand, to carry over with the person
COPY = "скилл"  # in the workshop: the working copy of a skill without a profile
LEAVE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "node_modules")


def found(name: str) -> Optional[Path]:
    """Where a skill with no profile lives, its real folder; None for a built skill or none at all."""
    for root in (agents_skills(), claude_skills()):
        folder = root / name
        if (folder / "SKILL.md").is_file() and not is_format_skill(folder):
            return folder.resolve()
    return None


def listing() -> List[Dict[str, str]]:
    out, seen = [], set()
    for root in (agents_skills(), claude_skills()):
        for folder in sorted(root.glob(PREFIX + "*")) if root.is_dir() else []:
            real = found(folder.name)
            if real is not None and real not in seen:
                seen.add(real)
                out.append({"name": folder.name, "path": str(real)})
    return out


def open_copy(source: Path, target: Path) -> Path:
    copy = target / COPY / source.name
    shutil.copytree(str(source), str(copy), ignore=LEAVE)
    return copy


def own_parts(source: Path, own: Path) -> List[str]:
    """A built skill's parts beyond its build go to the draft's `own/`, and the build puts them back. Returns what to tell."""
    said = []
    extra = [p for p in sorted(source.iterdir()) if p.name not in BUILT and not p.name.startswith(".")]
    for item in extra:
        own.mkdir(parents=True, exist_ok=True)
        if item.is_dir():
            shutil.copytree(str(item), str(own / item.name), ignore=LEAVE)
        else:
            shutil.copy2(str(item), str(own / item.name))
    if extra:
        said.append("Своё, чего нет в профиле, останется в скилле: {} (лежит в {})".format(", ".join(p.name for p in extra), own))
    kit = source / "design" / "overlay-kit"
    if kit.is_dir() and not (kit / KIT_MARK).is_file():
        said.append("Свой комплект design/overlay-kit: при сборке не обновляется, правится вместе с человеком")
    elif kit.is_dir() and kit_changes(kit):
        said.append("В design/overlay-kit есть правки после сборки: {}. Спросите человека, потом ae.py kit <скилл> own или renew, иначе "
                    "сборка остановится".format(", ".join(kit_changes(kit)[:6])))
    if (source / "design" / "method.md").is_file():
        said.append("Свой метод design/method.md: остаётся в SKILL.md, правится вместе с человеком")
    said += _edited(source, own.parent)
    return said


def _edited(source: Path, draft: Path) -> List[str]:
    text = (source / "SKILL.md").read_text(encoding="utf-8")
    try:
        built = json.loads((source / "pins.json").read_text(encoding="utf-8")).get("skill_md")
    except (OSError, ValueError):
        built = None
    if built == text_hash(text):
        return []
    (draft / AS_INSTALLED).write_text(text, encoding="utf-8")
    start = "SKILL.md правили после сборки" if built else "Скилл собран до того, как это отслеживалось: SKILL.md мог меняться после сборки"
    return ["{}. Сборка пишет его заново: сверьте {} и всё своё перенесите в design/method.md, он войдёт в новый SKILL.md".format(start, AS_INSTALLED)]


def _packages_back(old: Path, new: Path) -> List[str]:
    """`node_modules` are left out of the working copy: heavy, and made by a lockfile. They move over from the version replaced."""
    moved = []
    for folder, subs, _ in os.walk(str(old)):
        if "node_modules" in subs:
            subs.remove("node_modules")
            rel = Path(folder).relative_to(old) / "node_modules"
            if (new / rel.parent).is_dir() and not (new / rel).exists():
                shutil.move(str(old / rel), str(new / rel))
                moved.append(rel.as_posix())
    return moved


def install(folder) -> dict:
    """The edited copy back to where the skill lives, whole or not at all: it is copied under another name beside the skill and
    takes its place only then; what it replaces goes to the reserve."""
    folder = Path(folder).resolve()
    origin = found(folder.name)
    if origin is None or not (folder / "SKILL.md").is_file():
        raise InstallError("{}: нет такого установленного скилла без профиля".format(folder.name))
    if origin == folder:
        raise InstallError("Это уже установленная копия; правьте копию из ae.py profile open")
    fresh = origin.with_name("." + origin.name + ".новая")
    shutil.rmtree(str(fresh), ignore_errors=True)
    try:
        shutil.copytree(str(folder), str(fresh), ignore=SKIP)
    except BaseException:
        shutil.rmtree(str(fresh), ignore_errors=True)
        raise
    backup = move_to_backup(folder.name, origin)
    os.replace(str(fresh), str(origin))
    return {"name": folder.name, "path": str(origin), "backup": backup, "packages": _packages_back(backups_dir() / backup, origin)}


def restore(name: str, backup_id: Optional[str] = None) -> dict:
    origin = found(name)
    if origin is None:
        raise InstallError("{}: нет такого установленного скилла без профиля".format(name))
    chosen = pick_backup(name, backup_id)
    saved = move_to_backup(name, origin)
    shutil.move(str(chosen), str(origin))
    return {"name": name, "path": str(origin), "restored": chosen.name, "backup": saved,
            "packages": _packages_back(backups_dir() / saved, origin)}
