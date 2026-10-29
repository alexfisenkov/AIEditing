"""Running ffmpeg/ffprobe without a shell, on macOS and Windows alike."""
from __future__ import annotations

import functools
import os
import shutil
import subprocess
from pathlib import Path


class MediaError(RuntimeError):
    """ffmpeg/ffprobe failed or is missing; the message is meant for a human."""


def tool(name: str) -> str:
    """Path to ffmpeg/ffprobe; AIEDITING_FFMPEG / AIEDITING_FFPROBE override PATH."""
    found = os.environ.get("AIEDITING_" + name.upper()) or shutil.which(name)
    if not found:
        raise MediaError(
            "Не найден {0}. Установите ffmpeg (macOS: brew install ffmpeg; "
            "Windows: winget install Gyan.FFmpeg) и откройте терминал заново.".format(name)
        )
    return found


def run(args, what: str = "ffmpeg", check: bool = True) -> subprocess.CompletedProcess:
    """Runs ffmpeg (or ffprobe) with a list of arguments and returns the finished process."""
    base = [tool(what), "-hide_banner"]
    if what == "ffmpeg":
        base += ["-nostdin", "-y"]
    proc = subprocess.run(
        base + [str(a) for a in args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        encoding="utf-8", errors="replace",
    )
    if check and proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-6:])
        raise MediaError("{} завершился с ошибкой {}:\n{}".format(what, proc.returncode, tail))
    return proc


@functools.lru_cache(maxsize=1)
def encoders() -> frozenset:
    """Names of the video/audio encoders this ffmpeg build has."""
    out = run(["-encoders"]).stdout
    names = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and len(parts[0]) == 6 and parts[0][0] in "VAS":
            names.add(parts[1])
    return frozenset(names)


def ensure_file(path) -> Path:
    path = Path(path)
    if not path.is_file():
        raise MediaError("Файл не найден: {}".format(path))
    return path
