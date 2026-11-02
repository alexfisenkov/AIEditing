"""Vertical keeps continuous speech: a stretch with no word is cut even when it is louder than the threshold
(breath, click, room noise), a word keeps its first and last sounds; the lesson and the stream cut as before."""
import json
import unittest

from _support import SKILL, TempDirCase, _between, ffmpeg, needs_ffmpeg
from test_pipelines_helpers import Approver, asr_config, profile

PRESETS = SKILL / "templates" / "profiles"
LOUD_WORDS = [(1.0, 1.5), (1.62, 2.0), (4.0, 4.6)]   # tone at 0.5: said words
NOISE = [(2.4, 3.6)]                                  # tone at 0.1 (about −20 dB): above −30 dB, no word in it
WORDS = [{"text": t, "start": a, "end": b, "type": "word"}
         for (a, b), t in zip(LOUD_WORDS, ["Это", "скилл.", "Дальше"])]


def preset(name):
    return json.loads((PRESETS / (name + ".json")).read_text(encoding="utf-8"))


def inside(span, keep):
    return any(a <= span[0] + 1e-6 and span[1] <= b + 1e-6 for a, b in keep)


def overlap(span, keep):
    return sum(max(0.0, min(b, span[1]) - max(a, span[0])) for a, b in keep)


class ByWords(unittest.TestCase):
    def test_a_wordless_stretch_longer_than_the_gap_goes_even_if_it_is_loud(self):
        from runtime.pipelines.wordcut import by_words

        keep = by_words([(0.0, 10.0)], WORDS, join=0.25, total=10.0)
        self.assertEqual(keep, [(0.92, 2.12), (3.92, 4.72)], "the pause 1.5–1.62 stays, 2.0–4.0 goes")

    def test_first_and_last_sounds_stay_and_a_word_is_never_cut_into(self):
        from runtime.pipelines.wordcut import by_words

        keep = by_words([(0.0, 10.0)], WORDS, join=0.25, total=10.0)
        for w in WORDS:
            self.assertTrue(inside((w["start"] - 0.08, w["end"] + 0.12), keep), w["text"])
        quiet_start = by_words([(1.3, 2.2)], WORDS[:2], join=0.25, total=10.0)
        self.assertTrue(inside((1.0, 2.0), quiet_start), "the recogniser's word is kept whole")

    def test_the_margin_is_trimmed_to_where_there_is_sound(self):
        from runtime.pipelines.wordcut import by_words

        self.assertEqual(by_words([(1.0, 1.5)], WORDS[:1], join=0.25, total=10.0), [(1.0, 1.5)])

    def test_without_words_the_loudness_spans_stay(self):
        from runtime.pipelines.wordcut import by_words

        self.assertEqual(by_words([(0.5, 3.0)], [], join=0.25, total=10.0), [(0.5, 3.0)])

    def test_a_word_too_long_to_be_said_does_not_hold_its_silence(self):
        """Nothing is heard under it, so nothing tells where it really is: only the sound stays, not a minute of quiet."""
        from runtime.pipelines.wordcut import by_words

        words = [{"text": "слово", "start": 10.0, "end": 70.0, "type": "word"}]
        self.assertEqual(by_words([(0.0, 5.0), (80.0, 85.0)], words, join=0.25, total=100.0), [])
        self.assertEqual(by_words([(9.5, 11.0)], words, join=0.25, total=100.0), [(9.92, 11.0)])


class Presets(unittest.TestCase):
    def test_only_the_vertical_asks_for_continuous_speech(self):
        self.assertEqual(preset("vertical")["params"]["word_gap"], 0.25)
        for name in ("stream", "lesson", "youtube", "custom"):
            self.assertNotIn("word_gap", preset(name)["params"], name)


@needs_ffmpeg
class OnARecording(TempDirCase):
    def setUp(self):
        super().setUp()
        on, noise = _between(LOUD_WORDS), _between(NOISE)
        self.src = self.tmp / "вертикаль.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=black:s=160x120:r=25:d=5.5",
               "-f", "lavfi", "-i", "aevalsrc='if({},0.5,if({},0.1,0))*sin(2*PI*440*t)':s=48000:d=5.5".format(on, noise),
               "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", self.src)

    def planned(self, name):
        from runtime.pipelines.context import Context
        from runtime.pipelines.registry import PLAN

        params = {k: v for k, v in preset(name)["params"].items() if k not in ("vertical_source", "clips")}
        prof = profile(["speech_spans", "cut_spans"], asr_config(self.tmp, {"words": WORDS}), **params)
        ctx = Context(self.src, prof, self.tmp / name, Approver())
        for step in ("speech_spans", "cut_spans"):
            PLAN[step](ctx)
        return ctx

    def test_vertical_cuts_the_loud_stretch_with_no_word(self):
        ctx = self.planned("vertical")
        self.assertLess(overlap((2.2, 3.8), ctx.keep), 0.01, "noise above −30 dB with no word is cut")
        for a, b in LOUD_WORDS:
            self.assertTrue(inside((a - 0.05, b + 0.05), ctx.keep), "word {}–{} cut into".format(a, b))
        self.assertTrue(any(c["start"] <= 2.5 and c["end"] >= 3.5 for c in ctx.report["cuts"]))

    def test_lesson_cuts_by_loudness_exactly_as_before(self):
        from runtime.media import speech_spans

        ctx = self.planned("lesson")
        self.assertEqual(ctx.keep, speech_spans(self.src, gap=0.5, pad=0.12, db=-30))
        self.assertGreater(overlap(NOISE[0], ctx.keep), 1.0, "the lesson keeps what is loud, word or not")


if __name__ == "__main__":
    unittest.main()
