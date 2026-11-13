"""The `broll` step through the whole pipeline: inserts over the video, the same length, in the report, a shoot list beside it."""
import os
import unittest
from unittest import mock

import _support  # noqa: F401  (puts the skill on sys.path)
from _support import TempDirCase, ffmpeg, make_av, needs_ffmpeg
from runtime.library import inventory, paths
from test_broll_media import colour_at, volume
from test_pipelines_helpers import Approver, asr_config, profile, sha

SEA = "Летом мы поехали на море и купались каждый день."
SETTINGS = "Потом открываем настройки браузера и смотрим новые вкладки."


def words(*phrases):
    out = []
    for text, start in phrases:
        for i, w in enumerate(text.split()):
            out.append({"text": w, "start": round(start + i * 0.4, 3), "end": round(start + i * 0.4 + 0.35, 3)})
    return {"words": out}


@needs_ffmpeg
class BrollThroughThePipeline(TempDirCase):
    def setUp(self):
        super().setUp()
        self.lib = paths.make_layout(self.tmp / "библиотека")
        env = mock.patch.dict(os.environ, {"AIEDITING_LIBRARY": str(self.lib)})
        env.start()
        self.addCleanup(env.stop)
        self.src = make_av(self.tmp / "эфир.mp4", [(0.2, 1.5)], 14, size="160x120", rate=25)
        clip = self.lib / "футажи" / "море.mp4"
        clip.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg("-f", "lavfi", "-i", "color=c=red:s=320x180:r=25:d=10", "-f", "lavfi", "-i", "sine=f=1000:d=10",
               "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(clip))
        inventory.describe(self.lib, "футажи", [
            {"f": "футажи/море.mp4", "type": "видео", "orient": "гор", "dur": 10.0, "best": [[1.0, 8.0]], "what": "море",
             "tags": ["море"], "phrases": ["поехали на море"], "who": ["Аня"]},
            {"f": "футажи/горы.mp4", "type": "видео", "orient": "гор", "dur": 10.0, "best": [], "what": "горы",
             "tags": ["горы"], "phrases": []}])
        (self.lib / "футажи" / "горы.mp4").write_bytes(b"x")
        self.asr = asr_config(self.tmp, words((SEA, 2.0), (SETTINGS, 8.0)))
        self.out = self.tmp / "выпуски" / "эфир"

    def run_it(self, **params):
        from runtime import pipelines

        prof = profile(["broll"], self.asr, broll={"every": 5.0}, **params)
        return pipelines.run(self.src, prof, self.out, Approver())

    def test_the_insert_stands_over_its_phrase_without_its_sound_and_the_length_is_the_same(self):
        before = sha(self.src)
        report = self.run_it()
        from runtime.media import probe

        video = report["output"]
        self.assertGreater(colour_at(video, 3.5)[0], 180)
        self.assertLess(colour_at(video, 3.5)[1], 60)
        self.assertLess(colour_at(video, 7.0)[0], 40)      # after the phrase: the speaker again
        self.assertLess(colour_at(video, 10.0)[0], 40)     # the place that found no frame stays as it was
        self.assertAlmostEqual(probe(video)["duration"], probe(self.src)["duration"], delta=0.15)
        self.assertLess(volume(video, 2.5, 5.0), -60)
        self.assertEqual(sha(self.src), before)

    def test_the_report_lists_the_insert_with_who_is_on_it_and_names_the_shoot_list(self):
        report = self.run_it()
        text = (self.out / "отчёт.md").read_text(encoding="utf-8")
        self.assertIn("## Вставки", text)
        self.assertIn(SEA, text)
        self.assertIn("на кадре: Аня", text)
        self.assertIn("## Досъёмка", text)
        self.assertIn("досъёмка.md", text)
        self.assertEqual(report["broll"][0]["who"], ["Аня"])

    def test_the_shoot_list_is_a_file_next_to_the_video_with_time_phrase_what_and_orientation(self):
        self.run_it()
        text = (self.out / "досъёмка.md").read_text(encoding="utf-8")
        self.assertIn(SETTINGS, text)
        self.assertIn("0:00:08.0", text)
        self.assertIn("горизонтальный", text)
        self.assertNotIn(SEA, text, "a place with a frame is not a place to shoot")

    def test_the_insert_is_laid_before_the_speed_so_it_speeds_up_with_the_voice(self):
        report = self.run_it(speed=1.25)
        from runtime.media import probe

        self.assertAlmostEqual(probe(report["output"])["duration"], 14 / 1.25, delta=0.2)
        self.assertGreater(colour_at(report["output"], 3.5 / 1.25)[0], 180)
        self.assertLess(colour_at(report["output"], 6.5 / 1.25)[0], 40)
        self.assertAlmostEqual(report["broll"][0]["at"], 2.0 / 1.25, delta=0.1)

    def test_a_profile_without_the_step_leaves_the_picture_and_writes_no_list(self):
        from runtime import pipelines

        prof = profile(["loudnorm"], self.asr, broll=True)
        report = pipelines.run(self.src, prof, self.out, Approver())
        self.assertLess(colour_at(report["output"], 3.5)[0], 40)
        self.assertFalse((self.out / "досъёмка.md").exists())
        self.assertNotIn("## Вставки", (self.out / "отчёт.md").read_text(encoding="utf-8"))

    def test_a_person_who_says_no_gets_no_insert_and_no_list(self):
        from runtime import pipelines

        prof = profile(["broll"], self.asr, broll={"every": 5.0})
        report = pipelines.run(self.src, prof, self.out, Approver(answers={"broll": False}))
        self.assertLess(colour_at(report["output"], 3.5)[0], 40)
        self.assertFalse((self.out / "досъёмка.md").exists())


if __name__ == "__main__":
    unittest.main()
