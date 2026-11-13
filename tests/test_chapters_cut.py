"""A chapter whose start fell into a cut moves to the first kept moment after the cut, never to 0:00 (no ffmpeg)."""
import unittest

import _support  # noqa: F401  (puts the skill on sys.path)
from runtime.pipelines.chapters import plan_chapters
from runtime.pipelines.timeline import to_out

WORDS = [("Начало", 1.0, 1.5), ("рассказа.", 1.6, 2.2), ("Вторая", 14.5, 15.0), ("часть.", 16.0, 16.4),
         ("Третья", 40.0, 40.5), ("часть.", 40.6, 41.0)]
KEEP = [(0.0, 14.3), (15.8, 60.0)]  # 14.3–15.8 is cut away


class FakeCtx:
    def __init__(self, answer):
        self.params = {"chapters": {"timecodes": True}}
        self.overlays, self.chapters, self.notes, self.keep = [], [], [], list(KEEP)
        self.answer = answer

    def p(self, name, default=None):
        value = self.params.get(name)
        return default if value is None else value

    def transcript(self):
        return {"words": [{"text": t, "start": a, "end": b} for t, a, b in WORDS]}

    def design(self):
        return {"video": {"chapter": {"seconds": 3.0}}}

    def note(self, text):
        self.notes.append(text)

    def ask(self, key, question, payload):
        return True, {"items": [dict(c) for c in self.answer]}


class ChapterInACut(unittest.TestCase):
    def test_a_start_inside_a_cut_lands_on_the_first_kept_second_after_it(self):
        ctx = FakeCtx([{"start": 0.0, "title": "Начало"}, {"start": 14.5, "title": "Вторая"},
                       {"start": 40.0, "title": "Третья"}])
        plan_chapters(ctx)
        self.assertEqual([c["title"] for c in ctx.chapters], ["Начало", "Вторая", "Третья"])
        self.assertEqual([c["start"] for c in ctx.chapters], [0.0, 15.8, 40.0])
        # 15.8 s of the source is the first second after the cut: 14.3 s of the finished video, not 0:00
        self.assertEqual([to_out(c["start"], ctx.keep) for c in ctx.chapters], [0.0, 14.3, 38.5])

    def test_a_start_after_everything_kept_stays_at_the_end_not_at_zero(self):
        ctx = FakeCtx([{"start": 0.0, "title": "А"}, {"start": 61.0, "title": "Хвост"}])
        ctx.keep = [(0.0, 50.0)]
        plan_chapters(ctx)
        self.assertEqual([to_out(c["start"], ctx.keep) for c in ctx.chapters], [0.0, 50.0])


if __name__ == "__main__":
    unittest.main()
