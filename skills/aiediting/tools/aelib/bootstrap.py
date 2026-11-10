"""Select a compatible private Python; bootstrap 3.14 privately with pinned uv if needed."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .paths import WIN, _python_at, home, legacy_venv_dir, toolkit_venv_dir
from .session import CliError

MIN_PYTHON = (3, 12)
MAX_PYTHON = (3, 14)
MANAGED_PYTHON = "3.14"  # newest branch supported by the pinned ONNX Runtime wheels
UV_PIN = "0.13.7"


def _run(argv: list[str], env=None) -> None:
    try:
        done = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env=env)
    except OSError as exc:
        raise CliError("Не удалось запустить {}: {}".format(argv[0], exc)) from exc
    if done.returncode != 0:
        tail = "\n".join(((done.stdout or "") + (done.stderr or "")).splitlines()[-6:])
        raise CliError("Подготовка Python завершилась с кодом {}: {}".format(done.returncode, tail))


def python_version(command) -> tuple[int, int] | None:
    argv = [str(x) for x in command] if isinstance(command, (list, tuple)) else [str(command)]
    try:
        done = subprocess.run(argv + ["-c", "import sys; print('{}.{}'.format(*sys.version_info[:2]))"],
                              capture_output=True, text=True, timeout=20)
        if done.returncode == 0:
            major, minor = done.stdout.strip().split(".")
            return int(major), int(minor)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return None


def private_candidates() -> list[Path]:
    modern = toolkit_venv_dir()
    return ([_python_at(modern)] if (modern / "toolkit.ready").is_file() else []) + [_python_at(legacy_venv_dir())]


def _external_candidates() -> list[list[str]]:
    candidates = [[sys.executable]]
    for name in ("python3.14", "python3.13", "python3.12"):
        found = shutil.which(name)
        if found:
            candidates.append([found])
    if WIN and shutil.which("py"):
        for version in ("3.14", "3.13", "3.12"):
            candidates.append([shutil.which("py"), "-" + version])
    return candidates


def _bootstrap_with_uv(dest: Path) -> None:
    base = dest.parent
    bootstrap = base / "bootstrap-venv"
    uv = bootstrap / ("Scripts/uv.exe" if WIN else "bin/uv")
    if not _python_at(bootstrap).is_file():
        _run([sys.executable, "-m", "venv", str(bootstrap)])
    _run([str(_python_at(bootstrap)), "-m", "pip", "install", "--disable-pip-version-check",
          "uv==" + UV_PIN])
    env = dict(os.environ, UV_PYTHON_INSTALL_DIR=str(base / "python"), UV_CACHE_DIR=str(base / "uv-cache"))
    _run([str(uv), "python", "install", MANAGED_PYTHON], env=env)
    _run([str(uv), "venv", "--seed", "--python", MANAGED_PYTHON, str(dest)], env=env)


def ensure_python() -> Path:
    """Return private Python 3.12–3.14, with no global installation or PATH change."""
    for path in private_candidates():
        if path.is_file() and MIN_PYTHON <= (python_version(path) or (0, 0)) <= MAX_PYTHON:
            return path
    dest = toolkit_venv_dir()
    if dest.exists():
        raise CliError("{} существует, но Python в нём непригоден; сохраните папку для диагностики и восстановите окружение".format(dest))
    dest.parent.mkdir(parents=True, exist_ok=True)
    available = [(python_version(cmd), cmd) for cmd in _external_candidates()]
    modern = [(version, cmd) for version, cmd in available if version and MIN_PYTHON <= version <= MAX_PYTHON]
    try:
        if modern:
            _, command = max(modern, key=lambda item: item[0])
            _run(command + ["-m", "venv", str(dest)])
        else:
            _bootstrap_with_uv(dest)
        py = _python_at(dest)
        version = python_version(py) or (0, 0)
        if not MIN_PYTHON <= version <= MAX_PYTHON:
            raise CliError("{} создан, но не содержит Python 3.12–3.14".format(dest))
        _run([str(py), "-m", "pip", "--version"])
        (dest / "toolkit.ready").write_text("{}.{}\n".format(*version), encoding="utf-8")
        return py
    except BaseException:
        if dest.is_dir() and not (dest / "toolkit.ready").is_file():
            shutil.rmtree(dest)
        raise
