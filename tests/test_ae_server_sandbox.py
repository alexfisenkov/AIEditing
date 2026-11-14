"""The dashboard server inside an agent's sandbox: a closed network and no `ps`."""
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from unittest import mock

from _support import SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))

import state as st  # noqa: E402
from state import procs, server  # noqa: E402


def port_of(line):
    return int(line.split("http://127.0.0.1:", 1)[1].split("/", 1)[0])


class Sandbox(TempDirCase):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        for name in ("CI", "SSH_CONNECTION", "AIEDITING_NO_SERVE"):
            os.environ.pop(name, None)
        self.work = (self.tmp / "мастерская с пробелом").resolve()
        st.install_page(self.work)
        self.addCleanup(server.stop, self.work)          # with ps: whatever a test left running


class ClosedNetwork(Sandbox):
    """Codex `workspace-write` without network: binding even 127.0.0.1 is refused."""

    def check(self, line):
        self.assertIn("сеть закрыта песочницей агента", line)
        self.assertIn(str(self.work / "dashboard.html"), line)
        self.assertIn("sandbox_workspace_write.network_access=true", line)
        self.assertFalse((self.work / "serve.pid").exists())

    def test_a_refused_bind_says_why_and_gives_the_file(self):
        class Refused(socket.socket):
            def bind(self, address):
                raise PermissionError(1, "Operation not permitted")

        with mock.patch.object(server.socket, "socket", Refused):
            self.check(server.serve(self.work))

    def test_a_refused_socket_is_the_same_answer_not_a_crash(self):
        with mock.patch.object(server.socket, "socket", side_effect=PermissionError(1, "Operation not permitted")):
            self.check(server.serve(self.work))


class NoPs(Sandbox):
    """`ps` prints nothing in the sandbox: the server is known by what it serves on the recorded port."""

    def test_the_same_server_is_kept_and_can_be_stopped(self):
        with mock.patch("state.procs._run", return_value=""):
            first = server.serve(self.work)
            self.assertIn("сервер поднят", first)
            port = port_of(first)
            again = server.serve(self.work)
            self.assertEqual(port_of(again), port, again)
            self.assertNotIn("сервер поднят", again)
            self.assertEqual(server.stop(self.work), "сервер остановлен")
        for _ in range(40):
            if not server.http_ok(port):
                break
            time.sleep(0.05)
        self.assertFalse(server.http_ok(port), "the server outlived stop-server")

    def test_a_recorded_pid_ps_cannot_see_is_dead_not_ours_when_ps_works(self):
        """Our folder on the recorded port, but the pid in serve.pid is somebody else's now: it is left alone."""
        line = server.serve(self.work)
        port = port_of(line)
        stranger = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(stranger.wait)
        self.addCleanup(stranger.kill)
        (self.work / "serve.pid").write_text("{} {}\n".format(port, stranger.pid), encoding="utf-8")
        real = procs._run

        def ps(args):          # ps works, only that one process is not seen (gone, as far as ps tells)
            return "" if str(stranger.pid) in args else real(args)

        with mock.patch("state.procs._run", side_effect=ps):
            server.stop(self.work)
        time.sleep(0.2)
        self.assertIsNone(stranger.poll(), "stop-server sent SIGTERM to a process that is not ours")

    def test_a_stranger_on_the_recorded_port_is_neither_kept_nor_stopped(self):
        other = self.tmp / "чужая"
        st.install_page(other)
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        stranger = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1",
                                     "--directory", str(other)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(stranger.wait)
        self.addCleanup(stranger.terminate)
        for _ in range(40):
            if server.http_ok(port):
                break
            time.sleep(0.1)
        (self.work / "serve.pid").write_text("{} {}\n".format(port, stranger.pid), encoding="utf-8")
        with mock.patch("state.procs._run", return_value=""):
            server.stop(self.work)
            self.assertIsNone(stranger.poll(), "somebody else's server was stopped")
            (self.work / "serve.pid").write_text("{} {}\n".format(port, stranger.pid), encoding="utf-8")
            line = server.serve(self.work)
            self.assertNotEqual(port_of(line), port, line)
            with urllib.request.urlopen(line.split(": ", 1)[1], timeout=5) as r:
                self.assertEqual(r.status, 200)
            server.stop(self.work)


if __name__ == "__main__":
    unittest.main()
