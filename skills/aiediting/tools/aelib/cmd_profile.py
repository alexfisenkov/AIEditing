"""Formats and draft profiles in the workshop folder: `<work>/<skill>/profile.json` + `design/`."""
from __future__ import annotations

import shutil
from pathlib import Path

import state as st

from . import formats, profiles, session
from .install import find_installed
from .paths import DESIGN_DIR
from .session import CliError


def draft(skill: str) -> Path:
    return session.work() / skill / "profile.json"


def _remember(data: dict, fmt: dict, path: Path) -> None:
    rows = [f for f in data.setdefault("formats", []) if f["skill"] != fmt["skill"]]
    rows.append(dict(fmt, profile=st.rel(session.work(), path)))
    data["formats"] = rows


def cmd_formats(opt) -> str:
    chosen = formats.parse_answer(opt.answer)
    lines = []
    for fmt in chosen:
        path = draft(fmt["skill"])
        if not path.is_file():
            profiles.write(profiles.new_profile(fmt, language=opt.language), path)
        session.touch(lambda d, f=fmt, p=path: _remember(d, f, p))
        lines.append("{} — {}{}: {}".format(fmt["skill"], fmt["title"], " (свой)" if fmt["custom"] else "", path))
    return "\n".join(lines)


def cmd_profile(opt) -> str:
    if opt.action == "open":
        return _open(opt.skill, opt.fresh)
    path = draft(opt.skill)
    if not path.is_file():
        raise CliError("Черновика {} нет: сначала ae.py formats или ae.py profile open".format(path))
    profile = profiles.read(path)
    if opt.action == "set":
        profiles.set_values(profile, opt.values)
    elif opt.action == "taste":
        if opt.replace:
            profiles.replace_taste(profile, opt.replace, " ".join(opt.values), video=opt.video or "")
        else:
            profiles.add_taste(profile, " ".join(opt.values), video=opt.video or "")
        session.touch(lambda d: st.log(d, "taste", skill=opt.skill, note=" ".join(opt.values)))
    from runtime.profile import check_profile

    errors = check_profile(profile)
    if opt.action != "check":
        profiles.write(profile, path)
    return "{}: {}".format(path, "в порядке" if not errors else "есть замечания:\n- " + "\n- ".join(errors))


def _open(skill: str, fresh: bool) -> str:
    """Refinement starts from the installed skill: its profile and design come into the workshop."""
    source = find_installed(skill)
    if source is None:
        raise CliError("Скилл {} не найден среди установленных (ae.py list-skills)".format(skill))
    target = session.work() / skill
    if target.exists() and not fresh:
        raise CliError("Черновик {} уже есть — продолжайте его или откройте заново с --fresh".format(target))
    shutil.rmtree(str(target), ignore_errors=True)
    target.mkdir(parents=True)
    shutil.copy2(str(source / "profile.json"), str(target / "profile.json"))
    if (source / "design").is_dir():
        shutil.copytree(str(source / "design"), str(target / "design"))
    profile = profiles.read(target / "profile.json")
    fmt = {"id": "installed", "word": profile["format"], "title": profile["format"], "preset": "custom",
           "skill": skill, "custom": False}
    session.touch(lambda d: _remember(d, fmt, target / "profile.json"))
    return "Открыт для доработки: {} (из {})".format(target, source)


def cmd_design_example(opt) -> str:
    """The bundled example design system (Chrome & Graphite) as the start of this skill's design."""
    found = sorted(p.parent for p in DESIGN_DIR.rglob("tokens.json"))
    if not found:
        raise CliError("В этой версии AIEditing нет примера дизайн-системы — собираем свой стиль")
    target = session.work() / opt.skill / "design"
    for item in found[0].iterdir():
        dst = target / item.name
        if item.is_dir():
            shutil.copytree(str(item), str(dst), dirs_exist_ok=True)
        else:
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(item), str(dst))
    session.touch(lambda d: d["design"].update(example=found[0].name))
    return "Пример {} положен в {}".format(found[0].name, target)
