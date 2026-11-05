"""Corrections of subtitles work on words: exact, independent of where a subtitle breaks, and the same in both files."""
import json
import re
import sys
import types
import unittest

from _support import SKILL, TempDirCase

if str(SKILL / "tools") not in sys.path:
    sys.path.insert(0, str(SKILL / "tools"))


def words(text, step=0.5):
    return [{"text": w, "start": i * step, "end": i * step + 0.4, "type": "word"} for i, w in enumerate(text.split())]


def said(tokens):
    return " ".join(t["text"] for t in tokens)


class Corrected(unittest.TestCase):
    def run_it(self, text, **corrections):
        from runtime.media.srt_fixes import corrected

        return corrected(words(text), corrections)

    def test_replace_is_whole_words_and_their_case(self):
        tokens, changed, missed = self.run_it("Код и код, кодекс и Код", replace={"код": "скрипт"})
        self.assertEqual(said(tokens), "Код и скрипт, кодекс и Код")
        self.assertEqual(len(changed), 1)
        self.assertTrue(missed[0]["soft"], "the same word in another case is named")

    def test_a_phrase_that_a_subtitle_break_would_split_is_still_found(self):
        tokens, _, missed = self.run_it(" ".join(["слово"] * 12) + " в проекте " + " ".join(["слово"] * 12),
                                        replace={"в проекте": "в настроенном проекте"})
        self.assertIn("в настроенном проекте", said(tokens))
        self.assertEqual(missed, [])

    def test_at_changes_one_place_and_leaves_the_others(self):
        tokens, _, _ = self.run_it("да нет да нет да нет", at=[{"t": 1.1, "from": "да", "to": "ага"}])
        self.assertEqual(said(tokens), "да нет ага нет да нет")

    def test_an_empty_to_takes_a_made_up_repeat_out_and_keeps_the_stop(self):
        tokens, _, _ = self.run_it("сделали так так.", at=[{"t": 1.0, "from": "так", "to": ""}])
        self.assertEqual(said(tokens), "сделали так.")

    def test_the_punctuation_of_the_found_words_stays(self):
        tokens, _, _ = self.run_it("пишем клод, потом", replace={"клод": "Claude"})
        self.assertEqual(said(tokens), "пишем Claude, потом")

    def test_new_words_share_the_time_of_the_old(self):
        tokens, _, _ = self.run_it("раз два три", replace={"два": "два с половиной"})
        self.assertEqual(said(tokens), "раз два с половиной три")
        self.assertAlmostEqual(tokens[1]["start"], 0.5)
        self.assertAlmostEqual(tokens[3]["end"], 0.9)
        self.assertLess(tokens[1]["end"], tokens[3]["end"])

    def test_what_found_no_words_is_named_with_a_hint_about_the_case(self):
        _, _, missed = self.run_it("Код работает", replace={"код": "скрипт", "нет такого": "ничего"})
        by_word = {m["from"]: m["why"] for m in missed}
        self.assertIn("«Код»", by_word["код"])
        self.assertEqual(by_word["нет такого"], "")

    def test_at_too_far_from_its_second_does_not_change_another_place(self):
        tokens, _, missed = self.run_it("да " + "нет " * 40, at=[{"t": 19.0, "from": "да", "to": "ага"}])
        self.assertTrue(said(tokens).startswith("да "))
        self.assertIn("ближайшее", missed[0]["why"])


class WhatYouSee(unittest.TestCase):
    def test_a_correction_matches_the_text_after_the_glossary(self):
        from runtime.media.srt import final_tokens

        tokens = final_tokens(words("клод клод работает"), {"клод": "Claude"}, {"at": [{"t": 0.5, "from": "Claude", "to": ""}]})
        self.assertEqual(said(tokens), "Claude работает")

    def test_quotes_around_a_word_stay_in_both_ways(self):
        from runtime.media.srt_fixes import corrected, glossed

        tokens, _, _ = corrected(words("пишем «клод» и (код)"), {"replace": {"клод": "Claude", "код": "скрипт"}})
        self.assertEqual(said(tokens), "пишем «Claude» и (скрипт)")
        tokens, _ = glossed(words("пишем «клод код» и клод-код"), {"клод код": "Claude Code", "клод": "Claude"})
        self.assertEqual(said(tokens), "пишем «Claude Code» и Claude-код")

    def test_what_a_correction_wrote_is_not_corrected_again(self):
        from runtime.media.srt_fixes import corrected

        tokens, _, _ = corrected(words("икс игрек"), {"replace": {"икс": "игрек", "игрек": "икс"}})
        self.assertEqual(said(tokens), "игрек икс")

    def test_the_same_words_in_another_case_are_named_though_the_rest_applied(self):
        from runtime.media.srt_fixes import corrected

        tokens, _, missed = corrected(words("Клод и клод"), {"replace": {"клод": "Claude"}})
        self.assertEqual(said(tokens), "Клод и Claude")
        self.assertTrue(missed[0]["soft"])

    def test_a_sentence_goes_on_with_a_capital_after_its_first_word_is_taken_out(self):
        from runtime.media.srt_fixes import corrected

        tokens, _, _ = corrected(words("Так так работает."), {"at": [{"t": 0.0, "from": "Так", "to": ""}]})
        self.assertEqual(said(tokens), "Так работает.")

    def test_a_wrong_shape_is_refused_before_a_render(self):
        from runtime.media.srt_fixes import checked

        for bad in ({"at": [{"t": "12:34", "from": "а", "to": "б"}]}, {"at": [{"from": "а"}]}, {"at": {"t": 1}}, {"replace": ["а"]},
                    {"at": [{"t": True, "from": "а"}]}, {"at": [{"t": 1, "from": " "}]}):
            with self.assertRaises(ValueError):
                checked(bad)
        self.assertEqual(checked({"at": [{"t": 1, "from": "а", "to": None}]})["at"][0]["to"], "")


class TheFile(TempDirCase):
    def test_a_correction_goes_into_the_srt_whatever_the_breaks(self):
        from runtime.media import write_srt

        out = self.tmp / "a.srt"
        phrase = "первая часть длинной фразы которая не влезает в одну строку субтитра никак"
        fixes = write_srt({"words": words(phrase)}, out, {}, {"replace": {"влезает в одну": "помещается в одну"}})
        body = " ".join(line for line in out.read_text(encoding="utf-8").splitlines() if re.search("[а-я]", line))
        self.assertIn("помещается в одну", body)
        self.assertEqual(fixes[0]["from"], "влезает в одну")
        self.assertGreaterEqual(fixes[0]["index"], 1)

    def test_a_glossary_phrase_goes_before_its_first_word(self):
        from runtime.media import write_srt

        out = self.tmp / "a.srt"
        write_srt({"words": words("открываем клод код сейчас")}, out, {"клод": "Claude", "клод код": "Claude Code"})
        self.assertIn("Claude Code", out.read_text(encoding="utf-8"))

    def test_the_words_file_says_what_the_srt_says(self):
        from runtime.media import write_srt
        from runtime.pipelines.subtitles import write_words_file

        glossary, corrections = {"клод код": "Claude Code"}, {"replace": {"отдельно": "вместе"}}
        source = words("пишем в клод код отдельно.")
        write_srt({"words": source}, self.tmp / "a.srt", glossary, corrections)
        write_words_file(self.tmp / "слова.txt", source, glossary, corrections)
        in_file = " ".join(r[8:] for r in (self.tmp / "слова.txt").read_text(encoding="utf-8").splitlines())
        in_srt = " ".join(line for line in (self.tmp / "a.srt").read_text(encoding="utf-8").splitlines() if re.search("[а-я]", line))
        self.assertEqual(in_file, in_srt)
        self.assertIn("Claude Code вместе.", in_file)


class Rewrite(TempDirCase):
    def test_corrections_come_again_with_no_render_and_name_what_missed(self):
        from runtime.pipelines import subtitles
        from runtime.pipelines.words import KEPT

        issue = self.tmp / "выпуск"
        (issue / KEPT).mkdir(parents=True)
        (issue / KEPT / subtitles.FINAL_WORDS).write_text(
            json.dumps({"видео.srt": words("пишем клод отдельно")}, ensure_ascii=False), encoding="utf-8")
        (issue / subtitles.WORDS_FILE).write_text("старое\n", encoding="utf-8")
        done = subtitles.rewrite(issue, {"клод": "Claude"}, {"replace": {"отдельно": "вместе", "нет": "да"}})
        self.assertIn("Claude вместе", (issue / "видео.srt").read_text(encoding="utf-8"))
        self.assertEqual((issue / subtitles.WORDS_FILE).read_text(encoding="utf-8").splitlines()[-1][8:], "вместе")
        self.assertEqual([m["from"] for m in done["missed"]], ["нет"])

    def test_a_folder_from_an_earlier_version_is_named(self):
        from runtime.pipelines import subtitles

        with self.assertRaises(FileNotFoundError):
            subtitles.rewrite(self.tmp, {}, {})

    def test_a_correction_that_found_words_in_one_clip_is_not_lost(self):
        from runtime.pipelines import subtitles
        from runtime.pipelines.words import KEPT

        issue = self.tmp / "выпуск"
        (issue / KEPT).mkdir(parents=True)
        (issue / KEPT / subtitles.FINAL_WORDS).write_text(json.dumps({"а.srt": words("есть слово"), "б.srt": words("другой текст")}, ensure_ascii=False), encoding="utf-8")
        done = subtitles.rewrite(issue, {}, {"replace": {"слово": "дело"}})
        self.assertEqual(done["missed"], [])
        self.assertFalse(done["words_file"])

    def test_a_run_remembers_only_the_last_hearing(self):
        from runtime.pipelines import subtitles

        notes = []
        ctx = types.SimpleNamespace(outdir=self.tmp, srt_corrections={"replace": {"нет": "да"}}, note=notes.append,
                                    final_words={"а.srt": words("есть слова")})
        subtitles.keep_final_words(ctx)
        self.assertEqual(len(notes), 1)
        self.assertIn("не применилась", notes[0])


class TheHearing(unittest.TestCase):
    def test_a_video_with_cuts_is_heard_before_the_speed_up_and_scaled(self):
        from pathlib import Path
        from unittest import mock
        from runtime.pipelines import graphics

        heard = {"words": [{"start": 10.7, "end": 11.77, "text": "слово", "type": "word"}]}
        ctx = types.SimpleNamespace(profile={"asr": {"provider": "whispercpp"}}, keep=[(0, 5), (9, 20)],
                                    p=lambda name, d=None: 1.07 if name == "speed" else d, report={"outputs": [{"video": "/готово.mp4"}]},
                                    has=lambda s: False, srt_glossary={}, before_speed=Path("/до-скорости.mp4"),
                                    transcript=lambda: {"words": []})
        with mock.patch("runtime.pipelines.words.recognise", return_value=heard) as hear, \
                mock.patch("runtime.media.probe", return_value={"duration": 15.0}):
            words_ = graphics._finished_words(ctx)
        self.assertEqual(hear.call_args[1]["media"], Path("/до-скорости.mp4"))
        self.assertAlmostEqual(words_[0]["start"], 10.0, delta=0.01)

    def test_a_whole_video_is_not_heard_again_at_its_new_speed(self):
        from unittest import mock
        from runtime.pipelines import graphics

        first = [{"start": 10.7, "end": 11.77, "text": "слово", "type": "word"}]
        ctx = types.SimpleNamespace(profile={"asr": {"provider": "whispercpp"}}, keep=[(0, 20)],
                                    p=lambda name, d=None: 1.07 if name == "speed" else d, report={"outputs": []},
                                    transcript=lambda: {"words": first})
        with mock.patch("runtime.pipelines.words.recognise") as hear:
            words_ = graphics._finished_words(ctx)
        hear.assert_not_called()
        self.assertAlmostEqual(words_[0]["start"], 10.0, delta=0.01)


if __name__ == "__main__":
    unittest.main()
