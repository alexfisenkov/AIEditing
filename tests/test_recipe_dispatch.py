"""Recipe discovery is available without running an edit."""
import subprocess
import sys
import os
import importlib.util
from unittest import mock

from _support import SKILL, TempDirCase


class RecipeDispatcher(TempDirCase):
    def test_broken_private_environment_cannot_reexec_forever(self):
        spec = importlib.util.spec_from_file_location("recipe_entry_test", SKILL / "tools" / "recipes.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        private = self.tmp / "broken-env" / "bin" / "python"
        private.parent.mkdir(parents=True)
        private.touch()
        with mock.patch("aelib.paths.venv_python", return_value=private), \
                mock.patch.dict(os.environ, {"AIEDITING_RECIPES_REEXEC": str(private.parent.parent.resolve())}), \
                mock.patch.object(module.subprocess, "call", return_value=0) as again:
            self.assertEqual(module.main(["audio-report", "unused.wav"]), 1)
        again.assert_not_called()

    def test_help_lists_available_methods(self):
        proc = subprocess.run([sys.executable, "-B", str(SKILL / "tools" / "recipes.py"), "--help"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for name in ("scenes", "audio-sync", "subtitle-convert", "stabilize", "quality"):
            self.assertIn(name, proc.stdout)

    def test_invalid_command_does_not_create_any_output(self):
        proc = subprocess.run([sys.executable, "-B", str(SKILL / "tools" / "recipes.py"), "not-a-recipe"],
                              cwd=self.tmp, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(list(self.tmp.iterdir()), [])
