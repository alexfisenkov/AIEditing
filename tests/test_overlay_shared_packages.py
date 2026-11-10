"""Overlay working folders reuse only a verified matching shared Remotion install."""
import json
import os
import sys
from unittest import mock

from _support import SKILL, TempDirCase

KIT = SKILL / "overlay-kit"
sys.path.insert(0, str(KIT / "tools"))
from overlaylib import prepare  # noqa: E402


class SharedRemotion(TempDirCase):
    def setUp(self):
        super().setUp()
        self.work = self.tmp / "work"
        self.work.mkdir()
        self.shared = self.tmp / "shared"
        self.shared.mkdir()
        self.browser = self.tmp / "browser"
        self.browser.write_text("")
        lock = KIT / "template" / "package-lock.json"
        (self.work / "package-lock.json").write_bytes(lock.read_bytes())
        (self.shared / "package-lock.json").write_bytes(lock.read_bytes())
        packages = self.shared / "node_modules"
        remotion = packages / "remotion"
        remotion.mkdir(parents=True)
        (remotion / "package.json").write_text(json.dumps({"version": "4.0.542"}))
        cli = packages / "@remotion" / "cli"
        cli.mkdir(parents=True)
        (cli / "remotion-cli.js").write_text("")
        (cli / "package.json").write_text(json.dumps({"version": "4.0.542"}))

    def test_matching_lock_reuses_shared_node_modules(self):
        with mock.patch.object(prepare, "shared_prefix", return_value=self.shared), \
                mock.patch.dict(os.environ, {"OVERLAY_BROWSER": str(self.browser)}), \
                mock.patch.object(prepare, "run") as run:
            prepare.install_packages(self.work)
        self.assertTrue((self.work / "node_modules").is_symlink())
        run.assert_not_called()

    def test_changed_lock_unlinks_alias_before_local_npm_ci(self):
        (self.work / "node_modules").symlink_to(self.shared / "node_modules", target_is_directory=True)
        (self.work / "package-lock.json").write_text("{}")
        with mock.patch.object(prepare, "shared_prefix", return_value=self.shared), \
                mock.patch.dict(os.environ, {"OVERLAY_BROWSER": str(self.browser)}), \
                mock.patch.object(prepare, "run") as run:
            prepare.install_packages(self.work)
        self.assertFalse((self.work / "node_modules").is_symlink())
        self.assertTrue((self.shared / "node_modules" / "remotion" / "package.json").is_file())
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0][1], "ci")
        self.assertEqual(run.call_args_list[1].args[0][-2:], ["browser", "ensure"])

    def test_symlink_refusal_falls_back_to_local_npm_ci(self):
        with mock.patch.object(prepare, "shared_prefix", return_value=self.shared), \
                mock.patch.dict(os.environ, {"OVERLAY_BROWSER": str(self.browser)}), \
                mock.patch.object(prepare.Path, "symlink_to", side_effect=OSError("no symlink")), \
                mock.patch.object(prepare, "run") as run:
            prepare.install_packages(self.work)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0][1], "ci")
        self.assertEqual(run.call_args_list[1].args[0][-2:], ["browser", "ensure"])
