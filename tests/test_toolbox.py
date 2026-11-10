"""The optional toolkit stays finite, pinned and explicit about its model."""
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from _support import SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))


class ToolboxManifest(unittest.TestCase):
    def test_rows_are_unique_and_never_install_bria(self):
        from aelib.toolbox import rows

        listed = rows()
        ids = [r["id"] for r in listed]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 6)
        for row in listed:
            self.assertEqual(set(row["install"]), {"mac", "win"})
            self.assertTrue(row["license"])
            for step in row["install"].values():
                self.assertNotIn("bria", step.get("url", "").lower())
        self.assertEqual(next(r for r in listed if r["id"] == "rembg")["min_python"], "3.11")

    def test_older_python_chooses_compatible_pins(self):
        from aelib.installers import pip_package
        from aelib.toolbox import catalog

        rows = catalog()
        self.assertEqual(pip_package(rows["librosa"]["install"]["mac"], (3, 9)), "librosa==0.11.0")
        self.assertEqual(pip_package(rows["pysubs2"]["install"]["mac"], (3, 11)), "pysubs2==1.8.0")
        self.assertEqual(pip_package(rows["scenedetect"]["install"]["win"], (3, 9)), "scenedetect==0.6.7.1")
        self.assertEqual(pip_package(rows["soundfile"]["install"]["win"], (3, 9)), "soundfile==0.13.1")

    def test_cli_lists_json_without_installing(self):
        env = dict(os.environ, PYTHONPATH=str(SKILL / "tools"))
        out = subprocess.check_output([sys.executable, "-m", "aelib.toolbox", "list", "--json"], env=env)
        self.assertEqual(len(json.loads(out)), 6)


class ImageCutoutPreflight(TempDirCase):
    def test_requires_local_checked_model_before_processing(self):
        from aelib.toolbox import ToolboxError, image_cutout

        src = self.tmp / "source.png"
        src.write_bytes(b"not an image")
        out = self.tmp / "cutout.png"
        with patch("aelib.toolbox.status", return_value={"ok": False}), \
             patch("aelib.toolbox.subprocess.run") as run, self.assertRaises(ToolboxError):
            image_cutout(src, out)
        run.assert_not_called()
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
