"""Shared bits: the one error type, running programs, paths and small output helpers."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence

FPS = 30
FRAME_W, FRAME_H = 1920, 1080
TAIL = 12  # lines of a failed program's output shown to the person

KIT = Path(__file__).resolve().parent.parent.parent  # overlay-kit/
TEMPLATE = KIT / "template"


class ToolError(Exception):
    """A reason the person can act on. The command line prints it and exits with code 2."""


def say(text: str = "") -> None:
    print(text, flush=True)


def warn(text: str) -> None:
    print("Внимание: " + text, flush=True)


def need(*programs: str) -> None:
    missing = [p for p in programs if not shutil.which(p)]
    if missing:
        raise ToolError("Нет программы: {}. Поставьте её и повторите.".format(", ".join(missing)))


def run(cmd: Sequence, what: str, cwd: Optional[Path] = None, capture: bool = True,
        ok_codes: Sequence[int] = (0,)) -> subprocess.CompletedProcess:
    """Run a program; a failure becomes a ToolError with the tail of its output."""
    args = [str(c) for c in cmd]
    try:
        done = subprocess.run(
            args, cwd=str(cwd) if cwd else None, check=False,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.STDOUT if capture else None,
            stdin=subprocess.DEVNULL, universal_newlines=True, encoding="utf-8", errors="replace",
        )
    except OSError as exc:
        raise ToolError("{}: не запускается {} ({})".format(what, args[0], exc))
    if done.returncode not in ok_codes:
        tail = "\n".join((done.stdout or "").strip().splitlines()[-TAIL:])
        raise ToolError("{} не удалось (код {}).{}".format(what, done.returncode, ("\n" + tail) if tail else ""))
    return done


def ffmpeg(*args, what: str = "ffmpeg") -> subprocess.CompletedProcess:
    return run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", *args], what)


def ffmpeg_text(*args) -> str:
    """stderr of ffmpeg, for filters that print their result there (silencedetect, loudnorm, ebur128)."""
    done = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-nostats", *map(str, args)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                          universal_newlines=True, encoding="utf-8", errors="replace")
    return done.stderr or ""


def work_dir(arg: str) -> Path:
    """The working folder as an absolute path that exists and looks like a prepared one."""
    path = Path(arg).expanduser()
    if not path.is_absolute():
        raise ToolError("Рабочая папка должна быть абсолютным путём: {}".format(arg))
    if not (path / "src" / "Root.tsx").is_file():
        raise ToolError("В {} нет шаблона. Сначала: overlay.py prepare <видео> <папка> ...".format(path))
    return path


def write_atomic(path: Path, text: str) -> None:
    """A unique temporary name: scene executors running at the same time rewrite the same lists."""
    handle, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".part", dir=str(path.parent))
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(text)
    os.replace(tmp, str(path))


def fmt_secs(value: float) -> str:
    return "{:.2f} с".format(value)


def parse_secs(values: List[str], limit: Optional[float] = None) -> List[str]:
    out = []
    for raw in values:
        try:
            sec = float(raw)
        except ValueError:
            raise ToolError("Секунда должна быть числом: «{}»".format(raw))
        if sec < 0 or (limit is not None and sec > limit):
            raise ToolError("Секунда {} вне видео (длительность {:.2f} с)".format(raw, limit or 0))
        out.append(raw)
    return out


def stdout_utf8() -> None:
    """Russian output must not fail on a Windows console code page."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
