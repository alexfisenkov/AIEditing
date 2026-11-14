"""A static server for the workshop folder on 127.0.0.1, kept alive by every call.

Adapted from AISpa's ap.py (MIT, see NOTICE.md): the previous port first (an open tab revives by
itself), a detached `rangeserver.py`, no server over SSH or in CI.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from .procs import WIN, cmdline, is_current, is_ours, kill, kill_orphans

PID, LOG = "serve.pid", "serve.log"
# 127.0.0.1, not localhost: the port is checked there, and localhost may lead to somebody else's server on ::1.
URL = "http://127.0.0.1:%d/dashboard.html"
CLOSED = ("сеть закрыта песочницей агента: сервер не поднять. Чтобы дашборд жил по адресу, разрешите агенту локальную "
          "сеть (Codex: sandbox_workspace_write.network_access=true в ~/.codex/config.toml) и повторите вызов; "
          "пока он открывается файлом: {}")
SCRIPT = Path(__file__).resolve().with_name("rangeserver.py")


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
    """A port to bind on 127.0.0.1: the preferred one if free, else any. Raises PermissionError when the
    network itself is closed (an agent's sandbox refuses even a socket on 127.0.0.1)."""
    refused = None
    for p in ([prefer] if prefer else []) + [0]:
        s = socket.socket()          # PermissionError here (a seccomp sandbox) goes up as it is
        try:
            if not WIN:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", p))
            return s.getsockname()[1]
        except PermissionError as e:
            refused = e
        except OSError:
            continue
        finally:
            s.close()
    if refused is not None:
        raise refused
    return None


def serves_here(port: int, work: Path) -> bool:
    """The server on `port` serves this very folder: it answers with our own serve.pid, byte for byte."""
    try:
        mine = (Path(work) / PID).read_bytes()
        with urllib.request.urlopen("http://127.0.0.1:%d/%s" % (port, PID), timeout=2) as r:
            return r.status == 200 and r.read() == mine
    except urllib.error.HTTPError as e:
        e.close()
        return False
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _ours(work: Path, port, pid, check) -> bool:
    """Ours by the command line. An empty answer means a dead process while `ps` sees at least this very process;
    only where it sees nothing at all (an agent's sandbox) is the server known by what its port serves."""
    if not (port and pid):
        return False
    cmd = cmdline(pid)
    if cmd:
        return check(cmd, work)
    if cmdline(os.getpid()):
        return False
    return serves_here(port, work)


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
    if port and pid and http_ok(port) and _ours(work, port, pid, is_current):
        return URL % port
    try:
        if kill_orphans(work) and port:
            for _ in range(20):  # a stopped server lets go of its port in a moment; an open tab needs that port
                if free_port(port) == port:
                    break
                time.sleep(0.05)
        port = free_port(port)
    except PermissionError:
        return CLOSED.format(page)
    if not port:
        return "свободный порт на 127.0.0.1 не нашёлся — дашборд открывается файлом: {}".format(page)
    with open(str(work / LOG), "a", encoding="utf-8") as log:
        srv = subprocess.Popen([sys.executable, str(SCRIPT), str(port), "--bind", "127.0.0.1",
                                "--directory", str(work)], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=log, **_detached())
    for _ in range(20):
        if http_ok(port):
            (work / PID).write_text("%d %d\n" % (port, srv.pid), encoding="utf-8")
            return "сервер поднят: " + URL % port
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
    if _ours(work, port, pid, is_ours):
        kill(pid)
    n = kill_orphans(work)
    for name in (PID, LOG):
        try:
            (work / name).unlink()
        except OSError:
            pass
    return "сервер остановлен" if pid or n else "сервера не было"
