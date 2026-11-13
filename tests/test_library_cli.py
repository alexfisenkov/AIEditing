"""`ae.py library …` and the format skill's `run.py library|note|forbid` call the same library functions."""
import contextlib
import io
import json
import os
import subprocess
import sys
import unittest

from _support import SKILL, needs_ffmpeg
from test_library_paths import LibraryCase

sys.path.insert(0, str(SKILL / "tools"))

AE = SKILL / "tools" / "ae.py"
STEPS = ["speech_spans", "cut_spans", "loudnorm", "write_srt"]


def ae(*argv):
    from aelib.cli import main

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main([str(a) for a in argv])
    return code, out.getvalue()


class Workshop(LibraryCase):
    def test_set_where_status(self):
        code, said = ae("library", "set", self.tmp / "Моя библиотека")
        self.assertEqual(code, 0, said)
        lib = (self.tmp / "Моя библиотека").resolve()
        self.assertEqual(ae("library", "where"), (0, str(lib) + "\n"))
        code, said = ae("library", "status")
        self.assertEqual(code, 0)
        self.assertIn("галерея", said)

    def test_without_a_library_the_answer_says_how_to_choose_one(self):
        code, said = ae("library", "status")
        self.assertEqual(code, 1)
        self.assertIn("library set", said)

    def test_rule_forbid_and_find(self):
        ae("library", "set", self.tmp / "биб")
        lib = (self.tmp / "биб").resolve()
        rows = [{"f": "фото/а.jpg", "what": "Петя на рыбалке", "who": ["Петя"], "phrases": ["рыбалка"]},
                {"f": "фото/б.jpg", "what": "озеро на рыбалке", "phrases": ["рыбалка"]}]
        batch = self.tmp / "пачка.json"
        batch.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(ae("library", "describe", "галерея", batch)[0], 0)
        self.assertIn("фото/а.jpg", ae("library", "find", "поехали на рыбалку")[1])
        self.assertEqual(ae("library", "forbid", "Петю")[0], 0)
        said = ae("library", "find", "поехали на рыбалку")[1]
        self.assertNotIn("фото/а.jpg", said)
        self.assertIn("фото/б.jpg", said)
        self.assertEqual(ae("library", "rule", "титры крупнее", "--format", "урок")[0], 0)
        self.assertIn("## Формат: урок", (lib / "правила.md").read_text(encoding="utf-8"))
        self.assertIn("титры крупнее", ae("library", "rules", "--format", "урок")[1])

    @needs_ffmpeg
    def test_scan_sheet_describe_through_the_command(self):
        from test_library_inventory import video

        ae("library", "set", self.tmp / "биб")
        src = self.tmp / "камера"
        src.mkdir()
        video(src / "раз.mp4")
        video(src / "два.mp4")
        code, said = ae("library", "scan", "футажи", src)
        self.assertEqual(code, 0, said)
        self.assertIn("2", said)
        code, said = ae("library", "sheet", "футажи", "--n", "36")
        self.assertEqual(code, 0, said)
        sheet = next(line for line in said.splitlines() if line.endswith(".jpg"))
        self.assertTrue(os.path.isfile(sheet.split(": ", 1)[-1]))
        self.assertIn("1. ", said)
        self.assertEqual(ae("library", "scan", "футажи")[1].count(".mp4"), 2)


class FormatSkill(LibraryCase):
    @classmethod
    def setUpClass(cls):
        import shutil
        import tempfile
        from pathlib import Path

        cls.root = Path(tempfile.mkdtemp(prefix="aiediting скилл "))
        work = cls.root / "work" / "монтаж-урок"
        (work / "design").mkdir(parents=True)
        profile = {"format": "урок", "skill_name": "монтаж-урок", "language": "ru",
                   "asr": {"provider": "scribe", "language": "ru", "model": "scribe_v2", "base_url": None,
                           "api_key_env": "ELEVENLABS_API_KEY", "command": None},
                   "steps": STEPS, "params": {}, "approval": "plan", "design": "design/", "output_dir": "выпуски"}
        (work / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(AE), "build-skill", str(work / "profile.json"), str(cls.root / "out")],
                              capture_output=True, text=True, encoding="utf-8")
        assert proc.returncode == 0, proc.stdout + proc.stderr
        cls.skill = cls.root / "out" / "монтаж-урок"
        cls.addClassCleanup(shutil.rmtree, str(cls.root), True)

    def run_py(self, *argv):
        return subprocess.run([sys.executable, "-I", str(self.skill / "tools" / "run.py"), *map(str, argv)],
                              capture_output=True, text=True, encoding="utf-8", cwd=str(self.tmp), env=dict(os.environ))

    def test_the_library_goes_into_the_built_skill(self):
        pins = json.loads((self.skill / "pins.json").read_text(encoding="utf-8"))
        self.assertIn("library", pins["runtime_packages"])
        self.assertTrue((self.skill / "runtime" / "library" / "cli.py").is_file())
        proc = self.run_py("check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_note_without_a_library_writes_only_the_report(self):
        issue = self.tmp / "выпуск"
        proc = self.run_py("note", issue, "паузы короче")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("паузы короче", (issue / "отчёт.md").read_text(encoding="utf-8"))

    def test_note_goes_into_the_report_and_the_personal_rules(self):
        self.assertEqual(ae("library", "set", self.tmp / "биб")[0], 0)
        issue = self.tmp / "2026-11-13-рыбалка"
        proc = self.run_py("note", issue, "паузы короче", "--format")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("паузы короче", (issue / "отчёт.md").read_text(encoding="utf-8"))
        rules = (self.tmp / "биб" / "правила.md").read_text(encoding="utf-8")
        self.assertIn("## Формат: урок", rules)
        self.assertIn("2026-11-13-рыбалка: паузы короче", rules)
        self.run_py("note", issue, "титры крупнее")
        general = (self.tmp / "биб" / "правила.md").read_text(encoding="utf-8").split("## Формат")[0]
        self.assertIn("титры крупнее", general)

    def test_forbid_and_library_are_the_same_as_in_the_workshop(self):
        ae("library", "set", self.tmp / "биб")
        proc = self.run_py("forbid", "Петю")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Петю", (self.tmp / "биб" / "чего-нельзя.md").read_text(encoding="utf-8"))
        proc = self.run_py("library", "where")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, ae("library", "where")[1])

    def test_forbid_without_a_library_says_so(self):
        proc = self.run_py("forbid", "Петю")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("library set", proc.stdout)


if __name__ == "__main__":
    unittest.main()
