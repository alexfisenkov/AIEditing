"""A chapter title is on screen once: as the chapter plate; a card never repeats it (no ffmpeg needed)."""
import unittest

import _support  # noqa: F401  (puts the skill on sys.path)
from runtime.pipelines.cards import plan_cards
from runtime.pipelines.chapters import plan_chapters

WORDS = [("Контекстные", 22.26, 22.8), ("окна.", 22.9, 23.3), ("Дальше", 24.0, 24.4), ("идёт.", 24.5, 24.9),
         ("Потом", 30.0, 30.4), ("считаем.", 30.5, 31.0), ("Итог", 40.0, 40.4), ("такой.", 40.5, 41.0)]
TITLE = "Контекстные окна"


class FakeCtx:
    """Just what the planners use: params, words, answers by key, overlays and notes."""

    def __init__(self, cards=None):
        self.params = {"chapters": {"plates": True, "seconds": 3.5}, "cards": True}
        self.overlays, self.chapters, self.notes, self.asked = [], [], [], {}
        self.cards, self.keep = cards or {}, [(0.0, 1e9)]

    def p(self, name, default=None):
        value = self.params.get(name)
        return default if value is None else value

    def transcript(self):
        return {"words": [{"text": t, "start": a, "end": b} for t, a, b in WORDS]}

    def design(self):
        return {"video": {"chapter": {"seconds": 3.0}}}

    def note(self, text):
        if text not in self.notes:
            self.notes.append(text)

    def ask(self, key, question, payload):
        self.asked[key] = payload
        if key == "cards":
            for item in payload["items"]:
                item["text"] = self.cards.get(round(item["start"], 2), "")
        return True, payload


def planned(cards):
    ctx = FakeCtx(cards)
    plan_chapters(ctx)
    plan_cards(ctx)
    return ctx


def kinds(ctx):
    return [(o["kind"], o["text"].split("\n")[0]) for o in ctx.overlays]


class ChapterPlateOnce(unittest.TestCase):
    def test_card_titled_like_the_chapter_is_taken_off_with_a_note(self):
        ctx = FakeCtx()
        plan_chapters(ctx)
        # the answer to `cards` carries the chapter's title at the chapter's start, as in the probe at 0:22
        ctx.ask = lambda key, q, payload: (True, {"items": [{"start": 22.26, "end": 26.26, "text": TITLE + "\nпояснение"}]})
        plan_cards(ctx)
        self.assertEqual(kinds(ctx), [("chapter", TITLE)])
        self.assertEqual(len(ctx.notes), 1)
        self.assertIn("снята", ctx.notes[0])
        self.assertIn("совпала с главой", ctx.notes[0])
        self.assertIn(TITLE, ctx.notes[0])

    def test_title_match_ignores_case_and_punctuation_even_off_the_plate(self):
        ctx = FakeCtx()
        plan_chapters(ctx)
        ctx.ask = lambda key, q, payload: (True, {"items": [{"start": 40.0, "end": 44.0, "text": "КОНТЕКСТНЫЕ  окна!"}]})
        plan_cards(ctx)
        self.assertEqual(kinds(ctx), [("chapter", TITLE)])
        self.assertIn("совпала с главой", ctx.notes[0])

    def test_card_with_other_text_overlapping_the_plate_is_taken_off(self):
        ctx = FakeCtx()
        plan_chapters(ctx)
        ctx.ask = lambda key, q, payload: (True, {"items": [{"start": 24.0, "end": 28.0, "text": "Другое\nтекст"}]})
        plan_cards(ctx)
        self.assertEqual(kinds(ctx), [("chapter", TITLE)])
        self.assertIn("«Другое»", ctx.notes[0])
        self.assertIn("совпала с главой", ctx.notes[0])

    def test_card_outside_the_plate_with_another_title_stays(self):
        ctx = planned({30.0: "Токены\nединицы счёта"})
        self.assertEqual(kinds(ctx), [("chapter", TITLE), ("card", "Токены")])
        self.assertEqual(ctx.notes, [])

    def test_card_slots_stay_clear_of_the_plate(self):
        ctx = planned({})
        starts = [s["start"] for s in ctx.asked["cards"]["items"]]
        self.assertTrue(starts, "slots are still offered where there is no plate")
        end = 22.26 + 3.5  # the plate's own length from the profile
        for s in starts:
            self.assertFalse(s < end and s + 4.0 > 22.26, "slot at {} lands on the plate".format(s))
        self.assertEqual(starts[0], 30.0)

    def test_without_chapter_plates_cards_are_left_alone(self):
        ctx = FakeCtx({22.26: TITLE + "\nпояснение"})
        ctx.params["chapters"] = {"timecodes": True}
        plan_chapters(ctx)
        plan_cards(ctx)
        self.assertEqual(kinds(ctx), [("card", TITLE)])


if __name__ == "__main__":
    unittest.main()
