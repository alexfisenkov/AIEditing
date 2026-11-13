"""Gentle speech clean-up (`params.cleanup = "gentle"`) and repeats offered for the plan, on a synthetic recording."""
import unittest

from _support import TempDirCase, ffmpeg, needs_ffmpeg
from test_pipelines_helpers import Approver, asr_config, profile

# Words (tone bursts) and what lies between them, worked out by hand:
#   1.20–1.50  0.30 s of silence            → stays (not over 0.35 s)
#   2.00–2.80  0.80 s, a breath 2.67–2.75   → 0.3 s; the cut in the quietest point of 2.65–2.70, i.e. before the breath
#              (a fixed 0.12 s margin would cut at 2.68, inside it)
#   3.40–4.00  0.60 s of silence            → 0.2 s; the cut 100–150 ms before the word
#   4.60–5.10  0.50 s, a breath 4.75–4.95   → stays (a breath, not over 0.6 s)
WORDS = [(0.50, 1.20, "Сегодня"), (1.50, 2.00, "мы"), (2.80, 3.40, "смотрим"), (4.00, 4.60, "новый"), (5.10, 5.80, "монтаж.")]
BREATHS = [(2.67, 2.75), (4.75, 4.95)]
SECONDS = 6.4


def recording(path, words, breaths, duration):
    on = "+".join("between(t,{},{})".format(a, b) for a, b, _ in words)
    soft = "+".join("between(t,{},{})".format(a, b) for a, b in breaths) or "0"
    ffmpeg("-f", "lavfi", "-i", "color=c=black:s=160x120:r=25:d={}".format(duration), "-f", "lavfi", "-i",
           "aevalsrc='if({},0.5*sin(2*PI*440*t),0)+if({},0.02*sin(2*PI*170*t),0)':s=48000:d={}".format(on, soft, duration),
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-shortest", str(path))
    return path


def table(words):
    return {"words": [{"text": t, "start": a, "end": b} for a, b, t in words]}


def kept_between(keep, a, b):
    return sum(max(0.0, min(y, b) - max(x, a)) for x, y in keep)


@needs_ffmpeg
class Gentle(TempDirCase):
    def setUp(self):
        super().setUp()
        self.src = recording(self.tmp / "запись.mov", WORDS, BREATHS, SECONDS)

    def plan(self, words=WORDS, approve=None, **params):
        from runtime.pipelines.context import Context
        from runtime.pipelines.cutplan import plan_cut, plan_speech

        base = dict(gap=0.5, pad=0.12)
        base.update(params)
        ctx = Context(self.src, profile(["speech_spans", "cut_spans"], asr_config(self.tmp, table(words)), **base),
                      self.tmp / "выпуск", approve or Approver())
        plan_speech(ctx)
        plan_cut(ctx)
        return ctx

    def test_pauses_shrink_by_the_rules(self):
        keep = self.plan(cleanup="gentle").keep
        self.assertAlmostEqual(kept_between(keep, 1.20, 1.50), 0.30, delta=0.01)
        self.assertAlmostEqual(kept_between(keep, 2.00, 2.80), 0.30, delta=0.01)
        self.assertAlmostEqual(kept_between(keep, 3.40, 4.00), 0.20, delta=0.01)
        self.assertAlmostEqual(kept_between(keep, 4.60, 5.10), 0.50, delta=0.01)
        for a, b, _ in WORDS:
            self.assertAlmostEqual(kept_between(keep, a, b), b - a, delta=0.001, msg="a word is never cut into")

    def test_the_cut_lands_in_the_quietest_point_before_the_word(self):
        keep = self.plan(cleanup="gentle").keep
        resume = [a for a, _ in keep if 2.0 < a < 2.8]
        self.assertEqual(len(resume), 1, keep)
        self.assertTrue(2.65 <= resume[0] <= 2.67, "before the breath, 130–150 ms before the word: {}".format(resume[0]))
        resume = [a for a, _ in keep if 3.4 < a < 4.0]
        self.assertTrue(3.85 <= resume[0] <= 3.90, resume)

    def test_dense_and_no_key_cut_as_before(self):
        self.assertEqual(self.plan(cleanup="dense").keep, self.plan().keep)


REPEATING = [(0.50, 0.70, "я"), (0.90, 1.10, "я"), (1.30, 1.90, "хочу"), (2.10, 2.60, "сказать,"), (2.80, 3.20, "что"),
             (3.40, 3.60, "в"), (3.70, 4.10, "этом"), (4.30, 4.50, "в"), (4.60, 5.00, "этом"), (5.20, 5.80, "году.")]


class Repeats(unittest.TestCase):
    def test_the_same_words_twice_in_a_row(self):
        from runtime.pipelines.repeats import find

        found = find([{"text": t, "start": a, "end": b} for a, b, t in REPEATING])
        self.assertEqual([r["drop"] for r in found], [[0.5, 0.9], [3.4, 4.3]])
        self.assertEqual([r["said"] for r in found], ["я я", "в этом в этом"])
        self.assertTrue(all(r["why"] == "повтор" for r in found))

    def test_different_words_are_not_repeats(self):
        from runtime.pipelines.repeats import find

        said = [{"text": t, "start": i, "end": i + 0.5} for i, t in enumerate("мы монтируем ролик, а потом монтируем мы звук".split())]
        self.assertEqual(find(said), [])


@needs_ffmpeg
class RepeatsInThePlan(TempDirCase):
    def setUp(self):
        super().setUp()
        self.src = recording(self.tmp / "запись.mov", REPEATING, [], 6.2)

    def plan(self, approve):
        from runtime.pipelines.context import Context
        from runtime.pipelines.cutplan import plan_cut, plan_speech

        ctx = Context(self.src, profile(["speech_spans", "cut_spans"], asr_config(self.tmp, table(REPEATING)),
                                        gap=0.5, pad=0.12, cleanup="gentle"), self.tmp / "выпуск", approve)
        plan_speech(ctx)
        plan_cut(ctx)
        return ctx

    def test_no_leaves_the_repeats(self):
        approve = Approver(answers={"repeats": False})
        keep = self.plan(approve).keep
        self.assertIn("repeats", approve.asked)
        self.assertAlmostEqual(kept_between(keep, 0.5, 0.7), 0.2, delta=0.001)
        self.assertAlmostEqual(kept_between(keep, 3.4, 4.1), 0.7, delta=0.05)

    def test_yes_cuts_the_rows_left_in_the_answer(self):
        def keep_the_second(payload):
            payload["items"] = [r for r in payload["items"] if r["said"] == "я я"]
        ctx = self.plan(Approver(edits={"repeats": keep_the_second}))
        self.assertAlmostEqual(kept_between(ctx.keep, 0.5, 0.7), 0.0, delta=0.001)
        self.assertAlmostEqual(kept_between(ctx.keep, 3.7, 4.1), 0.4, delta=0.001, msg="the row taken out stays")
        self.assertTrue(any("повтор" in c["why"] for c in ctx.report["cuts"]))

    def test_dense_without_the_key_asks_nothing_new(self):
        from runtime.pipelines.context import Context
        from runtime.pipelines.cutplan import plan_cut, plan_speech

        approve = Approver()
        ctx = Context(self.src, profile(["speech_spans", "cut_spans"], asr_config(self.tmp, table(REPEATING)),
                                        gap=0.5, pad=0.12, fillers_cut=["э-э"]), self.tmp / "выпуск", approve)
        plan_speech(ctx)
        plan_cut(ctx)
        self.assertNotIn("repeats", approve.asked)


if __name__ == "__main__":
    unittest.main()
