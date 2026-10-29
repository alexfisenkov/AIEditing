"""Is a catalog tool present here, and at what version — read-only, never installs."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .paths import venv_python


def current_os() -> str:
    if sys.platform == "darwin":
        return "mac"
    return "win" if os.name == "nt" else "linux"


def argv_of(argv):
    """`{python}` → this interpreter; the program resolved through PATH (npm → npm.cmd on Windows)."""
    out = [sys.executable if a == "{python}" else os.path.expanduser(a) for a in argv]
    out[0] = shutil.which(out[0]) or out[0]
    return out


def _ver(text: str):
    return tuple(int(x) for x in re.findall(r"\d+", text)[:3])


def _command(check: dict, row: dict) -> dict:
    argv = argv_of(check["command"])
    if not (shutil.which(argv[0]) or Path(argv[0]).is_file()):
        return {"ok": False, "version": None, "note": "не найдено в PATH"}
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=20, encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "version": None, "note": "не запускается: {}".format(e)}
    text = (out.stdout or "") + (out.stderr or "")
    m = re.search(check["version"], text) if check.get("version") else None
    version = m.group(1) if m else None
    if version and row.get("pin_kind") == "minimum" and _ver(version) < _ver(row["pin"]):
        return {"ok": False, "version": version, "note": "версия {} старше пина {}".format(version, row["pin"])}
    return {"ok": True, "version": version, "note": "версия {}".format(version) if version else "найдено"}


def _python(module: str) -> dict:
    py = venv_python()
    if not py.is_file():
        return {"ok": False, "version": None, "note": "нет окружения AIEditing ({})".format(py.parent.parent)}
    out = subprocess.run([str(py), "-c", "import " + module], capture_output=True, text=True)
    return {"ok": out.returncode == 0, "version": None,
            "note": "в окружении" if out.returncode == 0 else "не установлено в окружении"}


def _file(check: dict) -> dict:
    """A file by path (per system when a dict); an environment variable may point elsewhere."""
    where = check["file"].get(current_os(), "") if isinstance(check["file"], dict) else check["file"]
    paths = [os.environ.get(check["env"], "")] if check.get("env") else []
    paths.append(os.path.expandvars(os.path.expanduser(where)) if where else "")
    found = next((p for p in paths if p and Path(p).is_file()), None)
    return {"ok": bool(found), "version": None, "note": "файл: {}".format(found) if found else "файла нет: {}".format(paths[-1])}


def status(row: dict) -> dict:
    check = row.get("check") or {}
    if "command" in check:
        return _command(check, row)
    if "python" in check:
        return _python(check["python"])
    if "file" in check:
        return _file(check)
    return {"ok": None, "version": None, "note": "ставится вручную, проверка по месту"}
