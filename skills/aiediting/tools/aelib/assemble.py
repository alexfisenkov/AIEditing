"""The parts a format skill is assembled from: runtime copy, schema, design, tools, pins."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

from .catalog import OPTIONAL_RUNTIME
from .paths import DESIGN_DIR, FORMAT_TEMPLATE, OVERLAY_KIT, RUNTIME_DIR, SCHEMA_DIR

SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
TOOL_FILES = ("run.py", "approvals.py", "issue.py", "notes.py")
KIT_MARK = ".from-aiediting"
KIT_STEPS = {"graphics", "reedit"}  # the steps the model does with the overlay kit
KIT_LEAVE = ("__pycache__", ".DS_Store", "node_modules")
OWN = "own"  # in a draft: what no profile describes, kept beside the built parts


def copy_runtime(stage: Path, packages) -> None:
    """runtime/ of this AIEditing version: top-level modules always, look/render only when a step needs them."""
    target = stage / "runtime"
    target.mkdir()
    for item in sorted(RUNTIME_DIR.iterdir()):
        if item.is_file() and item.suffix == ".py":
            shutil.copy2(str(item), str(target / item.name))
        elif item.is_dir() and (item / "__init__.py").is_file():
            if item.name in OPTIONAL_RUNTIME and item.name not in packages:
                continue
            shutil.copytree(str(item), str(target / item.name), ignore=SKIP)
    shutil.copytree(str(SCHEMA_DIR), str(stage / "schema"), ignore=SKIP)


def copy_design(stage: Path, source: Path, steps=()) -> None:
    """The draft's design/; a format with animations and no templates of its own gets the example's
    (they take colours, fonts and radii from the format's tokens). Graphics get the overlay kit the same way."""
    if source.is_dir():
        shutil.copytree(str(source), str(stage / "design"), ignore=SKIP)
    else:
        (stage / "design").mkdir()
    own, example = stage / "design" / "animations", DESIGN_DIR / "chrome-graphite" / "animations"
    if "animations" in steps and not own.is_dir() and example.is_dir():
        shutil.copytree(str(example), str(own), ignore=SKIP)
    if KIT_STEPS & set(steps):
        _graphics_parts(stage / "design")
    if {"bands", "teaser"} & set(steps):
        _example_design(stage / "design")


def _kit_files(kit: Path) -> dict:
    """{path inside the kit: hash of its bytes} of what the kit is made of; what running it leaves behind does not count."""
    found = {}
    for folder, subs, names in os.walk(str(kit)):
        subs[:] = [s for s in subs if s not in KIT_LEAVE]
        for name in names:
            if name in KIT_LEAVE or name.endswith(".pyc") or name == KIT_MARK:
                continue
            path = Path(folder) / name
            found[path.relative_to(kit).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def _marked(kit: Path) -> dict:
    """What the mark says the kit was when it was copied; {} for a mark older than this list."""
    rows = [line.split("  ", 1) for line in (kit / KIT_MARK).read_text(encoding="utf-8").splitlines()]
    return {row[1]: row[0] for row in rows if len(row) == 2 and len(row[0]) == 64}


def kit_changes(kit: Path) -> list:
    """The kit's files that are not as the workshop copied them. None when the kit has no list to compare with."""
    marked, now = _marked(kit), _kit_files(kit)
    if not marked:
        return None
    return sorted(p for p in set(marked) | set(now) if marked.get(p) != now.get(p))


def _graphics_parts(design: Path) -> None:
    """The kit, and a design to run it with. A kit this workshop copied earlier is renewed, unless someone changed it: then
    the build stops and the person chooses (`ae.py kit`). One the format made its own has no mark and stays."""
    kit = design / "overlay-kit"
    if (kit / KIT_MARK).is_file():
        changed = kit_changes(kit)
        if changed:
            raise ValueError("В design/overlay-kit есть правки после сборки: {}{}. Сборка их не стирает: оставить как свой комплект — "
                             "ae.py kit <скилл> own, отбросить и обновить — ae.py kit <скилл> renew.".format(
                                 ", ".join(changed[:6]), " и ещё {}".format(len(changed) - 6) if len(changed) > 6 else ""))
        if changed is None:
            print("design/overlay-kit скопирован версией без списка файлов: правки в нём сравнить не с чем, он обновлён; прежний "
                  "остался в черновике и в резерве установленной версии.", file=sys.stderr)
        shutil.rmtree(str(kit))
    if not kit.is_dir():
        shutil.copytree(str(OVERLAY_KIT), str(kit), ignore=shutil.ignore_patterns("*.pyc", *KIT_LEAVE))
        rows = ["{}  {}".format(sha, path) for path, sha in sorted(_kit_files(kit).items())]
        (kit / KIT_MARK).write_text("\n".join(["copied by AIEditing; renewed at every build, and the build stops if these files changed"]
                                              + rows) + "\n", encoding="utf-8")
    _example_design(design)


def _example_design(design: Path) -> None:
    """A format that draws and has no design of its own runs on the example, as it did in the trial."""
    if not (design / "tokens.json").is_file():
        example = DESIGN_DIR / "chrome-graphite"
        shutil.copy2(str(example / "tokens.json"), str(design / "tokens.json"))
        shutil.copytree(str(example / "fonts"), str(design / "fonts"), dirs_exist_ok=True)


def copy_tools(stage: Path) -> None:
    (stage / "tools").mkdir()
    for name in TOOL_FILES:
        shutil.copy2(str(FORMAT_TEMPLATE / name), str(stage / "tools" / name))


def copy_own(stage: Path, draft: Path) -> None:
    """Files of the skill no profile describes come back from the draft's `own/` as they were; they never replace a built part."""
    source = draft / OWN
    for item in sorted(source.iterdir()) if source.is_dir() else []:
        target = stage / item.name
        if target.exists():
            raise ValueError("В own/ лежит {}: это имя занято собранной частью скилла, переименуйте".format(item.name))
        if item.is_dir():
            shutil.copytree(str(item), str(target), ignore=SKIP)
        else:
            shutil.copy2(str(item), str(target))


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_pins(stage: Path, profile: dict, need: dict, tools: dict, version: str, skill_md: str = "") -> None:
    pins = {
        "aiediting": version, "runtime": version,
        "built_at": dt.datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "format": profile["format"], "skill_name": profile["skill_name"], "steps": list(profile["steps"]),
        "runtime_packages": need["runtime"],
        "tools": {t: {k: tools[t].get(k) for k in ("pin", "pin_kind", "license", "heavy")} for t in need["tools"]},
        "skill_md": text_hash(skill_md),  # so a later refinement can tell a SKILL.md edited by hand
    }
    (stage / "pins.json").write_text(json.dumps(pins, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
