"""The design chosen for a draft format is the one the trial and the built skill draw with — never AIEditing's own."""
import importlib.util
import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

from _support import SKILL, TempDirCase, make_av, needs_ffmpeg
from test_pipelines_helpers import LESSON, LESSON_SECONDS, asr_config, bursts

sys.path.insert(0, str(SKILL / "tools"))

HAVE_PIL = importlib.util.find_spec("PIL") is not None
STEPS = ["speech_spans", "cut_spans", "plate", "overlay_png"]
SIZE = (640, 360)
RED = "#FF0000"


def red_pixels(video, t=0.6):
    """How many clearly red pixels the frame at `t` seconds has (the draft's plate colour).

    The cuts leave the plate 0.12–1.12 s here, with a 0.3 s fade at each end: `t` is its middle."""
    w, h = SIZE
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-ss", str(t), "-i", str(video),
           "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, stdout=subprocess.PIPE, check=True).stdout
    px = [raw[i:i + 3] for i in range(0, w * h * 3, 3)]
    return sum(1 for r, g, b in px if r > 200 and g < 60 and b < 60)


@needs_ffmpeg
@unittest.skipUnless(HAVE_PIL, "Pillow not installed (ae.py doctor installs it)")
class DraftDesign(TempDirCase):
    def setUp(self):
        super().setUp()
        self.src = make_av(self.tmp / "урок.mp4", [(a, b) for a, b, _ in LESSON], LESSON_SECONDS, size="640x360")
        self.profile = {"format": "урок", "skill_name": "монтаж-урок", "language": "ru",
                        "asr": asr_config(self.tmp, bursts(LESSON)), "steps": STEPS,
                        "params": {"gap": 0.5, "pad": 0.12, "fillers_cut": ["э-э"], "retakes": "last_good",
                                   "chapters": {"plates": True, "timecodes": False}},
                        "approval": "plan", "design": "design/", "taste": [], "output_dir": str(self.tmp / "выпуски")}

    def draft(self, work):
        """A draft with the example design copied in and its chapter plate repainted red."""
        from aelib.cli import main

        def ae(*args):
            with redirect_stdout(io.StringIO()):
                return main([str(a) for a in args])

        self.assertEqual(ae("init", "--title", "Проба"), 0)
        self.assertEqual(ae("formats", "урок"), 0)
        folder = work / "монтаж-урок"
        self.assertEqual(ae("design-example", "монтаж-урок"), 0)
        tokens = folder / "design" / "tokens.json"
        data = json.loads(tokens.read_text(encoding="utf-8"))
        data["video"]["chapter"].update(bg=RED, bg_alpha=1.0)
        data["color"]["red"] = RED
        tokens.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        (folder / "profile.json").write_text(json.dumps(self.profile, ensure_ascii=False), encoding="utf-8")
        return folder, ae

    def test_trial_draws_the_plate_from_the_draft_design(self):
        from aelib.cli import main

        work = self.tmp / "мастерская"
        with mock.patch.dict(os.environ, {"AIEDITING_WORK": str(work), "AIEDITING_NO_SERVE": "1"}):
            folder, _ = self.draft(work)
            answers, code = folder / "ответы.json", 3
            for _ in range(6):
                with redirect_stdout(io.StringIO()):
                    args = ["trial", "монтаж-урок", str(self.src)]
                    code = main(args + (["--answers", str(answers)] if answers.is_file() else []))
                if code != 3:
                    break
                asked = json.loads((folder / "trials" / "01" / "вопросы.json").read_text(encoding="utf-8"))
                done = json.loads(answers.read_text(encoding="utf-8")) if answers.is_file() else {}
                answers.write_text(json.dumps(dict(done, **{asked["key"]: True})), encoding="utf-8")
            self.assertEqual(code, 0, "the trial reaches a finished clip, not a design error")
            clips = sorted((folder / "trials" / "01" / "out").glob("*.mp4"))
            self.assertTrue(clips, "the trial clip is in out/")
            self.assertGreater(red_pixels(clips[0]), 500, "the plate is the draft's red one, not AIEditing's graphite")

    def test_built_skill_draws_with_its_own_design_from_another_folder(self):
        work = self.tmp / "мастерская"
        with mock.patch.dict(os.environ, {"AIEDITING_WORK": str(work), "AIEDITING_NO_SERVE": "1"}):
            folder, _ = self.draft(work)
        subprocess.run([sys.executable, str(SKILL / "tools" / "ae.py"), "build-skill", str(folder / "profile.json"),
                        str(self.tmp / "out")], check=True, capture_output=True)
        skill = self.tmp / "out" / "монтаж-урок"
        elsewhere = self.tmp / "другая папка"
        elsewhere.mkdir()
        issue = self.tmp / "выпуск"
        answers = {}
        for _ in range(6):
            (issue.mkdir(exist_ok=True) or None)
            (issue / "ответы.json").write_text(json.dumps(answers), encoding="utf-8")
            done = subprocess.run([sys.executable, "-I", str(skill / "tools" / "run.py"), "edit", str(self.src),
                                   "--out", str(issue)], capture_output=True, text=True, encoding="utf-8",
                                  cwd=str(elsewhere))
            if done.returncode != 3:
                break
            answers[json.loads((issue / "вопросы.json").read_text(encoding="utf-8"))["key"]] = True
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        clips = sorted(issue.glob("*.mp4"))
        self.assertTrue(clips, "the finished clip is in the issue folder")
        self.assertGreater(red_pixels(clips[0]), 500, "the plate is the skill's own red one")


class VerticalHint(unittest.TestCase):
    def test_hint_does_not_cap_what_is_shot_vertically(self):
        row = next(f for f in json.loads((SKILL / "catalog" / "formats.json").read_text(encoding="utf-8"))["formats"]
                   if f["id"] == "vertical")
        self.assertNotIn("9:16 до 60 с", row["hint"])
        self.assertIn("нарезк", row["hint"])
        self.assertIn("снятое вертикально", row["hint"])


if __name__ == "__main__":
    unittest.main()
