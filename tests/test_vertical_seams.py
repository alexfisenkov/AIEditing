"""The seams of the lesson in a vertical: a cut goes from the end of the word before it, the neighbours' marks stay right,
«э-э» goes from inside the speech, and all of it reaches the burned captions of a clip."""
import json
import unittest
from unittest import mock

from _support import SKILL

PRESET = json.loads((SKILL / "templates" / "profiles" / "vertical.json").read_text(encoding="utf-8"))["params"]


def word(text, start, end, kind="word"):
    return {"text": text, "start": start, "end": end, "type": kind}


class Run(unittest.TestCase):
    def planned(self, words, loud, **params):
        from runtime.pipelines.context import Context
        from runtime.pipelines.cutplan import plan_cut, plan_speech

        ctx = Context.__new__(Context)
        ctx.params, ctx.notes, ctx.src, ctx.keep = dict(PRESET, **params), [], "x.mp4", [(0.0, 100.0)]
        ctx.steps, ctx.report, ctx.loud, ctx._timed, ctx.decisions = [], {}, None, False, []
        ctx.approve = lambda key, data: True
        ctx.info = {"duration": 100.0}
        ctx._words = {"words": words}
        with mock.patch("runtime.media.speech_spans", return_value=loud):
            plan_speech(ctx)
        plan_cut(ctx)
        return ctx

    def caption(self, ctx, start=0.0, end=100.0):
        from runtime.pipelines.captions import burned
        from runtime.pipelines.timeline import intersect

        return " ".join(c["text"] for c in burned(ctx, intersect(ctx.keep, start, end)))


class Hesitations(Run):
    WORDS = [word("вот", 1.0, 1.2), word("можно,", 1.3, 1.6), word("эээ,", 1.66, 2.0, "filler"), word("здесь", 2.05, 2.4),
             word("вычитать.", 2.45, 3.0)]

    def test_the_preset_takes_them_out_and_keeps_ну_and_вот(self):
        self.assertEqual(PRESET["fillers_keep"], ["ну", "вот"])
        ctx = self.planned(self.WORDS, [(0.9, 3.2)])
        self.assertFalse(any(a < 1.9 < b for a, b in ctx.keep), ctx.keep)
        self.assertEqual(self.caption(ctx), "вот можно здесь вычитать.")

    def test_the_first_sound_goes_with_it(self):
        """Scribe starts a word about 50 ms after its first sound: the cut goes from the end of the word before it."""
        ctx = self.planned(self.WORDS, [(0.9, 3.2)])
        self.assertEqual(ctx.keep, [(0.9, 1.61), (2.0, 3.12)])

    def test_after_a_pause_only_the_lead_goes(self):
        words = [word("Конец.", 1.0, 1.2), word("Эээ,", 1.6, 2.0, "filler"), word("дальше.", 2.1, 2.6)]
        ctx = self.planned(words, [(0.9, 2.8)])
        self.assertEqual(ctx.keep, [(0.9, 1.32), (2.0, 2.72)])

    def test_a_listed_word_goes_as_a_hesitation_does(self):
        words = [word("можно,", 1.0, 1.3), word("м-м,", 1.35, 1.6), word("здесь.", 1.65, 2.0)]
        ctx = self.planned(words, [(0.9, 2.2)])
        self.assertEqual(ctx.keep, [(0.9, 1.31), (1.6, 2.12)])
        self.assertEqual(self.caption(ctx), "можно здесь.")

    def test_the_transcript_on_disk_is_not_touched(self):
        words = [dict(w) for w in self.WORDS]
        self.planned(words, [(0.9, 3.2)])
        self.assertEqual(words, self.WORDS)

    def test_the_report_names_what_was_cut(self):
        ctx = self.planned(self.WORDS, [(0.9, 3.2)])
        self.assertTrue(any("эээ" in c["why"] for c in ctx.report["cuts"]), ctx.report["cuts"])


class Takes(Run):
    def test_a_take_cut_from_a_clip_leaves_a_full_stop_and_its_first_sound_goes(self):
        words = [word("Собираем", 1.0, 1.4), word("систему", 1.45, 1.9), word("и", 1.95, 2.0), word("текст", 2.05, 2.4),
                 word("здесь.", 2.45, 2.8), word("Дальше", 3.0, 3.3), word("идём.", 3.35, 3.7)]
        item = {"drop": [1.95, 2.8], "said": "и текст здесь.", "why": "редактор"}
        with mock.patch("runtime.pipelines.editing.plan_editing", return_value=[item]):
            ctx = self.planned(words, [(0.9, 3.9)], editor=True)
        self.assertEqual(ctx.keep, [(0.9, 1.91), (2.8, 3.82)])
        self.assertEqual(self.caption(ctx), "Собираем систему. Дальше идём.")

    def test_the_sentence_after_a_cut_starts_with_a_capital_letter(self):
        """From the lesson's cuts: «ну, в этом» cut down to «в этом» after «все.»."""
        words = [word("Это", 1.0, 1.2), word("все.", 1.25, 1.6), word("Ну,", 1.7, 1.9), word("в", 1.95, 2.0), word("этом", 2.05, 2.4),
                 word("суть.", 2.45, 2.8)]
        item = {"drop": [1.7, 1.9], "said": "Ну,", "why": "слово-паразит"}
        with mock.patch("runtime.pipelines.editing.plan_editing", return_value=[item]):
            ctx = self.planned(words, [(0.9, 3.0)], editor=True)
        self.assertEqual(self.caption(ctx), "Это все. В этом суть.")

    def test_only_the_clip_is_captioned(self):
        words = [word("Раньше", 1.0, 1.4), word("сказал.", 1.45, 1.8), word("можно,", 10.0, 10.4), word("эээ,", 10.45, 10.8, "filler"),
                 word("здесь.", 10.85, 11.2)]
        ctx = self.planned(words, [(0.9, 2.0), (9.9, 11.4)])
        self.assertEqual(self.caption(ctx, 9.0, 12.0), "можно здесь.")


class WithoutCuts(Run):
    def test_a_word_in_the_vertical_keeps_its_comma_when_nothing_is_cut_next_to_it(self):
        words = [word("можно,", 1.0, 1.3), word("здесь.", 1.35, 1.7)]
        self.assertEqual(self.caption(self.planned(words, [(0.9, 1.9)])), "можно, здесь.")

    def test_a_name_keeps_its_own_case_after_a_sentence(self):
        words = [word("Готово.", 1.0, 1.3), word("iCloud", 1.35, 1.7), word("тут.", 1.75, 2.0)]
        self.assertEqual(self.caption(self.planned(words, [(0.9, 2.2)])), "Готово. iCloud тут.")


if __name__ == "__main__":
    unittest.main()
