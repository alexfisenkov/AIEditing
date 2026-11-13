"""The `broll` step's plan: frames of the person's library under the sense of phrases, by the rules (no ffmpeg needed)."""
import os
import types
import unittest
from unittest import mock

import _support  # noqa: F401  (puts the skill on sys.path)
from _support import TempDirCase
from runtime.library import inventory, paths, rules
from runtime.library.stock import StockError
from runtime.pipelines.broll import plan_broll

SEA = "Летом мы поехали на море и купались каждый день."          # ten words
SETTINGS = "Потом открываем настройки браузера и смотрим новые вкладки."  # nothing of it in the library


def speech(*phrases):
    """Words 0.4 s each from (text, start): the last word of a text ends the phrase."""
    words = []
    for text, start in phrases:
        for i, w in enumerate(text.split()):
            words.append({"text": w, "start": round(start + i * 0.4, 3), "end": round(start + i * 0.4 + 0.35, 3),
                          "type": "word"})
    return words


class Ctx:
    """What the planner uses of a run: params, words, keep, answers by key, notes, decisions."""

    def __init__(self, words, broll=True, keep=None, info=None, auto=False):
        self.params = {"broll": broll}
        self.keep = keep or [(0.0, 200.0)]
        self.info = info or {"width": 1920, "height": 1080, "rotation": 0, "duration": 200.0}
        self.profile = {"format": "урок"}
        self.pieces, self.notes, self.decisions, self.broll, self.shoot_list, self.asked = None, [], [], [], [], []
        self.approve = types.SimpleNamespace(auto=auto)
        self.words, self.edit, self.answer = words, None, True

    def p(self, name, default=None):
        value = self.params.get(name)
        return default if value is None else value

    def transcript(self):
        return {"words": self.words}

    def note(self, text):
        if text not in self.notes:
            self.notes.append(text)

    def ask(self, key, question, payload):
        self.asked.append((key, payload))
        if self.edit:
            self.edit(payload)
        self.decisions.append({"key": key, "question": question, "ok": self.answer})
        return self.answer, payload


class Library(TempDirCase):
    def setUp(self):
        super().setUp()
        self.lib = paths.make_layout(self.tmp / "библиотека")
        env = mock.patch.dict(os.environ, {"AIEDITING_LIBRARY": str(self.lib)})
        env.start()
        self.addCleanup(env.stop)

    def add(self, name, **fields):
        """A row of the inventory and an (empty) file for it; a clip of the sea by default."""
        row = {"f": "футажи/" + name, "type": "видео", "orient": "гор", "dur": 20.0, "best": [[5.0, 12.0]],
               "what": "море", "tags": ["море", "пляж"], "phrases": ["поехали на море"], "who": [], "date": "2021-07-01"}
        row.update(fields)
        (self.lib / row["f"]).parent.mkdir(parents=True, exist_ok=True)
        (self.lib / row["f"]).write_bytes(b"x")
        inventory.describe(self.lib, "футажи", [row])
        return row

    def decoy(self):
        """Something usable that fits none of the phrases: the library is in use, so a missed place is a place to shoot."""
        return self.add("горы.mp4", what="горы", tags=["горы"], phrases=["в горах"])


class Quiet(Library):
    def test_off_or_without_a_library_it_does_nothing_and_asks_nothing(self):
        self.add("море.mp4")
        for broll in (None, False):
            ctx = Ctx(speech((SEA, 10.0)), broll=broll)
            plan_broll(ctx)
            self.assertEqual((ctx.broll, ctx.shoot_list, ctx.asked, ctx.notes), ([], [], [], []))
        with mock.patch.dict(os.environ, {"AIEDITING_LIBRARY": str(self.tmp / "нет такой")}):
            ctx = Ctx(speech((SEA, 10.0)))
            plan_broll(ctx)
        self.assertEqual((ctx.broll, ctx.shoot_list, ctx.asked, ctx.notes), ([], [], [], []))

    def test_a_library_without_a_single_usable_frame_does_nothing(self):
        for ctx in (Ctx(speech((SEA, 10.0))),):
            plan_broll(ctx)
            self.assertEqual((ctx.broll, ctx.shoot_list, ctx.asked), ([], [], []))
        self.add("вертикаль.mp4", orient="верт")
        self.add("коротко.mp4", dur=2.0, best=[])
        ctx = Ctx(speech((SEA, 10.0)))
        plan_broll(ctx)
        self.assertEqual((ctx.broll, ctx.shoot_list, ctx.asked), ([], [], []))

    def test_a_vertical_picture_gets_no_horizontal_inserts(self):
        self.add("море.mp4")
        ctx = Ctx(speech((SEA, 10.0)), info={"width": 1080, "height": 1920, "rotation": 0, "duration": 200.0})
        plan_broll(ctx)
        self.assertEqual((ctx.broll, ctx.asked), ([], []))
        ctx = Ctx(speech((SEA, 10.0)), info={"width": 1920, "height": 1080, "rotation": 90, "duration": 200.0})
        plan_broll(ctx)  # a phone clip stored sideways is vertical as it is shown
        self.assertEqual((ctx.broll, ctx.asked), ([], []))


class Picking(Library):
    def test_a_frame_for_the_sense_of_a_phrase_with_its_best_stretch_and_the_people_on_it(self):
        self.add("море.mp4", who=["Аня"])
        self.decoy()
        ctx = Ctx(speech((SEA, 10.0)))
        plan_broll(ctx)
        self.assertEqual(len(ctx.broll), 1)
        item = ctx.broll[0]
        self.assertEqual((item["kind"], item["from"], item["who"]), ("video", 5.0, ["Аня"]))
        self.assertEqual(item["phrase"], SEA)
        self.assertTrue(item["file"].endswith("море.mp4"))
        self.assertTrue(os.path.isabs(item["file"]))
        self.assertAlmostEqual(item["start"], 10.0, places=2)
        self.assertGreaterEqual(item["end"] - item["start"], 3.0)
        self.assertLessEqual(item["end"] - item["start"], 6.0)
        self.assertEqual(ctx.shoot_list, [])

    def test_the_question_carries_time_phrase_file_source_and_people(self):
        self.add("море.mp4", who=["Аня"], where="Крым")
        self.decoy()
        ctx = Ctx(speech((SEA, 10.0)))
        rules.add_rule(self.lib, "Море только днём")
        plan_broll(ctx)
        key, payload = ctx.asked[0]
        self.assertEqual(key, "broll")
        row = payload["rows"][0]
        for field in ("start", "end", "phrase", "file", "kind", "who", "from"):
            self.assertIn(field, row)
        self.assertEqual((row["file"], row["who"], row["phrase"]), ("футажи/море.mp4", ["Аня"], SEA))
        self.assertIn("Море только днём", payload["rules"])

    def test_a_photo_is_a_still_with_no_stretch_to_choose(self):
        self.add("закат.jpg", type="фото", dur=None, best=[], what="море", tags=["море"])
        self.decoy()
        ctx = Ctx(speech((SEA, 10.0)))
        plan_broll(ctx)
        self.assertEqual((ctx.broll[0]["kind"], ctx.broll[0]["from"]), ("photo", 0.0))

    def test_every_insert_is_three_to_six_seconds_and_a_short_phrase_gets_three(self):
        self.add("море.mp4")
        self.decoy()
        ctx = Ctx(speech(("На море.", 10.0), (SEA, 60.0)))
        plan_broll(ctx)
        self.assertEqual(len(ctx.broll), 2)
        for item in ctx.broll:
            self.assertTrue(3.0 - 1e-6 <= item["end"] - item["start"] <= 6.0 + 1e-6)

    def test_the_never_list_and_never_rows_are_left_out(self):
        self.add("море-никогда.mp4", never=True)
        self.add("море-аня.mp4", who=["Аня Петрова"])
        self.decoy()
        rules.forbid(self.lib, "Аня Петрова")
        ctx = Ctx(speech((SEA, 10.0)))
        plan_broll(ctx)
        self.assertEqual(ctx.broll, [])
        self.assertEqual(len(ctx.shoot_list), 1, "nothing may stand there, so the place is one to shoot")

    def test_a_vertical_frame_and_a_clip_under_three_seconds_are_not_taken(self):
        self.add("море-верт.mp4", orient="верт")
        self.add("море-коротко.mp4", dur=2.5, best=[])
        self.decoy()
        ctx = Ctx(speech((SEA, 10.0)))
        plan_broll(ctx)
        self.assertEqual(ctx.broll, [])
        self.assertEqual(len(ctx.shoot_list), 1)

    def test_a_year_in_the_phrase_brings_that_year_first(self):
        self.add("море-2021.mp4", date="2021-07-01")
        self.add("море-2019.mp4", date="2019-07-01")
        self.decoy()
        ctx = Ctx(speech(("В 2019 году мы поехали на море и купались каждый день.", 10.0)))
        plan_broll(ctx)
        self.assertTrue(ctx.broll[0]["file"].endswith("море-2019.mp4"))

    def test_a_clip_of_a_log_profile_is_named_in_the_notes(self):
        self.add("море-лог.mp4", log=True)
        self.decoy()
        ctx = Ctx(speech((SEA, 10.0)))
        plan_broll(ctx)
        self.assertTrue(any("лог" in n.lower() for n in ctx.notes), ctx.notes)


class Seams(Library):
    def setUp(self):
        super().setUp()
        self.add("море.mp4")
        self.decoy()

    def test_a_start_two_seconds_after_a_cut_is_refused(self):
        ctx = Ctx(speech((SEA, 10.0)), keep=[(0.0, 5.0), (8.0, 200.0)])  # the phrase lands 2 s after the cut
        plan_broll(ctx)
        self.assertEqual((ctx.broll, ctx.shoot_list), ([], []))

    def test_a_start_on_a_cut_is_taken_and_one_three_seconds_clear_too(self):
        ctx = Ctx(speech((SEA, 10.0)), keep=[(0.0, 10.0), (20.0, 200.0)])
        plan_broll(ctx)
        self.assertEqual(len(ctx.broll), 1)
        ctx = Ctx(speech((SEA, 13.5)), keep=[(0.0, 10.0), (20.0, 200.0)])  # source 13.5 is cut away: no frame there
        plan_broll(ctx)
        self.assertEqual(ctx.broll, [])
        ctx = Ctx(speech((SEA, 24.0)), keep=[(0.0, 10.0), (20.0, 200.0)])  # lands at 14 s of the cut video
        plan_broll(ctx)
        self.assertEqual(len(ctx.broll), 1)


class Runs(Library):
    def test_never_more_than_three_in_a_row_and_a_face_after_them(self):
        self.add("море.mp4")
        self.decoy()
        ctx = Ctx(speech(*[(SEA, 4.5 * i) for i in range(5)]), broll={"every": 1.0, "max_run": 3})
        plan_broll(ctx)
        self.assertEqual([round(i["start"], 1) for i in ctx.broll], [0.0, 4.5, 9.0, 18.0])

    def test_inserts_keep_the_spacing_the_person_chose(self):
        self.add("море.mp4")
        self.decoy()
        phrases = [(SEA, 4.5 * i) for i in range(5)]
        ctx = Ctx(speech(*phrases), broll={"every": 12.0})
        plan_broll(ctx)
        starts = [i["start"] for i in ctx.broll]
        self.assertTrue(all(b - a >= 12.0 - 1e-6 for a, b in zip(starts, starts[1:])), starts)


class Answers(Library):
    def setUp(self):
        super().setUp()
        self.add("море.mp4")
        self.add("море-2.mp4")
        self.decoy()
        self.words = speech((SEA, 10.0), (SEA, 40.0))

    def test_no_on_a_row_takes_it_out(self):
        ctx = Ctx(self.words, broll={"every": 5.0})

        def refuse(payload):
            payload["rows"][0]["ok"] = False

        ctx.edit = refuse
        plan_broll(ctx)
        self.assertEqual(len(ctx.broll), 1)
        self.assertAlmostEqual(ctx.broll[0]["start"], 40.0, places=1)

    def test_a_row_the_person_removed_is_not_laid(self):
        ctx = Ctx(self.words, broll={"every": 5.0})
        ctx.edit = lambda payload: payload["rows"].pop(1)
        plan_broll(ctx)
        self.assertEqual([round(i["start"]) for i in ctx.broll], [10])

    def test_refusing_the_whole_question_lays_nothing(self):
        ctx = Ctx(self.words, broll={"every": 5.0})
        ctx.answer = False
        plan_broll(ctx)
        self.assertEqual((ctx.broll, ctx.shoot_list), ([], []))

    def test_another_frame_the_agent_names_is_laid_unless_it_is_forbidden(self):
        self.add("море-3.mp4", who=["Боря"], best=[[1.0, 9.0]])
        rules.forbid(self.lib, "Боря")
        ctx = Ctx(self.words, broll={"every": 5.0})

        def swap(payload):
            payload["rows"][0]["file"] = "футажи/море-2.mp4"
            payload["rows"][1]["file"] = "футажи/море-3.mp4"

        ctx.edit = swap
        plan_broll(ctx)
        self.assertEqual([i["file"].rsplit("/", 1)[-1] for i in ctx.broll], ["море-2.mp4"])
        self.assertTrue(any("Боря" in n or "нельзя" in n for n in ctx.notes), ctx.notes)

    def test_without_questions_the_inserts_are_laid_as_proposed_and_the_decision_is_kept(self):
        ctx = Ctx(self.words, broll={"every": 5.0}, auto=True)
        plan_broll(ctx)
        self.assertEqual(ctx.asked, [])
        self.assertEqual(len(ctx.broll), 2)
        self.assertEqual([(d["key"], d["ok"]) for d in ctx.decisions], [("broll", True)])


class ShootList(Library):
    def setUp(self):
        super().setUp()
        self.add("море.mp4")
        self.decoy()

    def test_a_place_without_a_frame_goes_to_the_shoot_list_with_what_to_shoot(self):
        ctx = Ctx(speech((SEA, 10.0), (SETTINGS, 60.0)))
        plan_broll(ctx)
        self.assertEqual(len(ctx.broll), 1)
        self.assertEqual(len(ctx.shoot_list), 1)
        row = ctx.shoot_list[0]
        self.assertEqual(row["phrase"], SETTINGS)
        self.assertAlmostEqual(row["start"], 60.0, places=1)
        self.assertTrue(row["what"])
        self.assertTrue(3 <= row["dur"] <= 6)
        self.assertEqual(row["orient"], "горизонтальный")

    def test_the_text_of_what_to_shoot_is_the_persons_and_no_removes_the_row(self):
        ctx = Ctx(speech((SETTINGS, 60.0), (SETTINGS, 100.0)), broll={"every": 5.0})

        def edit(payload):
            payload["rows"][0]["want"] = "Экран браузера, вкладка настроек"
            payload["rows"][1]["ok"] = False

        ctx.edit = edit
        plan_broll(ctx)
        self.assertEqual([r["what"] for r in ctx.shoot_list], ["Экран браузера, вкладка настроек"])

    def test_no_more_than_a_handful_of_places_are_asked_for_and_short_phrases_are_not_places(self):
        texts = [("Потом открываем настройки браузера и смотрим вкладки номер {}.".format(n), 20.0 * n)
                 for n in range(1, 20)]
        ctx = Ctx(speech(*texts, ("Ну да.", 400.0)), broll={"every": 5.0})
        plan_broll(ctx)
        self.assertTrue(0 < len(ctx.shoot_list) <= 8)
        self.assertNotIn("Ну да.", [r["phrase"] for r in ctx.shoot_list])


class Stock(Library):
    HIT = {"provider": "pexels", "id": "9", "url": "https://example.test/9", "width": 1920, "height": 1080,
           "dur": 8.0, "link": "https://example.test/9.mp4", "query": "настройки браузера"}

    def setUp(self):
        super().setUp()
        self.add("море.mp4")
        self.decoy()
        self.words = speech((SETTINGS, 60.0))

    def fake_download(self, hit, library):
        row = dict(inventory.ROW, f="стоки/сток-1.mp4", kind="стоки", type="видео", orient="гор", dur=8.0,
                   source="pexels https://example.test/9")
        (self.lib / row["f"]).parent.mkdir(parents=True, exist_ok=True)
        (self.lib / row["f"]).write_bytes(b"x")
        return row

    def test_stock_fills_a_place_when_the_person_allowed_it_and_is_fetched_after_the_approval(self):
        ctx = Ctx(self.words, broll={"stock": True})
        with mock.patch("runtime.library.stock.search", return_value=[self.HIT]) as search, \
                mock.patch("runtime.library.stock.download", side_effect=self.fake_download) as download:
            plan_broll(ctx)
        self.assertEqual(search.call_args[0][1], "pexels")
        self.assertEqual(download.call_count, 1)
        self.assertEqual((ctx.broll[0]["kind"], ctx.shoot_list), ("stock", []))
        self.assertTrue(ctx.broll[0]["file"].endswith("сток-1.mp4"))
        shown = ctx.asked[0][1]["rows"][0]
        self.assertEqual(shown["kind"], "stock")
        self.assertNotIn("example.test", str(shown), "no link to the service in what the person reads")

    def test_a_stock_the_person_refused_is_not_downloaded(self):
        ctx = Ctx(self.words, broll={"stock": True})
        ctx.edit = lambda payload: payload["rows"][0].update(ok=False)
        with mock.patch("runtime.library.stock.search", return_value=[self.HIT]), \
                mock.patch("runtime.library.stock.download", side_effect=self.fake_download) as download:
            plan_broll(ctx)
        self.assertEqual((download.call_count, ctx.broll, ctx.shoot_list), (0, [], []))

    def test_stock_is_not_asked_for_unless_the_person_allowed_it(self):
        ctx = Ctx(self.words, broll=True)
        with mock.patch("runtime.library.stock.search") as search:
            plan_broll(ctx)
        search.assert_not_called()
        self.assertEqual(len(ctx.shoot_list), 1)

    def test_without_a_key_it_is_one_clear_phrase_and_the_place_is_left_to_shoot(self):
        ctx = Ctx(speech((SETTINGS, 60.0), (SETTINGS, 100.0)), broll={"stock": True, "every": 5.0})
        err = StockError("Не найден ключ: переменная PEXELS_API_KEY не задана.")
        with mock.patch("runtime.library.stock.search", side_effect=err) as search:
            plan_broll(ctx)
        self.assertEqual(len([n for n in ctx.notes if "PEXELS_API_KEY" in n]), 1)
        self.assertEqual(len(ctx.shoot_list), 2)
        self.assertLessEqual(search.call_count, 2, "a service without a key is not asked again and again")

    def test_a_failed_download_returns_the_place_to_the_shoot_list(self):
        ctx = Ctx(self.words, broll={"stock": True})
        with mock.patch("runtime.library.stock.search", return_value=[self.HIT]), \
                mock.patch("runtime.library.stock.download", side_effect=StockError("Нет связи")):
            plan_broll(ctx)
        self.assertEqual((ctx.broll, len(ctx.shoot_list)), ([], 1))

    def test_stock_works_with_a_library_that_has_no_frames_yet(self):
        os.remove(str(self.lib / "футажи" / "море.mp4"))
        os.remove(str(self.lib / "футажи" / "горы.mp4"))
        ctx = Ctx(self.words, broll={"stock": True})
        with mock.patch("runtime.library.stock.search", return_value=[self.HIT]), \
                mock.patch("runtime.library.stock.download", side_effect=self.fake_download):
            plan_broll(ctx)
        self.assertEqual(len(ctx.broll), 1)


if __name__ == "__main__":
    unittest.main()
