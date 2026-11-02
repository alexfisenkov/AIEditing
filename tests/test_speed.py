"""params.speed: the whole finished video a little faster — picture, voice, subtitles and timecodes together."""
import re
import unittest

from _support import TempDirCase, make_av, needs_ffmpeg
from test_pipelines_helpers import LESSON, LESSON_SECONDS, Approver, asr_config, bursts, profile

STEPS = ["speech_spans", "cut_spans", "verify_words", "drift_ms", "loudnorm", "write_srt"]
RATE = 1.05


def last_stamp(srt_text):
    h, m, s, ms = re.findall(r"--> (\d+):(\d+):(\d+),(\d+)", srt_text)[-1]
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


@needs_ffmpeg
class Speed(TempDirCase):
    def setUp(self):
        super().setUp()
        self.src = make_av(self.tmp / "урок.mp4", [(a, b) for a, b, _ in LESSON], LESSON_SECONDS, size="320x180")
        self.asr = asr_config(self.tmp, bursts(LESSON))

    def edit(self, name, **params):
        from runtime import pipelines

        base = dict(gap=0.5, pad=0.12, lufs=-16, fillers_cut=[], retakes=False, glossary={})
        base.update(params)
        return pipelines.run(self.src, profile(STEPS, self.asr, **base), self.tmp / name, Approver())

    def test_everything_goes_faster_together(self):
        from runtime.media import probe

        plain, fast = self.edit("обычно"), self.edit("быстрее", speed=RATE)
        a, b = probe(plain["output"]), probe(fast["output"])
        self.assertAlmostEqual(b["duration"], a["duration"] / RATE, delta=0.1)
        self.assertAlmostEqual(b["audio_duration"], a["audio_duration"] / RATE, delta=0.1)
        self.assertAlmostEqual(b["fps"], a["fps"], delta=0.5, msg="same frame rate, frames dropped")
        self.assertLess(fast["drift_ms"], 40)
        self.assertEqual(fast["words_lost"], [])
        was = last_stamp(plain["srt"].read_text(encoding="utf-8"))
        now = last_stamp(fast["srt"].read_text(encoding="utf-8"))
        self.assertAlmostEqual(now, was / RATE, delta=0.02)
        self.assertLessEqual(now, b["duration"] + 0.05)

    def test_report_says_the_speed(self):
        report = self.edit("быстрее", speed=RATE)
        self.assertIn("ускорен", report["report"].read_text(encoding="utf-8"))

    def test_no_speed_no_second_encode(self):
        from runtime.pipelines.speed import rate_of

        self.assertEqual(rate_of(1.0), 1.0)
        self.assertEqual(rate_of(1), 1.0)
        self.assertEqual(rate_of("1.05"), 1.05)

    def test_a_strange_speed_is_refused(self):
        from runtime.pipelines.errors import PipelineError
        from runtime.pipelines.speed import rate_of

        for bad in (0, -1, 0.2, 5, "быстро"):
            with self.assertRaises(PipelineError):
                rate_of(bad)


if __name__ == "__main__":
    unittest.main()
