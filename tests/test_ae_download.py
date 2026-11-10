"""`ae.py doctor --install yunet-model --yes` fetches the model itself and checks its sum; no network here."""
import contextlib
import hashlib
import io
import json
import os
import sys
import unittest
from argparse import Namespace
from unittest import mock

from _support import SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))

CATALOG = json.loads((SKILL / "catalog" / "tools.json").read_text(encoding="utf-8"))
ROW = next(r for r in CATALOG["tools"] if r["id"] == "yunet-model")
URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SUM = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
BODY = b"not the real model, only bytes"


class CatalogRow(unittest.TestCase):
    def test_both_systems_download_from_the_pinned_url_with_the_sum(self):
        for os_key, step in ROW["install"].items():
            self.assertEqual(step["kind"], "download", os_key)
            self.assertEqual((step["url"], step["sha256"]), (URL, SUM), os_key)
        self.assertIn("~/.aiediting/models/", ROW["install"]["mac"]["save_to"])
        self.assertIn("AIEditing", ROW["install"]["win"]["save_to"])
        self.assertIn("models", ROW["install"]["win"]["save_to"])


class Download(TempDirCase):
    def setUp(self):
        super().setUp()
        from aelib.checks import current_os

        self.dest = self.tmp / "models" / "face_detection_yunet_2023mar.onnx"
        step = {"kind": "download", "url": URL, "sha256": hashlib.sha256(BODY).hexdigest(),
                "save_to": str(self.dest)}
        self.row = dict(ROW, install={current_os(): step}, check={"file": str(self.dest)})
        self.calls = []

    def install(self, body):
        from aelib import doctor
        from aelib.session import CliError

        def loader(url):
            self.calls.append(url)
            return [body[:3], body[3:]]

        opt = Namespace(catalog=None, steps=None, asr=None, install="yunet-model", yes=True, requirements=False)
        with mock.patch("aelib.downloads.fetch", loader), \
                mock.patch("aelib.catalog.tools", lambda base=None: {"yunet-model": self.row}):
            try:
                return doctor.cmd_doctor(opt), None
            except CliError as e:
                return None, str(e)

    def test_good_download_lands_through_part_file(self):
        out, err = self.install(BODY)
        self.assertIsNone(err)
        self.assertEqual(self.calls, [URL])
        self.assertEqual(self.dest.read_bytes(), BODY)
        self.assertFalse(self.dest.with_name(self.dest.name + ".part").exists())
        self.assertIn("поставлено", out)

    def test_wrong_sum_leaves_no_file_and_fails_with_a_clear_message(self):
        out, err = self.install(b"something else")
        self.assertIsNone(out)
        self.assertIn("!!", err)
        self.assertIn("sha256", err)
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.dest.with_name(self.dest.name + ".part").exists())

    def test_the_command_exits_with_a_nonzero_code_on_a_wrong_sum(self):
        from aelib import cli

        with mock.patch("aelib.downloads.fetch", lambda url: [b"something else"]), \
                mock.patch("aelib.catalog.tools", lambda base=None: {"yunet-model": self.row}):
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["doctor", "--install", "yunet-model", "--yes"])
        self.assertNotEqual(code, 0)
        self.assertFalse(self.dest.exists())

    def test_a_file_already_there_is_not_fetched_again(self):
        self.install(BODY)
        self.calls.clear()
        out, err = self.install(BODY)
        self.assertIsNone(err)
        self.assertEqual(self.calls, [])
        self.assertIn("уже на месте", out)

    def test_a_download_cut_off_midway_is_one_clear_line_and_no_file(self):
        import http.client

        from aelib import downloads
        from aelib.checks import current_os
        from aelib.session import CliError

        def cut(url):
            yield b"abc"
            raise http.client.IncompleteRead(b"abc")

        step = self.row["install"][current_os()]
        with mock.patch("aelib.downloads.fetch", cut), self.assertRaises(CliError):
            downloads.download(step)
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.dest.with_name(self.dest.name + ".part").exists())

    def test_network_failure_is_one_clear_line_and_no_file(self):
        from aelib import doctor
        from aelib.session import CliError

        opt = Namespace(catalog=None, steps=None, asr=None, install="yunet-model", yes=True, requirements=False)

        def broken(url):
            raise OSError("нет сети")

        with mock.patch("aelib.downloads.fetch", broken), \
                mock.patch("aelib.catalog.tools", lambda base=None: {"yunet-model": self.row}):
            with self.assertRaises(CliError) as caught:
                doctor.cmd_doctor(opt)
        self.assertIn("!!", str(caught.exception))
        self.assertFalse(self.dest.exists())

    def test_plan_without_yes_downloads_nothing(self):
        from aelib import doctor

        opt = Namespace(catalog=None, steps=None, asr=None, install="yunet-model", yes=False, requirements=False)
        with mock.patch("aelib.downloads.fetch", lambda url: self.fail("network")), \
                mock.patch("aelib.catalog.tools", lambda base=None: {"yunet-model": self.row}):
            out = doctor.cmd_doctor(opt)
        self.assertIn(URL, out)
        self.assertFalse(self.dest.exists())


if __name__ == "__main__":
    unittest.main()
