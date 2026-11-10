"""A built format carries its own selected toolkit repair, independent of the workshop."""
import json
import os
import subprocess
import sys

from _support import SKILL, TempDirCase


AE = SKILL / "tools" / "ae.py"


class BuiltToolkit(TempDirCase):
    def setUp(self):
        super().setUp()
        draft = self.tmp / "draft"
        draft.mkdir()
        profile = {
            "format": "проверка", "skill_name": "монтаж-проверка", "language": "ru",
            "asr": {"provider": "scribe", "language": "ru", "model": "scribe_v2"},
            "steps": ["loudnorm"], "params": {}, "approval": "plan",
            "design": "design/", "taste": [], "output_dir": str(self.tmp / "out-media"),
        }
        (draft / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        built = subprocess.run([sys.executable, str(AE), "build-skill", str(draft / "profile.json"),
                                str(self.tmp / "built")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        self.skill = self.tmp / "built" / "монтаж-проверка"
        self.run = self.skill / "tools" / "run.py"
        self.env = dict(os.environ, HOME=str(self.tmp / "home"), LOCALAPPDATA=str(self.tmp / "home" / "AppData"))
        (self.tmp / "home").mkdir()

    def child(self, *args):
        return subprocess.run([sys.executable, "-I", "-B", str(self.run), *args], cwd=self.tmp,
                              env=self.env, capture_output=True, text=True, encoding="utf-8")

    def _fake_tool(self, install_success=True):
        ready = self.tmp / "ready.txt"
        check = self.tmp / "check.py"
        check.write_text(
            "import pathlib,sys\n"
            "p=pathlib.Path(sys.argv[1])\n"
            "print('ffmpeg version 9.0.2') if p.is_file() else sys.exit(1)\n",
            encoding="utf-8",
        )
        install = self.tmp / "install.py"
        install.write_text(
            "import pathlib,sys\n"
            + ("pathlib.Path(sys.argv[1]).write_text('ready')\n" if install_success else "print('no tool')\n"),
            encoding="utf-8",
        )
        catalog = self.skill / "catalog" / "tools.json"
        data = json.loads(catalog.read_text(encoding="utf-8"))
        self.assertEqual([r["id"] for r in data["tools"]], ["ffmpeg"])
        row = data["tools"][0]
        row["check"] = {"command": [sys.executable, str(check), str(ready)],
                        "version": "ffmpeg version (\\d+(?:\\.\\d+)*)"}
        row["install"]["mac"] = {"kind": "command", "argv": [sys.executable, str(install), str(ready)]}
        catalog.write_text(json.dumps(data), encoding="utf-8")
        return ready

    def test_selected_toolkit_is_packaged_without_workshop(self):
        self.assertTrue((self.skill / "tools" / "aelib" / "setup.py").is_file())
        self.assertTrue((self.skill / "catalog" / "tools.json").is_file())
        self.assertFalse((self.skill / "tools" / "state.py").exists())
        self.assertFalse((self.skill / "catalog" / "steps.json").exists())
        self.assertFalse((self.skill / "overlay-kit").exists())

    def test_graphics_carries_its_own_remotion_lock(self):
        profile_path = self.tmp / "draft" / "profile.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["steps"] = ["write_srt", "graphics"]
        profile_path.write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        built = subprocess.run([sys.executable, str(AE), "build-skill", str(profile_path),
                                str(self.tmp / "graphics")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        skill = self.tmp / "graphics" / "монтаж-проверка"
        catalog = json.loads((skill / "catalog" / "tools.json").read_text(encoding="utf-8"))
        remotion = next(r for r in catalog["tools"] if r["id"] == "remotion")
        self.assertEqual(remotion["install"]["mac"]["lock"], "locks/remotion")
        self.assertTrue((skill / "catalog" / "locks" / "remotion" / "package-lock.json").is_file())
        self.assertTrue((skill / "design" / "overlay-kit" / "README.md").is_file())
        self.assertFalse((skill / "overlay-kit").exists())

    def test_private_python_prefers_only_a_ready_modern_environment(self):
        base = self.tmp / "home" / ".aiediting"
        legacy = base / "venv" / "bin" / "python"
        modern = base / "toolkit-venv" / "bin" / "python"
        legacy.parent.mkdir(parents=True)
        legacy.touch()
        modern.parent.mkdir(parents=True)
        modern.touch()
        script = "import runpy,sys; print(runpy.run_path(sys.argv[1], run_name='child_test')['_private_python']())"
        before = subprocess.run([sys.executable, "-I", "-B", "-c", script, str(self.run)], env=self.env,
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(before.returncode, 0, before.stderr)
        self.assertEqual(before.stdout.strip(), str(legacy))
        (base / "toolkit-venv" / "toolkit.ready").touch()
        after = subprocess.run([sys.executable, "-I", "-B", "-c", script, str(self.run)], env=self.env,
                               capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(after.returncode, 0, after.stderr)
        self.assertEqual(after.stdout.strip(), str(modern))

    def test_setup_repairs_selected_dependency_and_check_is_read_only(self):
        ready = self._fake_tool()
        plain = self.child("check")
        self.assertEqual(plain.returncode, 0, plain.stdout + plain.stderr)
        missing = self.child("check", "--tools")
        self.assertNotEqual(missing.returncode, 0)
        self.assertFalse(ready.exists())
        done = self.child("setup")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue(ready.is_file())
        checked = self.child("check", "--tools")
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_setup_does_not_claim_success_after_failed_postcheck(self):
        self._fake_tool(install_success=False)
        done = self.child("setup")
        self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("Не готово", done.stdout + done.stderr)


if __name__ == "__main__":
    import unittest
    unittest.main()
