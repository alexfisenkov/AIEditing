"""Stream pipeline: nothing cut; only areas the person ticked are blurred; .srt and loudness; source intact."""
import unittest

from _support import TempDirCase, needs_ffmpeg
from test_blur_static import checker_video, gray_frame, sharpness
from test_pipelines_helpers import Approver, asr_config, loudness, profile, sha

WORDS = {"words": [{"text": "пишите", "start": 0.2, "end": 0.6}, {"text": "на", "start": 0.7, "end": 0.8},
                   {"text": "ivan@example.com", "start": 0.9, "end": 1.8}]}
STEPS = ["find_secrets", "blur_regions", "loudnorm", "write_srt"]
SIZE = (320, 240)
AREA = {"x": 80, "y": 60, "w": 120, "h": 80, "start": 0.0, "end": 3.0, "track": False}


@needs_ffmpeg
class Stream(TempDirCase):
    def setUp(self):
        super().setUp()
        self.src = checker_video(self.tmp / "эфир.mp4")
        self.prof = profile(STEPS, asr_config(self.tmp, WORDS), lufs=-16, ocr=False, cut=False)
        self.out = self.tmp / "выпуски" / "эфир"

    def test_ticked_area_blurred_nothing_cut(self):
        from runtime import pipelines
        from runtime.media import probe

        before = sha(self.src)
        seen = {}

        def tick(payload):
            seen["kinds"] = [c["kind"] for c in payload["candidates"]]
            payload["extra"].append(dict(AREA))

        report = pipelines.run(self.src, self.prof, self.out, Approver(edits={"secrets": tick}))
        self.assertIn("email", seen["kinds"], "the spoken e-mail is on the list for the person")
        self.assertAlmostEqual(probe(report["output"])["duration"], probe(self.src)["duration"], delta=0.05)
        self.assertEqual(report["cuts"], [])
        self.assertEqual(len(report["blurred"]), 1)
        mine, orig = gray_frame(report["output"], 1.5, SIZE), gray_frame(self.src, 1.5, SIZE)
        self.assertLess(sharpness(mine, 100, 80, 80, 40), sharpness(orig, 100, 80, 80, 40) / 4)
        self.assertGreater(sharpness(mine, 240, 180, 60, 40), sharpness(orig, 240, 180, 60, 40) / 2)
        self.assertTrue(report["srt"].is_file())
        self.assertAlmostEqual(loudness(report["output"]), -16, delta=1.5)
        self.assertEqual(sha(self.src), before)
        names = sorted(p.name for p in self.out.iterdir())
        self.assertEqual(names, sorted(["эфир.mp4", "эфир.srt", "отчёт.md"]), "only the result, no leftovers")
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), sorted(["эфир.mp4", "выпуски",
                                                                             "fake_asr.py", "слова.json"]))

    def test_nothing_is_blurred_without_a_tick(self):
        from runtime import pipelines

        report = pipelines.run(self.src, self.prof, self.out, Approver())
        self.assertEqual(report["blurred"], [])
        report = pipelines.run(self.src, self.prof, self.tmp / "нет",
                               Approver(answers={"secrets": False},
                                        edits={"secrets": lambda p: p["extra"].append(dict(AREA))}))
        self.assertEqual(report["blurred"], [], "a «нет» closes nothing even with an area drawn")


if __name__ == "__main__":
    unittest.main()
