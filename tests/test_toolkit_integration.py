"""A requested capability reaches a runnable format, not just a catalog label."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from _support import SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))


class ToolkitIntegration(TempDirCase):
    def test_extra_tool_catalog_is_loaded_and_duplicate_ids_are_rejected(self):
        from aelib import catalog

        (self.tmp / "tools.json").write_text(json.dumps({"tools": [{"id": "base"}]}))
        extra = self.tmp / "extra-tools.json"
        extra.write_text(json.dumps({"tools": [{"id": "extra"}]}))
        self.assertEqual(set(catalog.tools(self.tmp)), {"base", "extra"})
        extra.write_text(json.dumps({"tools": [{"id": "base"}]}))
        with self.assertRaises(ValueError):
            catalog.tools(self.tmp)

    def test_windows_whisper_uses_private_installed_binary_without_path_changes(self):
        from runtime.asr.whispercpp import _program

        exe = self.tmp / "AIEditing" / "bin" / "whisper-cpp" / "whisper-cli.exe"
        exe.parent.mkdir(parents=True)
        exe.write_bytes(b"test executable")
        with mock.patch("runtime.asr.whispercpp.sys.platform", "win32"), \
                mock.patch("runtime.asr.whispercpp.shutil.which", return_value=None), \
                mock.patch.dict(os.environ, {"LOCALAPPDATA": str(self.tmp)}):
            self.assertEqual(_program({}), [str(exe)])

    def test_default_whisper_model_resolves_to_the_installed_model(self):
        from runtime.asr.whispercpp import model_file

        with mock.patch.dict(os.environ, {"AIEDITING_WHISPER_MODEL": str(self.tmp / "model.bin")}):
            (self.tmp / "model.bin").write_bytes(b"model")
            self.assertEqual(model_file({}), self.tmp / "model.bin")

    def test_explicit_whisper_model_never_falls_back_silently(self):
        from runtime.asr.whispercpp import model_file
        from runtime.asr import AsrError

        with self.assertRaises(AsrError):
            model_file({"model": str(self.tmp / "missing.bin")})

    def test_background_modes_have_a_profile_contract(self):
        from runtime.profile import check_profile

        profile = {"format": "фон", "skill_name": "монтаж-фон", "language": "ru",
                   "asr": {"provider": "whispercpp"}, "steps": ["background"],
                   "params": {"background": {"mode": "not-a-mode"}}, "output_dir": "out"}
        self.assertTrue(check_profile(profile))
        profile["params"]["background"] = {"mode": "solid", "value": "#202020"}
        self.assertEqual(check_profile(profile), [])

    def test_both_subject_effects_declare_real_inference_dependencies(self):
        from aelib import catalog

        for step in ("background", "behind_head"):
            needed = catalog.needs([step], "command")["tools"]
            self.assertIn("onnxruntime", needed)
            self.assertIn("rvm-model", needed)
            self.assertFalse(catalog.steps()["steps"][step].get("not_built"))


if __name__ == "__main__":
    unittest.main()
