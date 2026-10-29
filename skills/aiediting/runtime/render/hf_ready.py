"""Before a run asks about animations: is Node new enough and is the render browser already on disk?

Nothing is downloaded here (`hyperframes browser path` would fetch Chrome when it is missing): the
browser is looked for where HyperFrames keeps it — HYPERFRAMES_BROWSER_PATH, else ~/.cache/hyperframes/chrome.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from . import hyperframes
from .hyperframes import HINT, NODE_MAJOR

SHELL = ("chrome-headless-shell", "chrome-headless-shell.exe")


def node_major() -> Optional[int]:
    node = shutil.which("node")
    if not node:
        return None
    try:
        out = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    found = re.findall(r"\d+", out or "")
    return int(found[0]) if found else None


def browser() -> Optional[Path]:
    own = os.environ.get("HYPERFRAMES_BROWSER_PATH")
    if own and Path(own).is_file():
        return Path(own)
    cache = Path.home() / ".cache" / "hyperframes" / "chrome" / "chrome-headless-shell"
    found = [p for name in SHELL for p in cache.glob("*/*/" + name) if p.is_file()] if cache.is_dir() else []
    return sorted(found)[-1] if found else None


def problem() -> Optional[str]:
    """Why animations cannot be made on this computer now, in Russian; None when they can."""
    why = hyperframes.missing()
    if why:
        return why
    major = node_major()
    if major is None or major < NODE_MAJOR:
        return "Node.js {} старше нужного {} ({})".format(major, NODE_MAJOR, HINT.format("node"))
    if browser() is None:
        return "нет браузера рендера HyperFrames ({})".format(HINT.format("hyperframes"))
    return None
