"""`build-skill`: profile.json → a self-contained `монтаж-<слово>/` with only what the interview chose."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import catalog, profiles, skillmd
from .assemble import copy_design, copy_runtime, copy_tools, write_pins
from .paths import agents_skills, claude_skills


class BuildError(Exception):
    """The profile cannot become a skill; the message says why, in Russian."""


def _errors(profile: dict):
    from runtime.profile import check_profile

    return check_profile(profile) + catalog.check_steps(profile.get("steps") or [])


def _imports(folder: Path):
    probe = "import sys; sys.path.insert(0, sys.argv[1]); import runtime, runtime.profile, runtime.asr, runtime.media, runtime.pipelines"
    proc = subprocess.run([sys.executable, "-I", "-B", "-c", probe, str(folder)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise BuildError("Собранная копия не импортируется сама по себе:\n" + proc.stderr.strip()[-800:])


def _target(dest: Path, name: str, replace: bool) -> Path:
    final = dest / name
    if not final.exists():
        return final
    installed = {agents_skills().resolve(), claude_skills().resolve()}
    if not replace or dest.resolve() in installed or not (final / "pins.json").is_file():
        raise BuildError("Папка {} уже есть. Ставить — командой install-skill (прежняя версия уйдёт "
                         "в резерв); пересобрать в рабочей папке — с --replace.".format(final))
    return final


def build_skill(profile_path, dest, replace: bool = False) -> Path:
    from runtime import __version__

    profile_path, dest = Path(profile_path).resolve(), Path(dest).resolve()
    profile = profiles.read(profile_path)
    errors = _errors(profile)
    if errors:
        raise BuildError("Профиль {} не готов к сборке:\n- {}".format(profile_path, "\n- ".join(errors)))
    final = _target(dest, profile["skill_name"], replace)
    need = catalog.needs(profile["steps"], profile["asr"]["provider"])
    dest.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".build-", dir=str(dest)))
    try:
        copy_runtime(stage, need["runtime"])
        copy_design(stage, profile_path.parent / (profile.get("design") or "design/"))
        copy_tools(stage)
        profile["design"] = "design/"
        profiles.write(profile, stage / "profile.json")
        write_pins(stage, profile, need, catalog.tools(), __version__)
        text = skillmd.render(profile, need, catalog.steps(), catalog.tools(), __version__)
        (stage / "SKILL.md").write_text(text, encoding="utf-8")
        _imports(stage)
        if final.exists():
            shutil.rmtree(str(final))
        stage.rename(final)
    except BaseException:
        shutil.rmtree(str(stage), ignore_errors=True)
        raise
    return final
