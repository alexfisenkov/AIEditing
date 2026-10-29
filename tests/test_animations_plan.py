"""Animated inserts are planned by speech: files/steps/lists/numbers, one per `every`, never on a chapter
plate, and an insert takes a card's place (no HyperFrames or ffmpeg needed)."""
import unittest
from unittest import mock

import _support  # noqa: F401  (puts the skill on sys.path)
from runtime.pipelines.anim_slots import every
from runtime.pipelines.animations import plan_animations
from runtime.pipelines.cards import plan_cards
from runtime.pipelines.chapters import plan_chapters
from runtime.pipelines.moments import detect
from runtime.render.design import default_design, load_design

FILES = "файлы agents.md, memory.md, spec, plan"
STEPS = "три шага: открыть терминал, вставить команду, нажать Enter."


def said(at, text, step=0.4):
    return [{"text": w, "start": round(at + k * step, 3), "end": round(at + k * step + 0.3, 3)}
            for k, w in enumerate(text.split())]


class FakeCtx:
    def __init__(self, words, **params):
        self.words, self.params = words, dict(params)
        self.overlays, self.chapters, self.notes, self.asked, self.answers = [], [], [], {}, {}

    def p(self, name, default=None):
        value = self.params.get(name)
        return default if value is None else value

    def transcript(self):
        return {"words": self.words}

    def design(self, vertical=False):
        return load_design(default_design())

    def note(self, text):
        if text not in self.notes:
            self.notes.append(text)

    def ask(self, key, question, payload):
        self.asked[key] = payload
        edit = self.answers.get(key)
        if edit:
            edit(payload)
        return True, payload


def ready():
    return mock.patch("runtime.render.hf_ready.problem", return_value=None)


class Moments(unittest.TestCase):
    def test_files_said_in_a_row_become_a_files_slot_of_four(self):
        found = detect({"start": 0, "words": said(0, FILES)})
        self.assertEqual(found["template"], "файлы")
        self.assertEqual(found["items"], ["agents.md", "memory.md", "spec", "plan"])

    def test_steps_list_and_number(self):
        self.assertEqual(detect({"start": 0, "words": said(0, STEPS)})["template"], "шаги")
        self.assertEqual(detect({"start": 0, "words": said(0, "это экономит 40 процентов времени.")})["title"], "40%")
        self.assertIsNone(detect({"start": 0, "words": said(0, "просто фраза без перечислений.")}))


# Phrases of the trial lesson (29.10): two were offered as «список» before the repair, the files never.
TALK = "Как челове-- как я, например, да, там, что-то в блокнотик записать, что-то важное, чтобы не забыть."
MEMORY = "которое откладывается в памяти, естественно, это все подгружается в эту новую сессию."
SPOKEN_FILES = "Для этого нам помогать будут специальные файлы, такие как agents MD, memory MD, spec, plan, intent."


class TrialLesson(unittest.TestCase):
    def test_talk_is_not_a_list_and_files_said_apart_are_found(self):
        self.assertIsNone(detect({"start": 0, "words": said(0, TALK)}))
        self.assertIsNone(detect({"start": 0, "words": said(0, MEMORY)}))
        found = detect({"start": 0, "words": said(0, SPOKEN_FILES)})
        self.assertEqual(found["template"], "файлы")
        self.assertEqual(found["items"], ["agents.md", "memory.md", "spec", "plan", "intent"])

    def test_the_files_win_their_window_over_earlier_weaker_moments(self):
        words = said(12.6, TALK) + said(59.8, MEMORY) + said(70.0, "важны контекст, память, инструменты.") + \
            said(82.0, SPOKEN_FILES)
        ctx = FakeCtx(words, animations={"every": 45})
        with ready():
            plan_animations(ctx)
        items = ctx.asked["animations"]["items"]
        self.assertEqual([(i["template"], i["start"]) for i in items], [("файлы", 82.0)])

    def test_every_file_name_is_kept_and_bare_numbers_are_not_moments(self):
        found = detect({"start": 0, "words": said(0, "кладём CLAUDE.md и README.md, а потом agents.md и spec.md рядом.")})
        self.assertEqual(found["items"], ["CLAUDE.md", "README.md", "agents.md", "spec.md"])
        self.assertIsNone(detect({"start": 0, "words": said(0, "у нас было 3 попытки, потом 5.")}))
        self.assertEqual(detect({"start": 0, "words": said(0, "окно на 200 тысяч токенов.")})["title"], "200 тысяч")


class Plan(unittest.TestCase):
    def test_slot_in_the_question_and_two_lists_closer_than_every_are_one(self):
        ctx = FakeCtx(said(10.0, FILES + ".") + said(30.0, STEPS), animations={"every": 45})
        with ready():
            plan_animations(ctx)
        items = ctx.asked["animations"]["items"]
        self.assertEqual(len(items), 1, "the steps 20 s later are inside `every`")
        self.assertEqual(items[0]["template"], "файлы")
        self.assertEqual(items[0]["items"], ["agents.md", "memory.md", "spec", "plan"])
        self.assertEqual(items[0]["start"], 10.0)
        self.assertEqual([o["kind"] for o in ctx.overlays], ["animation"])

    def test_every_is_kept_between_30_and_60(self):
        ctx = FakeCtx(said(10.0, FILES + ".") + said(42.0, STEPS), animations={"every": 10})
        self.assertEqual(every(ctx), 30.0)
        with ready():
            plan_animations(ctx)
        self.assertEqual(len(ctx.asked["animations"]["items"]), 2)
        self.assertEqual(every(FakeCtx([], animations={"every": 90})), 60.0)

    def test_no_slot_on_a_chapter_plate(self):
        ctx = FakeCtx(said(10.0, FILES + ".") + said(70.0, STEPS), chapters={"plates": True, "every": 100})
        ctx.answers["chapters"] = lambda p: p["items"][0].update(title="Файлы проекта")
        plan_chapters(ctx)
        self.assertEqual(ctx.overlays[0]["start"], 10.0)
        with ready():
            plan_animations(ctx)
        starts = [s["start"] for s in ctx.asked["animations"]["items"]]
        self.assertNotIn(10.0, starts, "the chapter plate holds the screen at 10 s")
        self.assertEqual(starts, [70.0])

    def test_insert_moved_onto_a_plate_is_taken_off(self):
        ctx = FakeCtx(said(10.0, FILES + ".") + said(70.0, STEPS), chapters={"plates": True, "every": 100})
        ctx.answers["chapters"] = lambda p: p["items"][0].update(title="Начало")
        plan_chapters(ctx)
        ctx.answers["animations"] = lambda p: p["items"][0].update(start=11.0, end=15.0)
        with ready():
            plan_animations(ctx)
        self.assertEqual([o["kind"] for o in ctx.overlays], ["chapter"])
        self.assertTrue(any("плашка главы" in n for n in ctx.notes))

    def test_card_and_animation_never_both_at_one_moment(self):
        ctx = FakeCtx(said(10.0, FILES + ".") + said(20.0, "Дальше идём."), cards=True)
        ctx.answers["cards"] = lambda p: [s.update(text="Файлы\nчто лежит в проекте") for s in p["items"]]
        plan_cards(ctx)
        self.assertTrue(any(o["kind"] == "card" and o["start"] == 10.0 for o in ctx.overlays))
        with ready():
            plan_animations(ctx)
        at_ten = [o for o in ctx.overlays if o["start"] < 14.0 and o["end"] > 10.0]
        self.assertEqual([o["kind"] for o in at_ten], ["animation"])
        self.assertTrue(any("снята: в этот момент анимация «файлы»" in n for n in ctx.notes))
        self.assertTrue(any(o["kind"] == "card" and o["start"] == 20.0 for o in ctx.overlays), "others stay")

    def test_answer_as_a_line_with_a_clock_start_and_overlaps_taken_off(self):
        ctx = FakeCtx(said(10.0, FILES + "."))
        ctx.answers["animations"] = lambda p: p.update(items=[
            {"template": "файлы", "title": "Файлы", "items": "agents.md, memory.md", "start": "0:00:10"},
            {"template": "шаги", "title": "Шаги", "items": ["раз", "два"], "start": 12.0},
            {"template": "список", "items": ["a", "b", "c"], "start": "потом"}])
        with ready():
            plan_animations(ctx)
        inserts = [o for o in ctx.overlays if o["kind"] == "animation"]
        self.assertEqual([(o["start"], o["items"]) for o in inserts], [(10.0, ["agents.md", "memory.md"])])
        self.assertTrue(any("пересекается с анимацией" in n for n in ctx.notes), ctx.notes)
        self.assertTrue(any("не понял start «потом»" in n for n in ctx.notes), ctx.notes)

    def test_empty_answer_means_no_animations(self):
        ctx = FakeCtx(said(10.0, FILES + "."))
        ctx.answers["animations"] = lambda p: p.update(items=[])
        with ready():
            plan_animations(ctx)
        self.assertEqual(ctx.overlays, [])

    def test_without_hyperframes_nothing_is_asked_and_the_report_says_why(self):
        ctx = FakeCtx(said(10.0, FILES + "."))
        with mock.patch("runtime.render.hf_ready.problem", return_value="нет Node.js 22+ в PATH"):
            plan_animations(ctx)
        self.assertNotIn("animations", ctx.asked)
        self.assertIn("Анимации не делались: нет Node.js 22+ в PATH", ctx.notes)


if __name__ == "__main__":
    unittest.main()
