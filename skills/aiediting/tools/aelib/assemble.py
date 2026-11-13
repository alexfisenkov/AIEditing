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
SETUP_FILES = ("setup.py", "checks.py", "installers.py", "downloads.py", "archives.py",
               "npm.py", "bootstrap.py", "paths.py")
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
    elif "music" in steps:
        _sound_parts(stage / "design")
    if {"bands", "teaser", "publish_pack"} & set(steps):  # publish_pack: `run.py covers` draws in the format's design
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


def _sound_parts(design: Path) -> None:
    """Music without graphics still puts sounds by role on the plates (`params.sfx.roles`): the kit's sounds and their
    `catalog.json` only, where `pipelines/music.py` looks for them, marked as copied by this workshop."""
    kit = design / "overlay-kit"
    sfx = kit / "template" / "public" / "sfx"
    if (kit / KIT_MARK).is_file() and not kit_changes(kit):
        shutil.rmtree(str(kit))
    if kit.is_dir():  # a kit of the format's own, or one changed by hand, stays as it is
        return
    shutil.copytree(str(OVERLAY_KIT / "template" / "public" / "sfx"), str(sfx), ignore=shutil.ignore_patterns("*.pyc", *KIT_LEAVE))
    rows = ["{}  {}".format(sha, path) for path, sha in sorted(_kit_files(kit).items())]
    (kit / KIT_MARK).write_text("\n".join(["copied by AIEditing: the kit's sounds only, renewed at every build"] + rows) + "\n",
                                encoding="utf-8")


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


def copy_toolkit_support(stage: Path, need: dict, tools: dict) -> None:
    """Package selected installers and pinned locks so the built skill repairs itself without AIEditing."""
    support = stage / "tools" / "aelib"
    support.mkdir()
    (support / "__init__.py").write_text("", encoding="utf-8")
    source = Path(__file__).resolve().parent
    for name in SETUP_FILES:
        shutil.copy2(str(source / name), str(support / name))
    # The workshop session module imports its dashboard state. A built format needs only its error type.
    (support / "session.py").write_text("class CliError(Exception):\n    pass\n", encoding="utf-8")
    # A built format needs only tool rows. The workshop's catalog also loads presets and steps.
    (support / "catalog.py").write_text(
        "import json\nfrom pathlib import Path\n"
        "from .paths import CATALOG_DIR\n"
        "def tools(base=None):\n"
        "    return {r['id']: r for r in json.loads(((base or CATALOG_DIR) / 'tools.json').read_text(encoding='utf-8'))['tools']}\n",
        encoding="utf-8",
    )
    wanted = set(need["tools"])
    pending = list(wanted)
    while pending:
        dependency = tools[pending.pop()].get("needs") or []
        for name in ([dependency] if isinstance(dependency, str) else dependency):
            if name not in tools:
                raise ValueError("Неизвестная зависимость инструмента: {}".format(name))
            if name not in wanted:
                wanted.add(name)
                pending.append(name)
    catalog = stage / "catalog"
    catalog.mkdir()
    rows = []
    for name in tools:
        if name not in wanted:
            continue
        row = json.loads(json.dumps(tools[name]))
        for spec in row.get("install", {}).values():
            if spec.get("kind") == "npm" and spec.get("lock"):
                lock_source = (source.parent.parent / "catalog" / spec["lock"]).resolve()
                lock_target = catalog / "locks" / name
                lock_target.mkdir(parents=True, exist_ok=True)
                for file in ("package.json", "package-lock.json"):
                    shutil.copy2(str(lock_source / file), str(lock_target / file))
                spec["lock"] = "locks/" + name
        rows.append(row)
    (catalog / "tools.json").write_text(json.dumps({"tools": rows}, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")


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
    copy_toolkit_support(stage, need, tools)
    pins = {
        "aiediting": version, "runtime": version,
        "built_at": dt.datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "format": profile["format"], "skill_name": profile["skill_name"], "steps": list(profile["steps"]),
        "runtime_packages": need["runtime"],
        "tools": {t: {k: tools[t].get(k) for k in ("pin", "pin_kind", "license", "heavy")} for t in need["tools"]},
        "skill_md": text_hash(skill_md),  # so a later refinement can tell a SKILL.md edited by hand
    }
    (stage / "pins.json").write_text(json.dumps(pins, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
