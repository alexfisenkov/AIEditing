"""`ae.py init` raises the dashboard on 127.0.0.1: the page and state.js answer over http, video by ranges."""
import os
import re
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from email.utils import formatdate

from _support import SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))

AE = SKILL / "tools" / "ae.py"
CLIP = bytes(range(256)) * 4      # 1024 bytes where every slice is recognisable


class Workshop(TempDirCase):
    def setUp(self):
        super().setUp()
        self.env = {k: v for k, v in os.environ.items() if k not in ("CI", "SSH_CONNECTION", "AIEDITING_NO_SERVE")}
        self.env["AIEDITING_WORK"] = str(self.tmp / "мастерская")

    def tearDown(self):
        self.ae("stop-server")
        super().tearDown()

    def ae(self, *args):
        return subprocess.run([sys.executable, str(AE), *args], capture_output=True, text=True,
                              encoding="utf-8", env=self.env, cwd=str(self.tmp), timeout=60)


class Dashboard(Workshop):
    def get(self, url):
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.read().decode("utf-8")

    def test_init_serves_page_and_state_on_localhost(self):
        proc = self.ae("init", "--title", "Проба сервера")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        port = re.search(r"http://localhost:(\d+)/dashboard\.html", proc.stdout)
        self.assertIsNotNone(port, proc.stdout)
        base = "http://127.0.0.1:{}/".format(port.group(1))
        status, page = self.get(base + "dashboard.html")
        self.assertEqual(status, 200)
        self.assertIn("Проба сервера", page)          # the snapshot inside the page
        self.assertIn("NOTICE.md", page)              # the MIT notice of the borrowed parts
        status, state = self.get(base + "state.js")
        self.assertTrue(state.startswith("window.STATE ="))
        again = self.ae("stage", "formats")            # the next call finds the same server
        self.assertIn(base.replace("127.0.0.1", "localhost"), again.stdout)


class Seeking(Workshop):
    """A <video> can seek only if the server answers byte ranges with 206."""

    def setUp(self):
        super().setUp()
        proc = self.ae("init", "--title", "Перемотка")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.base = "http://127.0.0.1:{}/".format(re.search(r"localhost:(\d+)/", proc.stdout).group(1))
        self.work = self.tmp / "мастерская"
        folder = self.work / "монтаж урок" / "out"
        folder.mkdir(parents=True)
        self.clip = folder / "ролик.mp4"
        self.clip.write_bytes(CLIP)
        self.url = self.base + urllib.request.quote("монтаж урок/out/ролик.mp4")

    def request(self, url=None, method="GET", **headers):
        req = urllib.request.Request(url or self.url, method=method,
                                     headers={k.replace("_", "-"): v for k, v in headers.items()})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.headers, e.read()

    def test_a_middle_range_answers_206_with_exactly_those_bytes(self):
        status, head, body = self.request(Range="bytes=100-199")
        self.assertEqual(status, 206)
        self.assertEqual(head["Content-Range"], "bytes 100-199/1024")
        self.assertEqual(head["Content-Length"], "100")
        self.assertEqual(head["Content-Type"], "video/mp4")
        self.assertEqual(head["Accept-Ranges"], "bytes")
        self.assertEqual(body, CLIP[100:200])

    def test_open_ended_suffix_and_overlong_ranges(self):
        cases = {"bytes=1000-": (1000, 1023), "bytes=-24": (1000, 1023), "bytes=1000-99999": (1000, 1023),
                 "bytes=0-": (0, 1023), "bytes=-99999": (0, 1023), "bytes=0-0": (0, 0)}
        for wanted, (a, b) in cases.items():
            with self.subTest(wanted):
                status, head, body = self.request(Range=wanted)
                self.assertEqual(status, 206)
                self.assertEqual(head["Content-Range"], "bytes {}-{}/1024".format(a, b))
                self.assertEqual(body, CLIP[a:b + 1])

    def test_a_range_past_the_end_answers_416_with_the_size(self):
        for wanted in ("bytes=1024-", "bytes=5000-6000", "bytes=-0"):
            with self.subTest(wanted):
                status, head, _ = self.request(Range=wanted)
                self.assertEqual(status, 416)
                self.assertEqual(head["Content-Range"], "bytes */1024")

    def test_without_a_range_the_whole_file_says_it_can_do_ranges(self):
        status, head, body = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(head["Accept-Ranges"], "bytes")
        self.assertEqual(body, CLIP)

    def test_what_is_not_one_plain_range_gets_the_whole_file(self):
        for wanted in ("bytes=0-1,5-6", "bytes=9-3", "bytes=a-b", "items=0-1", "bytes=-", "bytes=²-³",
                       "bytes=" + "9" * 5000 + "-"):
            with self.subTest(wanted[:20]):
                status, _, body = self.request(Range=wanted)
                self.assertEqual(status, 200)
                self.assertEqual(body, CLIP)

    def test_if_range_gives_the_part_only_for_the_same_version(self):
        stamp = formatdate(self.clip.stat().st_mtime, usegmt=True)
        status, _, body = self.request(Range="bytes=0-9", If_Range=stamp)
        self.assertEqual((status, body), (206, CLIP[:10]))
        status, _, body = self.request(Range="bytes=0-9", If_Range="Thu, 01 Jan 1970 00:00:00 GMT")
        self.assertEqual((status, body), (200, CLIP))

    def test_not_modified_wins_over_a_range(self):
        stamp = formatdate(self.clip.stat().st_mtime + 60, usegmt=True)
        status, _, body = self.request(Range="bytes=0-9", If_Modified_Since=stamp)
        self.assertEqual((status, body), (304, b""))

    def test_head_ignores_the_range(self):
        status, head, body = self.request(method="HEAD", Range="bytes=0-9")
        self.assertEqual((status, head["Content-Length"], body), (200, "1024", b""))

    def test_a_folder_and_a_missing_file_behave_as_before(self):
        status, _, _ = self.request(self.base + urllib.request.quote("нет-такого.mp4"), Range="bytes=0-9")
        self.assertEqual(status, 404)
        status, _, body = self.request(self.base + urllib.request.quote("монтаж урок/out/"), Range="bytes=0-9")
        self.assertEqual(status, 200)
        self.assertIn("ролик.mp4".encode("utf-8"), body)

    def test_an_abandoned_range_leaves_no_traceback_in_the_log(self):
        big = self.work / "большой.mp4"
        with open(str(big), "wb") as f:
            f.truncate(64 * 1024 * 1024)
        port = int(self.base.rsplit(":", 1)[1].strip("/"))
        path = urllib.request.quote(big.name)
        with socket.create_connection(("127.0.0.1", port), timeout=5) as s:
            s.sendall("GET /{} HTTP/1.1\r\nHost: x\r\nRange: bytes=0-\r\n\r\n".format(path).encode("ascii"))
            self.assertIn(b"206", s.recv(64))
        time.sleep(0.5)                                                # the server notices the dropped socket
        self.assertEqual(self.request(Range="bytes=0-0")[0], 206)      # and outlives the seek
        self.assertNotIn("Traceback", (self.work / "serve.log").read_text(encoding="utf-8"))


class OldServer(Workshop):
    def test_a_running_server_without_ranges_is_replaced_by_the_next_call(self):
        self.assertEqual(self.ae("init", "--title", "Смена сервера").returncode, 0)
        self.assertEqual(self.ae("stop-server").returncode, 0)
        work = (self.tmp / "мастерская").resolve()
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        old = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1",
                                "--directory", str(work)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(old.wait)
        self.addCleanup(old.terminate)
        for _ in range(40):
            try:
                urllib.request.urlopen("http://127.0.0.1:{}/dashboard.html".format(port), timeout=1).close()
                break
            except OSError:
                self.assertIsNone(old.poll(), "the old server did not start")
                time.sleep(0.1)
        (work / "serve.pid").write_text("{} {}\n".format(port, old.pid), encoding="utf-8")
        (work / "кусок.bin").write_bytes(CLIP)
        out = self.ae("stage", "formats").stdout
        old.wait(timeout=5)                                            # stopped, not reused
        new = re.search(r"localhost:(\d+)/", out).group(1)
        self.assertEqual(int(new), port, "the previous port first: an open tab revives by itself")
        req = urllib.request.Request("http://127.0.0.1:{}/{}".format(new, urllib.request.quote("кусок.bin")),
                                     headers={"Range": "bytes=10-19"})
        with urllib.request.urlopen(req, timeout=5) as r:
            self.assertEqual((r.status, r.read()), (206, CLIP[10:20]))


class WhoseServer(unittest.TestCase):
    """The check stays narrow: only our script or the old stdlib server, and only in exactly our folder."""

    def test_ours_and_not_ours(self):
        from state.procs import is_current, is_ours
        work = "/tmp/мастерская"
        new = "python /kit/tools/state/rangeserver.py 8000 --bind 127.0.0.1 --directory " + work
        old = "python -m http.server 8000 --bind 127.0.0.1 --directory " + work
        self.assertTrue(is_ours(new, work))
        self.assertTrue(is_current(new, work))
        self.assertTrue(is_ours(old, work))
        self.assertFalse(is_current(old, work))
        for stranger in (new + "-2", old + "-2", "python -m http.server 8000", "python app.py --directory " + work,
                         "vim rangeserver.py"):
            self.assertFalse(is_ours(stranger, work), stranger)
            self.assertFalse(is_current(stranger, work), stranger)


if __name__ == "__main__":
    unittest.main()
