"""The parts a format skill is assembled from: runtime copy, schema, design, tools, pins."""
from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path

from .catalog import OPTIONAL_RUNTIME
from .paths import DESIGN_DIR, FORMAT_TEMPLATE, OVERLAY_KIT, RUNTIME_DIR, SCHEMA_DIR

SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
TOOL_FILES = ("run.py", "approvals.py", "issue.py", "notes.py")
KIT_MARK = ".from-aiediting"


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
    if "graphics" in steps:
        _graphics_parts(stage / "design")


def _graphics_parts(design: Path) -> None:
    """The kit, and a design to run it with. A kit this workshop copied earlier is renewed; one the format made its
    own has no mark and stays."""
    kit = design / "overlay-kit"
    if (kit / KIT_MARK).is_file():
        shutil.rmtree(str(kit))
    if not kit.is_dir():
        shutil.copytree(str(OVERLAY_KIT), str(kit), ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "node_modules"))
        (kit / KIT_MARK).write_text("copied by AIEditing; renewed at every build\n", encoding="utf-8")
    if not (design / "tokens.json").is_file():
        example = DESIGN_DIR / "chrome-graphite"
        shutil.copy2(str(example / "tokens.json"), str(design / "tokens.json"))
        shutil.copytree(str(example / "fonts"), str(design / "fonts"), dirs_exist_ok=True)


def copy_tools(stage: Path) -> None:
    (stage / "tools").mkdir()
    for name in TOOL_FILES:
        shutil.copy2(str(FORMAT_TEMPLATE / name), str(stage / "tools" / name))


def write_pins(stage: Path, profile: dict, need: dict, tools: dict, version: str) -> None:
    pins = {
        "aiediting": version, "runtime": version,
        "built_at": dt.datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "format": profile["format"], "skill_name": profile["skill_name"], "steps": list(profile["steps"]),
        "runtime_packages": need["runtime"],
        "tools": {t: {k: tools[t].get(k) for k in ("pin", "pin_kind", "license", "heavy")} for t in need["tools"]},
    }
    (stage / "pins.json").write_text(json.dumps(pins, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
