"""Finding and stopping this workshop's own static server — and only it.

Adapted from AISpa's ap.py (MIT, see NOTICE.md): the check is deliberately narrow (`-m http.server`
and exactly our `--directory`), because a wide one once killed somebody else's server.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

WIN = os.name == "nt"


def _run(args) -> str:
    # ps prints non-ASCII paths as M-PM-… escapes under the C locale — and our folders are Cyrillic.
    env = dict(os.environ, LC_ALL="en_US.UTF-8" if sys.platform == "darwin" else "C.UTF-8")
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=10, env=env,
                              encoding="utf-8", errors="replace").stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _ps(script: str) -> str:
    return _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])


def cmdline(pid: int) -> str:
    if WIN:
        return _ps("(Get-CimInstance Win32_Process -Filter 'ProcessId=%d').CommandLine" % int(pid)).strip()
    return _run(["ps", "-p", str(int(pid)), "-o", "command="]).strip()


def processes():
    out = []
    if WIN:
        text = _ps("Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | "
                   "ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }")
        rows = (line.partition("\t") for line in text.splitlines())
    else:
        rows = (line.strip().partition(" ") for line in _run(["ps", "-Ao", "pid=,command="]).splitlines())
    for num, _, cmd in rows:
        if num.strip().isdigit():
            out.append((int(num), cmd))
    return out


def _norm(path) -> str:
    return os.path.normcase(os.path.normpath(str(path))).replace("\\", "/")


def is_ours(cmd: str, work) -> bool:
    c = cmd.replace("\\", "/")
    c = c.lower() if WIN else c
    ours = re.compile(r"--directory\s+\"?" + re.escape(_norm(work)) + r"\"?(?=\s|$)")
    return bool(re.search(r"-m\s+http\.server\b", c)) and bool(ours.search(c))


def kill(pid) -> None:
    try:
        os.kill(int(pid), 15)
    except (OSError, ValueError):
        pass


def kill_orphans(work, keep=None) -> int:
    n = 0
    for pid, cmd in processes():
        if pid not in (keep, os.getpid()) and is_ours(cmd, work):
            kill(pid)
            n += 1
    return n
