"""Is a catalog tool present here, and at what version — read-only, never installs."""
from __future__ import annotations

import os
import hashlib
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


def _system_path_entries() -> list[str]:
    """Read package-manager paths without changing user or system settings."""
    if current_os() == "mac":
        return [str(p) for p in (Path("/opt/homebrew/bin"), Path("/usr/local/bin")) if p.is_dir()]
    if current_os() != "win":
        return []
    try:
        import winreg

        values = []
        for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                          (winreg.HKEY_CURRENT_USER, "Environment")):
            try:
                with winreg.OpenKey(hive, key) as opened:
                    value, _ = winreg.QueryValueEx(opened, "Path")
                    values.extend(os.path.expandvars(value).split(";"))
            except OSError:
                continue
        return values
    except ImportError:
        return []


def _full_ffmpeg_bins() -> list[str]:
    if current_os() != "mac":
        return []
    return [str(folder) for folder in (Path("/opt/homebrew/opt/ffmpeg-full/bin"),
                                      Path("/usr/local/opt/ffmpeg-full/bin"))
            if (folder / "ffmpeg").is_file() and (folder / "ffprobe").is_file()]


def refresh_path() -> None:
    """Make newly installed tools visible in this process; never write the registry or shell profile."""
    separator = ";" if current_os() == "win" else os.pathsep
    current = [part for part in os.environ.get("PATH", "").split(separator) if part]
    full = _full_ffmpeg_bins()
    current = full + [part for part in current if os.path.normcase(part) not in
                      {os.path.normcase(candidate) for candidate in full}]
    seen = {os.path.normcase(part) for part in current}
    for part in _system_path_entries():
        if part and os.path.normcase(part) not in seen:
            current.append(part)
            seen.add(os.path.normcase(part))
    os.environ["PATH"] = separator.join(current)


def argv_of(argv):
    """`{python}` → this interpreter; the program resolved through PATH (npm → npm.cmd on Windows)."""
    out = [sys.executable if a == "{python}" else os.path.expanduser(a) for a in argv]
    if out[0] in ("ffmpeg", "ffprobe"):
        direct = os.environ.get("AIEDITING_" + out[0].upper())
        if not direct and out[0] == "ffprobe" and os.environ.get("AIEDITING_FFMPEG"):
            direct = str(Path(os.environ["AIEDITING_FFMPEG"]).with_name(
                "ffprobe.exe" if current_os() == "win" else "ffprobe"))
        if direct:
            out[0] = os.path.expanduser(direct)
    if out[0] == "whisper-cli" and current_os() == "win":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            private = Path(base) / "AIEditing" / "bin" / "whisper-cpp" / "whisper-cli.exe"
            if private.is_file():
                out[0] = str(private)
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
    if out.returncode != 0:
        return {"ok": False, "version": None, "note": "команда завершилась с кодом {}".format(out.returncode)}
    m = re.search(check["version"], text) if check.get("version") else None
    version = m.group(1) if m else None
    if check.get("version") and not version:
        return {"ok": False, "version": None, "note": "версию определить не удалось"}
    if version and row.get("pin_kind") == "minimum" and _ver(version) < _ver(row["pin"]):
        return {"ok": False, "version": version, "note": "версия {} старше пина {}".format(version, row["pin"])}
    required = check.get("required_filters") or []
    if required:
        available = set()
        for line in text.splitlines():
            fields = line.split()
            if len(fields) >= 2 and 2 <= len(fields[0]) <= 3 and set(fields[0]) <= set(".TSC"):
                available.add(fields[1])
        missing = [name for name in required if name not in available]
        if missing:
            return {"ok": False, "version": version, "note": "нет фильтров: " + ", ".join(missing)}
    if check.get("also"):
        companion = _command(check["also"], row)
        if companion["ok"] is not True:
            return {"ok": False, "version": version,
                    "note": "{}: {}".format(check["also"]["command"][0], companion["note"])}
        if version and companion["version"] and version != companion["version"]:
            return {"ok": False, "version": version, "note": "версии ffmpeg и ffprobe отличаются"}
    return {"ok": True, "version": version, "note": "версия {}".format(version) if version else "найдено"}


def _python(module: str, row: dict) -> dict:
    py = venv_python()
    if not py.is_file():
        return {"ok": False, "version": None, "note": "нет окружения AIEditing ({})".format(py.parent.parent)}
    step = row["install"].get(current_os(), {})
    dist = step.get("package", module).split("==", 1)[0].split("[", 1)[0]
    script = ("import importlib, importlib.metadata, sys; "
              "importlib.import_module(sys.argv[1]); "
              "print(importlib.metadata.version(sys.argv[2])); "
              "print('{}.{}'.format(*sys.version_info[:2]))")
    try:
        out = subprocess.run([str(py), "-c", script, module, dist], capture_output=True, text=True,
                             timeout=row.get("check", {}).get("timeout", 20), encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return {"ok": False, "version": None, "note": "импорт превысил лимит времени {} с".format(
            row.get("check", {}).get("timeout", 20))}
    except (OSError, subprocess.SubprocessError):
        return {"ok": False, "version": None, "note": "модуль не запускается в окружении"}
    if out.returncode != 0:
        return {"ok": False, "version": None, "note": "не установлено в окружении"}
    lines = out.stdout.splitlines()
    if len(lines) < 2:
        return {"ok": False, "version": None, "note": "версию определить не удалось"}
    from .installers import pip_package
    expected = pip_package(step, tuple(int(x) for x in lines[-1].split("."))).split("==", 1)[-1]
    version = lines[-2].strip()
    return {"ok": version == expected, "version": version,
            "note": "версия {} в окружении".format(version) if version == expected else
                    "версия {} вместо пина {}".format(version, expected)}


def _file(check: dict, row: dict) -> dict:
    """A file by path (per system when a dict); an environment variable may point elsewhere."""
    where = check["file"].get(current_os(), "") if isinstance(check["file"], dict) else check["file"]
    paths = [os.environ.get(check["env"], "")] if check.get("env") else []
    paths.append(os.path.expandvars(os.path.expanduser(where)) if where else "")
    found = next((p for p in paths if p and Path(p).is_file()), None)
    if found:
        expected = row.get("install", {}).get(current_os(), {}).get("sha256")
        if expected:
            digest = hashlib.sha256()
            try:
                with Path(found).open("rb") as source:
                    for piece in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(piece)
            except OSError:
                return {"ok": False, "version": None, "note": "файл не читается: {}".format(found)}
            if digest.hexdigest().lower() != expected.lower():
                return {"ok": False, "version": None, "note": "контрольная сумма файла не совпала: {}".format(found)}
    return {"ok": bool(found), "version": None, "note": "файл: {}".format(found) if found else "файла нет: {}".format(paths[-1])}


def status(row: dict) -> dict:
    check = row.get("check") or {}
    if "npm" in check:
        from .npm import npm_status

        return npm_status(check["npm"], row)
    if "command" in check:
        return _command(check, row)
    if "python" in check:
        return _python(check["python"], row)
    if "file" in check:
        return _file(check, row)
    return {"ok": None, "version": None, "note": "ставится вручную, проверка по месту"}
