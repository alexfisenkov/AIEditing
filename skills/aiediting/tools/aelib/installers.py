"""Installing one catalog row by its pin. Called only by `doctor --install <id> --yes`."""
from __future__ import annotations

import subprocess
import sys

from .checks import argv_of, current_os
from .paths import home, venv_dir, venv_python


def _run(argv) -> str:
    proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = "\n".join(((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()[-5:])
    if proc.returncode != 0:
        return "не получилось (код {}):\n{}".format(proc.returncode, tail)
    return "поставлено" + ("\n" + tail if tail else "")


def _venv() -> str:
    if venv_python().is_file():
        return ""
    venv_dir().parent.mkdir(parents=True, exist_ok=True)
    return _run([sys.executable, "-m", "venv", str(venv_dir())])


def run_install(row: dict) -> str:
    step = row["install"].get(current_os())
    if not step:
        return "На этой системе {} не ставится".format(row["id"])
    kind = step["kind"]
    if kind == "manual":
        where = " и сохраните как {}".format(step["save_to"]) if step.get("save_to") else ""
        return "Ставится вручную: скачайте с {}{}; вернитесь, когда готово.".format(step["url"], where)
    if kind == "command":
        return _run(argv_of(step["argv"]))
    if kind == "pip":
        made = _venv()
        if made.startswith("не получилось"):
            return made
        return _run([str(venv_python()), "-m", "pip", "install", "--disable-pip-version-check", step["package"]])
    if kind == "npm":
        prefix = home() / ".aiediting" / "node"
        prefix.mkdir(parents=True, exist_ok=True)
        return _run(argv_of(["npm", "install", "--prefix", str(prefix), "--save-exact", step["package"]]))
    return "Неизвестный способ установки {!r}".format(kind)
