"""build-skill, install-skill, list-skills, backup-skill, restore-skill — and their marks on the dashboard."""
from __future__ import annotations

import json

import state as st

from . import backups, session
from .build import BuildError, build_skill
from .install import InstallError, install_skill, list_skills, restore_skill
from .session import CliError


def _mark(name: str, **kw) -> None:
    def change(d):
        rows = [s for s in d.setdefault("skills", []) if s["name"] != name]
        old = next((s for s in d["skills"] if s["name"] == name), {})
        rows.append(dict(old, name=name, at=st.now(), **kw))
        d["skills"] = rows
        st.log(d, "skill", skill=name, **{k: v for k, v in kw.items() if isinstance(v, str)})

    session.touch(change)


def cmd_build(opt) -> str:
    try:
        folder = build_skill(opt.profile, opt.dest, replace=opt.replace)
    except BuildError as e:
        raise CliError(str(e))
    _mark(folder.name, built=str(folder))
    return "Собран: {}".format(folder)


def cmd_install(opt) -> str:
    try:
        done = install_skill(opt.folder)
    except InstallError as e:
        raise CliError(str(e))
    _mark(done["name"], installed=done["path"], backup=done["backup"])
    reserve = "прежняя версия в резерве: {}".format(done["backup"]) if done["backup"] else "первая установка"
    return "Установлен глобально: {} (указатель в ~/.claude/skills — {}); {}. Скилл виден в новой сессии.".format(
        done["path"], "ссылка" if done["pointer"] == "symlink" else "копия", reserve)


def cmd_list(opt) -> str:
    rows = list_skills()
    if opt.json:
        return json.dumps(rows, ensure_ascii=False, indent=2)
    if not rows:
        return "Скиллов монтажа, собранных AIEditing, пока нет."
    return "\n".join("{name} — формат «{format}», версия {version}, собран {built_at}".format(**r) for r in rows)


def cmd_backup(opt) -> str:
    try:
        made = backups.copy_to_backup(opt.name)
    except FileNotFoundError as e:
        raise CliError(str(e))
    return "Резервная копия: {}".format(made)


def cmd_restore(opt) -> str:
    if opt.list:
        found = backups.backups_of(opt.name)
        return "\n".join(p.name for p in found) or "Резервных копий {} нет".format(opt.name)
    try:
        done = restore_skill(opt.name, opt.backup)
    except (FileNotFoundError, InstallError) as e:
        raise CliError(str(e))
    _mark(done["name"], installed=done["path"], restored=done["restored"])
    return "Возвращена версия {} → {}; заменённая ушла в резерв: {}".format(
        done["restored"], done["path"], done["backup"] or "—")
