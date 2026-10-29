"""What the cut throws away never comes back through a plan: no card or insert slot on it, no stray first
word of a dropped take in captions or sound, and the glossary's fixes of burned captions reach the report."""
import importlib.util
import unittest

from _support import TempDirCase, make_av, needs_ffmpeg
from test_animations_plan import FILES, STEPS, FakeCtx, said
from test_pipelines_helpers import Approver, asr_config, profile

HAVE_PIL = importlib.util.find_spec("PIL") is not None
KEEP = [(0.9, 3.2), (69.9, 80.0)]  # the pause 3.2–69.9 is cut, and with it the dropped take at 12


def alive(t, keep):
    return any(a <= t < b for a, b in keep)


class SlotsOnKeptSpeech(unittest.TestCase):
    def test_card_slots_are_not_on_a_cut_take_or_a_pause(self):
        from runtime.pipelines.cards import plan_cards

        words = said(1.0, "Это первая мысль про скилл.") + said(12.0, "Вторая мысль не вышла") \
            + said(70.0, "Вторая мысль вышла.")
        ctx = FakeCtx(words, cards=True)
        ctx.keep = KEEP
        plan_cards(ctx)
        starts = [s["start"] for s in ctx.asked["cards"]["items"]]
        self.assertEqual(starts, [1.0, 70.0])
        self.assertTrue(all(alive(s, KEEP) for s in starts))

    def test_animation_slots_are_not_on_cut_speech_either(self):
        from runtime.pipelines.anim_slots import slots

        ctx = FakeCtx(said(10.0, FILES + ".") + said(70.0, STEPS), animations={"every": 45})
        ctx.keep = KEEP
        self.assertEqual([(s["template"], s["start"]) for s in slots(ctx)], [("шаги", 70.0)])


class LeftoverOfADroppedTake(unittest.TestCase):
    def test_a_word_of_zero_length_at_the_cut_is_not_kept_by_the_span_that_ends_there(self):
        from runtime.pipelines.words import mapped

        word = {"text": "В", "start": 1.0, "end": 1.0}
        self.assertEqual(mapped([word], [(0.5, 1.0)]), [], "the end of a span is the start of what follows")
        self.assertEqual([w["text"] for w in mapped([word], [(1.0, 2.0)])], ["В"])


@needs_ffmpeg
class DroppedTakeLeavesNothing(TempDirCase):
    """The take «В ближайшее время…» (Scribe gives its «В» zero length) is dropped; the next one stays."""

    WORDS = [{"text": "В", "start": 1.0, "end": 1.0}, {"text": "ближайшее", "start": 1.02, "end": 1.4},
             {"text": "время", "start": 1.45, "end": 1.7}, {"text": "я", "start": 1.75, "end": 1.8},
             {"text": "проведу", "start": 1.85, "end": 2.0}, {"text": "в", "start": 3.5, "end": 3.52},
             {"text": "ближайшее", "start": 3.52, "end": 3.9}, {"text": "время", "start": 3.95, "end": 4.2},
             {"text": "я", "start": 4.25, "end": 4.3}, {"text": "Fixfield.", "start": 4.35, "end": 4.8}]

    def planned(self, steps, **params):
        from runtime.pipelines.context import Context
        from runtime.pipelines.registry import PLAN

        src = make_av(self.tmp / "дубль.mp4", [(1.0, 2.0), (3.5, 4.8)], 6.0, size="320x180")
        prof = profile(steps, asr_config(self.tmp, {"words": self.WORDS}), gap=0.5, pad=0.12, retakes="last_good",
                       glossary={"fixfield": "Higgsfield"}, **params)
        ctx = Context(src, prof, self.tmp / "выпуск", Approver())
        for step in ("speech_spans", "cut_spans"):
            PLAN[step](ctx)
        return ctx

    def test_no_first_word_in_the_cuts_and_none_in_the_captions(self):
        from runtime.pipelines.captions import burned

        ctx = self.planned(["speech_spans", "cut_spans", "plate"], captions="burned")
        self.assertEqual([a for a, _ in ctx.keep if a < 3.0], [], "a sliver of the dropped take is kept")
        texts = [c["text"] for c in burned(ctx, ctx.keep)]
        self.assertEqual(" ".join(texts), "в ближайшее время я Higgsfield.")

    def test_glossary_fixes_of_burned_captions_are_in_the_report(self):
        from runtime.pipelines.captions import burned
        from runtime.pipelines.report import finish

        ctx = self.planned(["speech_spans", "cut_spans", "plate", "overlay_png"], captions="burned")
        burned(ctx, ctx.keep)
        self.assertEqual([(f["from"], f["to"]) for f in ctx.report["fixes"]], [("Fixfield", "Higgsfield")])
        self.assertEqual(ctx.report["fixes"][0]["index"], 2)  # the second cue: «в ближайшее время я» comes first
        ctx.report["outputs"] = []
        self.assertIn("«Fixfield» → «Higgsfield»", finish(ctx)["report"].read_text(encoding="utf-8"))

    def test_the_srt_step_lists_its_own_fixes_not_twice(self):
        from runtime.pipelines.captions import burned

        ctx = self.planned(["speech_spans", "cut_spans", "plate", "overlay_png", "write_srt"], captions="burned")
        burned(ctx, ctx.keep)
        self.assertEqual(ctx.report["fixes"], [])


if __name__ == "__main__":
    unittest.main()
