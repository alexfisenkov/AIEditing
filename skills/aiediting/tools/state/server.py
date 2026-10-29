"""A static server for the workshop folder on 127.0.0.1, kept alive by every call.

Adapted from AISpa's ap.py (MIT, see NOTICE.md): the previous port first (an open tab revives by
itself), a detached `python -m http.server`, no server over SSH or in CI.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from .procs import WIN, cmdline, is_ours, kill, kill_orphans

PID, LOG = "serve.pid", "serve.log"


def recorded(work: Path):
    try:
        port, pid = (Path(work) / PID).read_text(encoding="utf-8").split()
        return int(port), int(pid)
    except (OSError, ValueError):
        return None, None


def http_ok(port: int) -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/dashboard.html" % port, timeout=2) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def free_port(prefer):
    for p in ([prefer] if prefer else []) + [0]:
        s = socket.socket()
        if not WIN:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", p))
            return s.getsockname()[1]
        except OSError:
            continue
        finally:
            s.close()
    return None


def _detached() -> dict:
    if WIN:
        return {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                | getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {"start_new_session": True}


def serve(work: Path) -> str:
    work = Path(work).resolve()
    page = work / "dashboard.html"
    if os.environ.get("SSH_CONNECTION") or os.environ.get("CI"):
        return "удалённая сессия — без сервера, дашборд: {}".format(page)
    port, pid = recorded(work)
    if port and pid and http_ok(port) and is_ours(cmdline(pid), work):
        return "http://localhost:%d/dashboard.html" % port
    kill_orphans(work)
    port = free_port(port)
    if not port:
        return "порт не нашёлся — дашборд открывается файлом: {}".format(page)
    with open(str(work / LOG), "a", encoding="utf-8") as log:
        srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1",
                                "--directory", str(work)], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=log, **_detached())
    for _ in range(20):
        if http_ok(port):
            (work / PID).write_text("%d %d\n" % (port, srv.pid), encoding="utf-8")
            return "сервер поднят: http://localhost:%d/dashboard.html" % port
        try:
            srv.wait(timeout=0.5)
            break
        except subprocess.TimeoutExpired:
            continue
    srv.terminate()
    return "сервер не ответил — дашборд открывается файлом: {}".format(page)


def stop(work: Path) -> str:
    work = Path(work).resolve()
    port, pid = recorded(work)
    if pid and is_ours(cmdline(pid), work):
        kill(pid)
    n = kill_orphans(work)
    for name in (PID, LOG):
        try:
            (work / name).unlink()
        except OSError:
            pass
    return "сервер остановлен" if pid or n else "сервера не было"
