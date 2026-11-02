import unittest
from unittest import mock

import _support  # noqa: F401  (puts the skill on sys.path)


def word(text, start, end, **kw):
    return dict({"text": text, "start": start, "end": end, "type": "word"}, **kw)


class Repaired(unittest.TestCase):
    def fix(self, words, loud, **kw):
        from runtime.pipelines.word_times import repaired

        out, moved = repaired({"words": words, "language": "ru"}, loud, **kw)
        return out["words"], moved

    def test_a_word_stretched_over_the_pause_goes_back_to_its_sound(self):
        """From the lesson: «дизайн-системе.» 436.89–562.83, with noise near its middle."""
        words = [word("этой", 436.3, 436.8), word("дизайн-системе.", 436.89, 562.83), word("Что", 629.4, 629.6)]
        fixed, moved = self.fix(words, [(432.0, 437.7), (499.5, 500.0), (629.3, 640.0)])
        self.assertEqual((fixed[1]["start"], fixed[1]["end"]), (436.89, 437.7))
        self.assertEqual(moved, ["дизайн-системе. 0:07:16.9–0:09:22.8 → 0:07:16.9"])

    def test_a_stretch_ending_on_a_noise_still_goes_back(self):
        words = [word("системе.", 10.0, 90.0), word("Дальше", 90.1, 90.4)]
        fixed, _ = self.fix(words, [(9.0, 10.6), (40.0, 40.3), (89.8, 95.0)])
        self.assertEqual((fixed[0]["start"], fixed[0]["end"]), (10.0, 10.6))

    def test_a_word_stretched_backwards_goes_to_the_sound_at_its_end(self):
        words = [word("Что", 480.0, 629.6)]
        fixed, _ = self.fix(words, [(499.5, 500.0), (629.3, 640.0)])
        self.assertEqual((fixed[0]["start"], fixed[0]["end"]), (629.3, 629.6))

    def test_a_long_word_with_sound_through_all_of_it_stays(self):
        words = [word("https-адрес", 10.0, 13.5)]
        self.assertEqual(self.fix(words, [(9.0, 20.0)]), (words, []))

    def test_a_tail_placed_inside_a_later_silence_returns_to_the_sound_after_the_last_word(self):
        """From the lesson: «даже через Telegram.» is heard at 2363.9–2365.9, recognised at 2425–2431."""
        words = [word("с", 2363.3, 2363.5), word("ним", 2363.5, 2363.9), word("даже", 2425.27, 2426.35),
                 word("через", 2426.4, 2429.0), word("Telegram.", 2429.15, 2431.17), word("Под", 2431.8, 2432.0)]
        fixed, moved = self.fix(words, [(2360.0, 2366.0), (2400.0, 2400.25), (2431.7, 2440.0)])
        tail = fixed[2:5]
        self.assertEqual(tail[0]["start"], 2363.9)
        self.assertEqual(tail[-1]["end"], 2365.88)
        for a, b in zip(tail, tail[1:]):
            self.assertAlmostEqual(a["end"], b["start"], places=2)
        self.assertEqual(moved, ["даже через Telegram. 0:40:25.3 → 0:39:23.9"])

    def test_a_word_in_its_sound_is_left_alone(self):
        words = [word("Сегодня", 1.0, 1.5), word("говорим", 1.6, 2.1)]
        self.assertEqual(self.fix(words, [(0.9, 2.2)]), (words, []))

    def test_a_click_is_no_place_for_a_quiet_word(self):
        """A 10 ms click comes out of speech_spans as 0.25 s: the word stays where it is, and stays out."""
        words = [word("а", 1.0, 1.1), word("да", 50.0, 50.3)]
        fixed, moved = self.fix(words, [(0.9, 1.2), (19.88, 20.13)])
        self.assertEqual((fixed[1]["start"], fixed[1]["end"]), (50.0, 50.3))
        self.assertEqual(moved, [])

    def test_the_tail_of_the_last_word_is_no_place_for_the_next(self):
        words = [word("системе.", 9.5, 10.0), word("э-э", 10.9, 11.2)]
        self.assertEqual(self.fix(words, [(9.0, 10.25)])[1], [])

    def test_lost_words_never_get_a_whole_demonstration(self):
        words = [word("смотрите", 100.0, 100.4), word("так", 141.0, 141.4), word("Дальше", 142.5, 142.9)]
        fixed, _ = self.fix(words, [(99.0, 140.12), (142.4, 150.0)])
        self.assertEqual((fixed[1]["start"], fixed[1]["end"]), (100.4, 100.8))

    def test_words_after_a_finished_sentence_are_not_moved(self):
        """A quiet word or a recogniser's invention after a full stop: the breath before it is not its sound."""
        words = [word("системе.", 9.5, 10.0), word("да", 14.0, 14.3), word("Дальше", 20.0, 20.4)]
        self.assertEqual(self.fix(words, [(9.0, 10.72), (19.9, 21.0)]), (words, []))

    def test_a_click_under_a_word_is_not_its_sound(self):
        fixed, moved = self.fix([word("через", 19.0, 19.9)], [(19.88, 20.13)])
        self.assertEqual((fixed[0]["start"], fixed[0]["end"]), (19.0, 19.9))
        self.assertEqual(moved, [])

    def test_a_click_inside_a_tail_does_not_break_it(self):
        words = [word("ним", 2363.5, 2363.9), word("даже", 2399.0, 2400.1), word("через", 2400.2, 2401.0),
                 word("Telegram.", 2401.1, 2403.0)]
        fixed, _ = self.fix(words, [(2360.0, 2366.0), (2400.0, 2400.25)])
        self.assertEqual(fixed[1]["start"], 2363.9)
        self.assertEqual(fixed[3]["end"], 2365.88)

    def test_a_stretch_with_both_ends_in_silence_goes_to_its_first_sound(self):
        fixed, _ = self.fix([word("системе.", 10.0, 60.0)], [(10.2, 11.0), (59.0, 59.9)])
        self.assertEqual((fixed[0]["start"], fixed[0]["end"]), (10.2, 11.0))

    def test_a_middle_in_a_pause_moves_to_the_part_that_sounds(self):
        fixed, moved = self.fix([word("да", 10.0, 11.0)], [(9.0, 10.2)])
        self.assertEqual((fixed[0]["start"], fixed[0]["end"]), (10.0, 10.2))
        self.assertEqual(moved, ["да 0:00:10.0–0:00:11.0 → 0:00:10.0"])

    def test_a_hesitation_keeps_its_times(self):
        words = [word("смотрите", 100.0, 100.4), word("э-э", 141.0, 141.4), word("э-э", 150.0, 155.0)]
        fix = lambda w: w["text"] == "э-э"  # noqa: E731
        self.assertEqual(self.fix(words, [(99.0, 160.0)], fixed=fix)[0], words)
        self.assertEqual(self.fix(words, [(99.0, 140.12)], fixed=fix)[0], words)

    def test_spacing_and_the_rest_of_the_transcript_stay(self):
        from runtime.pipelines.word_times import repaired

        source = {"words": [word(" ", 1.0, 900.0, type="spacing"), word("да", 900.0, 900.5)], "language": "ru"}
        out, moved = repaired(source, [(899.9, 901.0)])
        self.assertEqual(out["language"], "ru")
        self.assertEqual(out["words"], source["words"])
        self.assertEqual(moved, [])

    def test_the_source_is_not_changed(self):
        words = [word("дизайн", 1.0, 200.0)]
        self.fix(words, [(0.9, 2.0)])
        self.assertEqual(words[0]["end"], 200.0)

    def test_no_words_no_trouble(self):
        from runtime.pipelines.word_times import repaired

        self.assertEqual(repaired({"words": []}, [(0.0, 1.0)])[1], [])
        self.assertEqual(repaired(None, [(0.0, 1.0)])[0]["words"], [])


class InTheRun(unittest.TestCase):
    """Through Context and plan_speech, as a run goes."""

    def context(self, params, words):
        from runtime.pipelines.context import Context

        ctx = Context.__new__(Context)
        ctx.params, ctx.notes, ctx.src, ctx.keep = dict(params), [], "x.mp4", [(0.0, 100.0)]
        ctx.steps, ctx.report, ctx.loud, ctx._timed = [], {}, None, False
        ctx.info = {"duration": 100.0}
        ctx._words = {"words": words}
        return ctx

    def speech(self, ctx, spans):
        from runtime.pipelines.cutplan import plan_speech

        with mock.patch("runtime.media.speech_spans", return_value=spans):
            plan_speech(ctx)

    def test_the_subtitles_keep_the_tail_after_the_cut(self):
        from runtime.pipelines.kept import kept_words

        spans = [(0.0, 3.0), (60.0, 61.0)]
        ctx = self.context({}, [word("Первое", 0.2, 2.0), word("слово.", 2.1, 50.0), word("Дальше.", 60.1, 60.9)])
        self.assertEqual([w["text"] for w in kept_words(ctx._words["words"], spans)], ["Первое", "Дальше."])
        self.speech(ctx, spans)
        self.assertEqual([w["text"] for w in kept_words(ctx.transcript()["words"], spans)],
                         ["Первое", "слово.", "Дальше."])
        self.assertEqual(len(ctx.notes), 1)

    def test_a_listed_hesitation_is_cut_where_it_was_said(self):
        words = [word("смотрите", 10.0, 10.4), word("э-э", 12.0, 12.4), word("Дальше", 20.0, 20.4)]
        ctx = self.context({"fillers_cut": ["э-э"]}, words)
        self.speech(ctx, [(9.0, 11.0), (19.9, 21.0)])
        self.assertEqual(ctx.transcript()["words"], words)

    def test_a_format_cut_by_words_keeps_recognised_times(self):
        words = [word("тихое", 1.0, 1.5), word("слово", 5.0, 5.4)]
        ctx = self.context({"word_gap": 0.25}, words)
        self.speech(ctx, [(0.9, 1.2), (5.0, 5.4)])
        self.assertIsNone(ctx.loud)
        self.assertEqual(ctx.transcript()["words"], words)

    def test_the_times_are_checked_once_and_the_cache_stays_raw(self):
        words = [word("слово.", 2.1, 50.0)]
        ctx = self.context({}, words)
        ctx.loud = [(0.0, 3.0)]
        first = ctx.transcript()
        self.assertIs(ctx.transcript(), first)
        self.assertEqual(first["words"][0]["end"], 3.0)
        self.assertEqual(words[0]["end"], 50.0)


if __name__ == "__main__":
    unittest.main()
