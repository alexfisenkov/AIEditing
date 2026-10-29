"""A built format skill: «смонтируй <путь>» → its issue folder only; decisions go to the person; remarks to the report."""
import datetime as dt
import json
import subprocess
import sys

from _support import SKILL, TempDirCase

AE = SKILL / "tools" / "ae.py"

# Stands in for runtime/pipelines (task 03): asks one decision, then writes the clip and the report.
FAKE_PIPELINES = '''
from pathlib import Path


def run(src, profile, outdir, approve):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    payload = {"key": "cuts", "cuts": [[1.0, 2.0], [3.0, 4.0]]}
    if not approve("cuts", payload):
        raise SystemExit("отказ")
    (outdir / "ролик.mp4").write_bytes(b"video")
    (outdir / "отчёт.md").write_text("# Отчёт\\n\\nВырезано: {}\\n".format(payload["cuts"]), encoding="utf-8")
    return {"output": outdir / "ролик.mp4", "srt": None, "cuts": payload["cuts"], "blurred": [], "fixes": [],
            "drift_ms": 0.0}
'''


class FormatSkillRun(TempDirCase):
    def setUp(self):
        super().setUp()
        folder = self.tmp / "work" / "монтаж-урок"
        folder.mkdir(parents=True)
        profile = {"format": "урок", "skill_name": "монтаж-урок", "language": "ru",
                   "asr": {"provider": "whispercpp", "language": "ru", "model": None, "base_url": None,
                           "api_key_env": None, "command": None},
                   "steps": ["speech_spans", "cut_spans"], "params": {}, "approval": "plan",
                   "design": "design/", "taste": [], "output_dir": str(self.tmp / "выпуски")}
        (folder / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        subprocess.run([sys.executable, str(AE), "build-skill", str(folder / "profile.json"), str(self.tmp / "out")],
                       check=True, capture_output=True)
        self.skill = self.tmp / "out" / "монтаж-урок"
        (self.skill / "runtime" / "pipelines" / "__init__.py").write_text(FAKE_PIPELINES, encoding="utf-8")
        self.video = self.tmp / "запись урока.mp4"
        self.video.write_bytes(b"source")

    def run_skill(self, *args):
        return subprocess.run([sys.executable, "-I", str(self.skill / "tools" / "run.py"), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8", cwd=str(self.tmp))

    def test_edit_asks_then_lands_in_the_issue_folder(self):
        first = self.run_skill("edit", self.video, "--topic", "Урок 14")
        self.assertEqual(first.returncode, 3, first.stdout + first.stderr)
        issue = self.tmp / "выпуски" / "{}-урок-14".format(dt.date.today().isoformat())
        question = json.loads((issue / "вопросы.json").read_text(encoding="utf-8"))
        self.assertEqual(question["payload"]["cuts"], [[1.0, 2.0], [3.0, 4.0]])
        (issue / "ответы.json").write_text(json.dumps({"cuts": {"ok": True, "payload": {"cuts": [[1.0, 2.0]]}}}),
                                          encoding="utf-8")
        second = self.run_skill("edit", self.video, "--out", issue)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertTrue((issue / "ролик.mp4").is_file())
        self.assertIn("[[1.0, 2.0]]", (issue / "отчёт.md").read_text(encoding="utf-8"))
        self.assertEqual(self.video.read_bytes(), b"source")

    def test_remark_goes_to_the_report_and_suggests_refinement(self):
        issue = self.tmp / "выпуски" / "2026-10-29-урок"
        issue.mkdir(parents=True)
        (issue / "отчёт.md").write_text("# Отчёт\n\nВырезано: 3 паузы\n", encoding="utf-8")
        out = self.run_skill("note", issue, "паузы всё ещё длинные")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("доработка монтаж-урок", out.stdout)
        self.run_skill("note", issue, "плашка мелкая")
        report = (issue / "отчёт.md").read_text(encoding="utf-8")
        self.assertEqual(report.count("## Замечания для доработки"), 1)
        self.assertRegex(report, r"паузы всё ещё длинные\n- \d{4}-\d{2}-\d{2}: плашка мелкая\n$")
        profile = json.loads((self.skill / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["taste"], [])  # the profile changes only through AIEditing
