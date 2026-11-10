"""Where things live: the skill itself, the workshop folder, the user's skill roots."""
from __future__ import annotations

import os
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2]
TOOLS_DIR = SKILL_DIR / "tools"
CATALOG_DIR = SKILL_DIR / "catalog"
TEMPLATES_DIR = SKILL_DIR / "templates"
FORMAT_TEMPLATE = TEMPLATES_DIR / "format-skill"
PRESETS_DIR = TEMPLATES_DIR / "profiles"
RUNTIME_DIR = SKILL_DIR / "runtime"
SCHEMA_DIR = SKILL_DIR / "schema"
DESIGN_DIR = SKILL_DIR / "design"
OVERLAY_KIT = SKILL_DIR / "overlay-kit"
STATE_TEMPLATE = TOOLS_DIR / "state" / "dashboard.html"

WORK_NAME = ".aiediting-work"
BACKUPS_NAME = ".aiediting-backups"
WIN = os.name == "nt"


def work_dir(base=None) -> Path:
    """The workshop folder: frames, trials, drafts and the dashboard. AIEDITING_WORK overrides."""
    env = os.environ.get("AIEDITING_WORK")
    if env:
        return Path(env).expanduser().resolve()
    return (Path(base) if base else Path.cwd()).resolve() / WORK_NAME


def home() -> Path:
    return Path.home()


def agents_skills() -> Path:
    return home() / ".agents" / "skills"


def claude_skills() -> Path:
    return home() / ".claude" / "skills"


def backups_dir() -> Path:
    return agents_skills() / BACKUPS_NAME


def _python_at(folder: Path) -> Path:
    return folder / ("Scripts/python.exe" if WIN else "bin/python")


def legacy_venv_dir() -> Path:
    """The original AIEditing private environment, kept for existing installations."""
    if WIN and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "AIEditing" / "venv"
    return home() / ".aiediting" / "venv"


def toolkit_venv_dir() -> Path:
    """Modern private Python for packages whose latest releases need Python 3.12+."""
    if WIN and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "AIEditing" / "toolkit-venv"
    return home() / ".aiediting" / "toolkit-venv"


def venv_dir() -> Path:
    modern = toolkit_venv_dir()
    return modern if _python_at(modern).is_file() and (modern / "toolkit.ready").is_file() else legacy_venv_dir()


def venv_python() -> Path:
    return _python_at(venv_dir())
