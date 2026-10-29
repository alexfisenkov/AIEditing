"""`ae.py init` raises the dashboard on 127.0.0.1: the page and state.js answer over http."""
import os
import re
import subprocess
import sys
import unittest
import urllib.request

from _support import SKILL, TempDirCase

AE = SKILL / "tools" / "ae.py"


class Dashboard(TempDirCase):
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


if __name__ == "__main__":
    unittest.main()
