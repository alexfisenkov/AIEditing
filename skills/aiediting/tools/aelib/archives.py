"""Install a checksum-pinned official Windows whisper.cpp CPU archive in a private folder."""
from __future__ import annotations

import hashlib
import os
import platform
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from .downloads import fetch
from .session import CliError


def _architecture() -> str:
    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64"):
        return "x64"
    if machine in ("arm64", "aarch64"):
        return "arm64"
    raise CliError("Для архитектуры {} нет проверенной сборки whisper.cpp".format(machine))


def install_archive(step: dict, arch: str | None = None) -> str:
    """Verify before extraction, reject unsafe paths, then replace only AIEditing's private copy."""
    arch = arch or _architecture()
    variant = step["archives"].get(arch)
    if variant is None:
        raise CliError("Для архитектуры {} нет проверенной сборки whisper.cpp".format(arch))
    dest = Path(os.path.expandvars(os.path.expanduser(step["save_to"])))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".whisper-install-", dir=str(dest.parent)) as raw:
        tmp = Path(raw)
        archive = tmp / "whisper.zip"
        digest = hashlib.sha256()
        try:
            with archive.open("wb") as out:
                for piece in fetch(variant["url"]):
                    digest.update(piece)
                    out.write(piece)
        except OSError as exc:
            raise CliError("Не получилось скачать whisper.cpp: {}".format(exc)) from exc
        if digest.hexdigest().lower() != variant["sha256"].lower():
            raise CliError("Сумма sha256 архива whisper.cpp не совпала; ничего не установлено")
        stage = tmp / "new"
        stage.mkdir()
        try:
            with zipfile.ZipFile(archive) as source:
                for member in source.infolist():
                    path = PurePosixPath(member.filename)
                    mode = member.external_attr >> 16
                    if path.is_absolute() or ".." in path.parts or "\\" in member.filename or stat.S_ISLNK(mode):
                        raise CliError("В архиве whisper.cpp небезопасный путь; ничего не установлено")
                    if member.is_dir():
                        continue
                    if len(path.parts) == 2 and path.parts[0] == "Release" and (
                            path.name == "whisper-cli.exe" or path.suffix.lower() == ".dll"):
                        with source.open(member) as src, (stage / path.name).open("wb") as dst:
                            shutil.copyfileobj(src, dst)
        except zipfile.BadZipFile as exc:
            raise CliError("Архив whisper.cpp повреждён; ничего не установлено") from exc
        if not (stage / "whisper-cli.exe").is_file() or not any(stage.glob("*.dll")):
            raise CliError("В архиве whisper.cpp нет CLI или DLL; ничего не установлено")
        previous = tmp / "previous"
        if dest.exists():
            os.replace(dest, previous)
        try:
            os.replace(stage, dest)
        except OSError:
            if previous.exists():
                os.replace(previous, dest)
            raise
    return "поставлено: {}".format(dest / "whisper-cli.exe")
