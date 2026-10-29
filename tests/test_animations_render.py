"""An approved insert is laid in the corner opposite the face and listed in the report — with the
HyperFrames render replaced by a white clip with alpha, so neither Node nor Chrome is needed."""
import re
from pathlib import Path
from unittest import mock

from _support import TempDirCase, ffmpeg, needs_ffmpeg
from test_blur_static import gray_frame
from test_pipelines_helpers import Approver, asr_config

SECONDS = 12.0
WORDS = [{"text": w, "start": 2.0 + k * 0.4, "end": 2.3 + k * 0.4}
         for k, w in enumerate("файлы agents.md, memory.md, spec, plan.".split())]
FACE = {"x": 480, "y": 240, "w": 120, "h": 100}  # bottom-right: the insert goes top-left
PAGES = []  # the pages the fake renderer got (the run folder is gone after the run)


def fake_render_mov(project, out, fps=30):
    """What hyperframes.render_mov makes, minus the browser: a clip of the page's size and length."""
    page = (Path(project) / "index.html").read_text(encoding="utf-8")
    PAGES.append(page)
    w, h = re.search(r'data-width="(\d+)" data-height="(\d+)"', page).groups()
    seconds = re.search(r'data-duration="([\d.]+)"', page).group(1)
    ffmpeg("-f", "lavfi", "-i", "color=c=white:s={}x{}:r={}:d={}".format(w, h, fps, seconds),
           "-vf", "format=argb", "-c:v", "qtrle", str(out))
    return Path(out)


@needs_ffmpeg
class AnimationOverlay(TempDirCase):
    def setUp(self):
        super().setUp()
        self.src = self.tmp / "урок.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=black:s=640x360:r=25:d={}".format(SECONDS),
               "-f", "lavfi", "-i", "sine=f=440:d={}".format(SECONDS), "-c:v", "libx264", "-preset", "ultrafast",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(self.src))
        self.asr = asr_config(self.tmp, {"words": WORDS})

    def run_lesson(self, approve):
        from runtime import pipelines

        profile = {"format": "урок", "skill_name": "монтаж-урок", "language": "ru", "asr": self.asr,
                   "output_dir": str(self.tmp), "steps": ["detect_layout", "animations"],
                   "params": {"layout": "screen_face_window", "face": FACE, "animations": {"every": 45}}}
        with mock.patch("runtime.render.hyperframes.missing", return_value=None), \
                mock.patch("runtime.render.hyperframes.render_mov", side_effect=fake_render_mov) as render:
            report = pipelines.run(self.src, profile, self.tmp / "выпуск", approve)
        return report, render

    def test_answer_becomes_an_insert_opposite_the_face_and_a_report_line(self):
        approve, PAGES[:] = Approver(), []
        report, render = self.run_lesson(approve)
        self.assertIn("animations", approve.asked)
        self.assertEqual(render.call_count, 1)
        page = PAGES[0]
        for name in ("agents.md", "memory.md", "spec", "plan"):
            self.assertIn(name, page)
        self.assertNotIn("{{", page)
        rows = gray_frame(report["output"], 4.5, (640, 360))
        self.assertGreater(rows[40][60], 200, "the insert sits in the top-left corner")
        self.assertLess(rows[300][560], 40, "the face corner stays clear")
        self.assertLess(rows[40][560], 40, "nothing in the other corners")
        self.assertLess(gray_frame(report["output"], 10.5, (640, 360))[40][60], 40, "gone after its slot")
        text = report["report"].read_text(encoding="utf-8")
        self.assertIn("## Анимации", text)
        self.assertRegex(text, r"- 0:00:02\.0–0:00:0\d\.\d «файлы»: Файлы · agents\.md, memory\.md, spec, plan")

    def test_refused_question_leaves_the_video_alone(self):
        report, render = self.run_lesson(Approver(answers={"animations": False}))
        self.assertEqual(render.call_count, 0)
        self.assertNotIn("## Анимации", report["report"].read_text(encoding="utf-8"))
