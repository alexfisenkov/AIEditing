import sys
import tempfile
import unittest
from pathlib import Path

import _support

sys.path.insert(0, str(Path(_support.__file__).resolve().parent.parent / "skills" / "aiediting" / "tools"))


def said(*phrases, pause=1.0):
    """Words of the phrases, one every 0.3 s, with `pause` s between phrases."""
    out, t = [], 0.0
    for phrase in phrases:
        for w in phrase.split():
            out.append({"text": w, "start": round(t, 3), "end": round(t + 0.25, 3), "type": "word"})
            t += 0.3
        t += pause
    return out


class Slips(unittest.TestCase):
    def items(self, *phrases, **kw):
        from runtime.pipelines.retakes import find_retakes

        return find_retakes(said(*phrases, **kw))

    def one(self, *phrases, **kw):
        items = self.items(*phrases, **kw)
        self.assertEqual(len(items), 1, items)
        return items[0]

    def test_what_is_said_between_takes_goes_with_the_earlier_one(self):
        item = self.one("Под этим видео будет ссылка--", "нет, не так.",
                        "Под этим видео будет ссылка на подробную статью.")
        self.assertIn("нет, не так.", item["said"])
        self.assertAlmostEqual(item["keep"][0] - item["drop"][1], 0.05)

    def test_a_take_of_two_phrases_leaves_the_last_one_whole(self):
        a, b = "Под этим видео будет ссылка.", "В ней всё подробно написано."
        items = self.items(a, b, a, b)
        words = said(a, b, a, b)
        kept = [w["text"] for w in words if not any(t["drop"][0] <= w["start"] < t["drop"][1] for t in items)]
        self.assertEqual(" ".join(kept), a + " " + b)

    def test_real_speech_between_like_starts_is_not_taken(self):
        item = self.one("Если вы хотите настроить почту, откройте почту.",
                        "Там есть раздел с настройками для каждого ящика.",
                        "Если вы хотите настроить календарь, откройте календарь.")
        self.assertNotIn("раздел", item["said"])

    def test_a_phrase_restarted_from_its_tail(self):
        item = self.one("Которые вы нашли в интернете и хотите их,", "и хотите их адаптировать под себя.")
        self.assertEqual(item["said"], "и хотите их,")
        self.assertEqual(item["why"], "фраза начата заново")

    def test_a_restart_without_a_pause_inside_one_phrase(self):
        item = self.one("Которые вы нашли и хотите их и хотите их адаптировать.")
        self.assertEqual(item["said"], "и хотите их")

    def test_a_finished_sentence_is_no_restart(self):
        self.assertEqual(self.items("Вот так это работает.", "Это работает у всех подряд."), [])

    def test_one_repeated_word_is_emphasis_not_a_restart(self):
        self.assertEqual(self.items("Здесь все, все,", "все считал правильно."), [])
        self.assertEqual(self.items("Уже все, все, все, все, все, все здесь будет присутствовать."), [])

    def test_a_name_said_twice_is_no_restart(self):
        self.assertEqual(self.items("И отдадим его уже в Claude Code, Claude Code уже сможет помочь."), [])

    def test_a_hanging_word_is_still_found_after_a_name_said_twice(self):
        item = self.one("В Claude Code, Claude Code уже сможет нам, соответственно,", "именно работать в интеграции.")
        self.assertEqual(item["said"], "соответственно,")

    def test_an_aside_to_oneself(self):
        for text in ("Нет, без этого.", "Нет, давай перепишу весь последний абзац.", "Не так, еще раз.",
                     "Итак, диктую промпт.", "Я уже нашёл, Не-не.", "Так, нет, сейчас промпт сначала скажу.",
                     "Если что, контакт там бу-- а, не, не, дальше, вот это уже больше не надо."):
            items = self.items("Здесь обычная длинная фраза про настройки.", text, "И дальше идёт другая речь.")
            self.assertEqual([t["why"] for t in items], ["реплика в сторону"], text)
            self.assertEqual(items[0]["before"], "Здесь обычная длинная фраза про настройки.", text)
            self.assertEqual(items[0]["said"], text)

    def test_ordinary_speech_is_no_aside(self):
        for text in ("И я еще раз ему отправлю все вот эти карточки, которые были созданы.",
                     "Если сейчас вам этого делать не надо, то можно не делать.",
                     "Если что-то пошло не так, напишите мне.", "Без этого скилла ничего не заработает.",
                     "Сейчас я перепишу этот файл целиком.", "Вам больше не надо платить за это."):
            self.assertEqual(self.items(text, "И дальше идёт другая речь про настройки."), [], text)

    def test_a_short_phrase_that_breaks_off(self):
        item = self.one("А на этом все.", "Это видео-- и это видео смонтировал мне Claude Code.")
        self.assertEqual((item["said"], item["why"]), ("Это видео--", "начал и бросил"))

    def test_a_word_hanging_before_a_pause(self):
        item = self.one("Claude Code уже сможет нам, соответственно,", "именно в интеграции работать.")
        self.assertEqual(item["said"], "соответственно,")
        self.assertEqual(item["why"], "слово повисло перед паузой")

    def test_a_word_is_not_hanging_without_a_pause_or_a_comma(self):
        self.assertEqual(self.items("Откроем приложение и", "дальше смотрим настройки."), [])
        self.assertEqual(self.items("Откроем приложение, и", "дальше смотрим настройки.", pause=0.2), [])

    def test_no_words(self):
        self.assertEqual(self.items(), [])


class Plan(unittest.TestCase):
    def ctx(self, params, words, spans, answer=None):
        from runtime.pipelines.context import Context

        ctx = Context.__new__(Context)
        ctx.params, ctx.notes, ctx.src, ctx.steps = dict(params), [], "x.mp4", []
        ctx.report, ctx.loud, ctx._timed, ctx.keep = {}, None, True, list(spans)
        ctx.info = {"duration": 100.0}
        ctx._words = {"words": words}
        ctx.ask = answer or (lambda key, question, payload: (True, payload))
        return ctx

    def plan(self, params, words, spans, answer=None):
        from runtime.pipelines.cutplan import plan_cut

        ctx = self.ctx(params, words, spans, answer)
        plan_cut(ctx)
        return ctx

    def test_a_click_goes_and_the_report_says_why(self):
        ctx = self.plan({"wordless": "cut"}, said("Первая фраза.", pause=0.0), [(0.0, 1.0), (20.0, 22.0), (30.0, 30.5)])
        self.assertEqual(ctx.keep, [(0.0, 1.0)])
        self.assertIn("звук без слов", [c["why"] for c in ctx.report["cuts"]])

    def test_a_demo_with_its_own_sound_stays(self):
        spans = [(0.0, 1.0), (20.0, 30.0)]
        self.assertEqual(self.plan({"wordless": "cut"}, said("Первая фраза.", pause=0.0), spans).keep, spans)

    def test_a_loud_piece_next_to_a_word_that_lost_its_place_stays(self):
        """«настройки» sounds at 10.8–11.3, recognised at 12.0–12.5 in silence."""
        words = [{"text": "откройте", "start": 10.0, "end": 10.4, "type": "word"},
                 {"text": "настройки", "start": 12.0, "end": 12.5, "type": "word"}]
        spans = [(9.95, 10.45), (10.75, 11.35)]
        self.assertEqual(self.plan({"wordless": "cut"}, words, spans).keep, spans)

    def test_it_stays_unless_the_profile_asks(self):
        spans = [(0.0, 1.0), (20.0, 22.0)]
        self.assertEqual(self.plan({}, said("Первая фраза.", pause=0.0), spans).keep, spans)

    def test_no_words_at_all_leaves_the_cut_as_it_was(self):
        self.assertEqual(self.plan({"wordless": "cut"}, [], [(0.0, 1.0)]).keep, [(0.0, 1.0)])

    def test_the_report_names_a_slip_as_a_slip(self):
        words = said("Claude Code уже сможет нам, соответственно,", "именно в интеграции работать.")
        ctx = self.plan({"retakes": "last_good"}, words, [(0.0, 100.0)])
        self.assertIn("слово повисло перед паузой", " ".join(c["why"] for c in ctx.report["cuts"]))

    def test_an_answer_may_name_items_by_id(self):
        from runtime.pipelines.retakes import plan_retakes

        words = said("Claude Code уже сможет нам, соответственно,", "именно в интеграции работать.")
        ctx = self.ctx({}, words, [(0.0, 100.0)], lambda key, question, payload: (True, {"items": ["r1", "нет такого"]}))
        self.assertEqual([t["id"] for t in plan_retakes(ctx, words)], ["r1"])


TIMELINE = """<fcpxml><resources><asset id="logo" duration="0s"/><asset id="r" start="{origin}" duration="100s"/></resources>
<library><event><project><sequence><spine>{clips}</spine></sequence></project></event></library></fcpxml>"""
RETIME = '<timeMap><timept time="0s" value="0s"/><timept time="100s" value="107s"/></timeMap>'


class Timeline(unittest.TestCase):
    def read(self, clips, origin="0s"):
        from fcpx_timeline import read

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Info.fcpxml").write_text(TIMELINE.format(origin=origin, clips=clips), encoding="utf-8")
            return read(tmp)

    def test_retimed_clips_give_source_time(self):
        got = self.read('<asset-clip ref="r" start="10s" duration="2s">{0}</asset-clip>'
                        '<asset-clip ref="r" start="20s" duration="1s">{0}</asset-clip>'.format(RETIME))
        self.assertEqual(got["total"], 100.0)
        self.assertAlmostEqual(got["rate"], 1.07)
        self.assertAlmostEqual(got["kept"][0][0], 10.7)
        self.assertAlmostEqual(got["kept"][1][1], 22.47)

    def test_a_gap_a_title_and_a_transition_keep_nothing(self):
        got = self.read('<gap start="3600s" duration="5s"/><transition duration="1s"/><title start="0s" duration="5s"/>'
                        '<asset-clip ref="r" start="10s" duration="2s"/>')
        self.assertEqual(got["kept"], [(10.0, 12.0)])

    def test_a_logo_on_the_storyline_is_not_the_lesson(self):
        got = self.read('<asset-clip ref="logo" start="0s" duration="3s"/><asset-clip ref="r" start="10s" duration="20s"/>')
        self.assertEqual(got["kept"], [(10.0, 30.0)])
        self.assertEqual(got["total"], 100.0)

    def test_a_camera_timecode_is_taken_off(self):
        self.assertEqual(self.read('<asset-clip ref="r" start="3610s" duration="2s"/>', "3600s")["kept"], [(10.0, 12.0)])

    def test_a_compound_clip_is_an_error_not_a_guess(self):
        from fcpx_timeline import TimelineError

        with self.assertRaises(TimelineError):
            self.read('<ref-clip ref="c" start="0s" duration="5s"/><asset-clip ref="r" start="10s" duration="2s"/>')

    def test_a_retime_with_two_speeds_goes_point_by_point(self):
        steps = '<timeMap><timept time="0s" value="0s"/><timept time="10s" value="10s"/><timept time="20s" value="30s"/></timeMap>'
        self.assertAlmostEqual(self.read('<asset-clip ref="r" start="15s" duration="5s">{}</asset-clip>'.format(steps))["kept"][0][0], 20.0)

    def test_only_in_counts_what_the_other_cut_away(self):
        import cut_compare as cc

        self.assertEqual(cc.only_in([(0.0, 10.0)], [(2.0, 3.0), (5.0, 6.0)]), [(0.0, 2.0), (3.0, 5.0), (6.0, 10.0)])
        self.assertEqual(cc.only_in([(0.0, 1.0)], [(0.0, 1.0)]), [])
        self.assertEqual(cc.invert([(1.0, 2.0)], 3.0), [(0.0, 1.0), (2.0, 3.0)])

    def test_a_report_without_cuts_is_a_clear_error(self):
        import cut_compare as cc

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "отчёт.md"
            path.write_text("# Отчёт", encoding="utf-8")
            with self.assertRaises(ValueError):
                cc.report_cuts(path)


class WordTimes(unittest.TestCase):
    def test_a_tail_returns_across_the_short_breaths_of_a_dense_cut(self):
        from runtime.pipelines.word_times import repaired

        words = [{"text": "ним", "start": 2363.5, "end": 2363.9, "type": "word"},
                 {"text": "даже", "start": 2425.3, "end": 2426.3, "type": "word"},
                 {"text": "Telegram.", "start": 2429.1, "end": 2431.1, "type": "word"}]
        loud = [(2360.0, 2364.2), (2364.6, 2366.0)]
        fixed, _ = repaired({"words": words}, loud, pad=0.05)
        self.assertEqual(fixed["words"][1]["start"], 2363.9)
        self.assertEqual(fixed["words"][2]["end"], 2365.95)


if __name__ == "__main__":
    unittest.main()
