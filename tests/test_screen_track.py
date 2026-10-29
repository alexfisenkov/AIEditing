"""Separate camera and screen files: `run.py edit --screen` and `ae.py trial --screen` hand the screen to the
real pipeline, so «камера в бок, экран в бок» is proposed — and without it the report says why it is not."""
import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout
from unittest import mock

from _support import SKILL, TempDirCase, ffmpeg, make_av, needs_ffmpeg
from test_pipelines_helpers import asr_config

sys.path.insert(0, str(SKILL / "tools"))

WORDS = {"words": [{"text": "смотрите", "start": 0.5, "end": 1.2}, {"text": "сюда.", "start": 1.3, "end": 1.9}]}
FACE = {"x": 110, "y": 40, "w": 100, "h": 100}
NO_SCREEN = "файл экрана не передан"


def lesson_profile(tmp):
    return {"format": "урок", "skill_name": "монтаж-урок", "language": "ru", "asr": asr_config(tmp, WORDS),
            "steps": ["detect_layout", "motion"], "params": {"layout": "separate_tracks", "face": FACE},
            "approval": "plan", "design": "design/", "taste": [], "output_dir": str(tmp / "выпуски")}


@needs_ffmpeg
class ScreenFile(TempDirCase):
    def setUp(self):
        super().setUp()
        self.camera = make_av(self.tmp / "камера.mp4", [(0.5, 1.9)], 3.0, size="320x180")
        self.screen = self.tmp / "экран.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=0x404040:s=320x180:r=50:d=3", "-c:v", "libx264", "-preset",
               "ultrafast", "-pix_fmt", "yuv420p", self.screen)

    def build(self):
        folder = self.tmp / "work" / "монтаж-урок"
        folder.mkdir(parents=True)
        (folder / "profile.json").write_text(json.dumps(lesson_profile(self.tmp), ensure_ascii=False),
                                             encoding="utf-8")
        subprocess.run([sys.executable, str(SKILL / "tools" / "ae.py"), "build-skill", str(folder / "profile.json"),
                        str(self.tmp / "out")], check=True, capture_output=True)
        return self.tmp / "out" / "монтаж-урок"

    def run_skill(self, skill, *args):
        return subprocess.run([sys.executable, "-I", str(skill / "tools" / "run.py"), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8", cwd=str(self.tmp))

    def test_built_skill_passes_the_screen_to_the_pipeline(self):
        skill = self.build()
        alone = self.tmp / "без экрана"
        done = self.run_skill(skill, "edit", self.camera, "--out", alone)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn(NO_SCREEN, (alone / "отчёт.md").read_text(encoding="utf-8"))
        issue = self.tmp / "с экраном"
        first = self.run_skill(skill, "edit", self.camera, "--screen", self.screen, "--out", issue)
        self.assertEqual(first.returncode, 3, first.stdout + first.stderr)
        self.assertEqual(json.loads((issue / "вопросы.json").read_text(encoding="utf-8"))["key"], "motion")
        (issue / "ответы.json").write_text(json.dumps({"motion": True}), encoding="utf-8")
        second = self.run_skill(skill, "edit", self.camera, "--screen", self.screen, "--out", issue)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        report = (issue / "отчёт.md").read_text(encoding="utf-8")
        self.assertNotIn(NO_SCREEN, report)

    def test_trial_passes_the_screen_cut_to_the_same_piece(self):
        from aelib.cli import main

        work = self.tmp / "мастерская"
        with mock.patch.dict(os.environ, {"AIEDITING_WORK": str(work), "AIEDITING_NO_SERVE": "1"}):
            def ae(*args):
                with redirect_stdout(io.StringIO()) as buf:
                    code = main([str(a) for a in args])
                return code, buf.getvalue()

            self.assertEqual(ae("init", "--title", "Проба")[0], 0)
            self.assertEqual(ae("formats", "урок")[0], 0)
            (work / "монтаж-урок" / "profile.json").write_text(
                json.dumps(lesson_profile(self.tmp), ensure_ascii=False), encoding="utf-8")
            code, out = ae("trial", "монтаж-урок", self.camera, "--screen", self.screen, "--start", "0",
                           "--duration", "2.5")
            self.assertEqual(code, 3, out)
            asked = json.loads((work / "монтаж-урок" / "trials" / "01" / "вопросы.json").read_text(encoding="utf-8"))
            self.assertEqual(asked["key"], "motion")
            self.assertTrue((work / "монтаж-урок" / "trials" / "01" / "экран.mp4").is_file(),
                            "the screen is cut to the same piece as the camera")
