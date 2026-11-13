"""The publishing pack: YouTube chapters by YouTube's rules, places for the words, frames in the pauses of the speech."""
import re

from _support import TempDirCase, ffmpeg, needs_ffmpeg
from runtime.pipelines import publish


def rules_hold(test, chapters, total):
    """YouTube: the first at 0:00, at least three, in order, each at least 10 s long."""
    times = [t for t, _ in chapters]
    test.assertEqual(times[0], 0)
    test.assertGreaterEqual(len(times), 3)
    test.assertEqual(times, sorted(set(times)))
    for a, b in zip(times, times[1:] + [int(total)]):
        test.assertGreaterEqual(b - a, 10, chapters)


class Chapters(TempDirCase):
    def test_good_chapters_pass_as_they_are(self):
        got = publish.youtube_chapters([(0.0, "Начало"), (65.4, "Как"), (130.9, "Итог")], 200.0)
        self.assertEqual(got, [(0, "Начало"), (65, "Как"), (130, "Итог")])

    def test_a_first_chapter_a_little_late_starts_at_zero_and_a_late_one_gets_a_place_before_it(self):
        self.assertEqual(publish.youtube_chapters([(4.6, "А"), (60, "Б"), (120, "В")], 200)[0], (0, "А"))
        got = publish.youtube_chapters([(30, "А"), (60, "Б"), (120, "В")], 200)
        self.assertEqual([t for t, _ in got], [0, 30, 60, 120])
        self.assertRegex(got[0][1], r"^\[.*впиши.*\]$")  # the pipeline does not make up a title

    def test_a_too_short_chapter_merges_instead_of_breaking_the_list(self):
        self.assertEqual(publish.youtube_chapters([(0, "А"), (60, "Б"), (66, "В"), (120, "Г")], 300),
                         [(0, "А"), (66, "В"), (120, "Г")])
        self.assertEqual(publish.youtube_chapters([(0, "А"), (5, "Б"), (60, "В"), (120, "Г")], 300),
                         [(0, "А"), (60, "В"), (120, "Г")])
        self.assertEqual(publish.youtube_chapters([(0, "А"), (60, "Б"), (120, "В"), (295, "Г")], 300),
                         [(0, "А"), (60, "Б"), (120, "В")])

    def test_fewer_than_three_is_no_list(self):
        self.assertEqual(publish.youtube_chapters([(0, "А"), (60, "Б")], 300), [])
        self.assertEqual(publish.youtube_chapters([(0, "А"), (4, "Б"), (8, "В")], 300), [])
        self.assertEqual(publish.youtube_chapters([], 300), [])

    def test_whatever_comes_in_the_rules_hold_on_what_goes_out(self):
        starts = [0.0, 3.0, 9.5, 19.0, 20.0, 45.0, 46.0, 47.0, 58.0, 71.0, 79.0, 92.0, 118.0]
        got = publish.youtube_chapters([(t, "глава {}".format(k)) for k, t in enumerate(reversed(starts))], 125.0)
        rules_hold(self, got, 125.0)

    def test_the_clock_is_minutes_and_seconds_and_hours_only_when_needed(self):
        self.assertEqual(publish.clock(0, 600), "0:00")
        self.assertEqual(publish.clock(125, 600), "2:05")
        self.assertEqual(publish.clock(125, 4000), "0:02:05")


class Ctx:
    """What the pack reads from a run."""

    def __init__(self, outdir, words, chapters, keep, speed=1.0):
        self.outdir, self.chapters, self.keep = outdir, chapters, keep
        self.params, self.notes, self.decisions = {"speed": speed}, [], []
        self._words = {"words": words}
        self.profile = {"format": "ютуб"}

    def p(self, name, default=None):
        value = self.params.get(name)
        return default if value is None else value

    def has(self, step):
        return step == "publish_pack"

    def transcript(self):
        return self._words

    def note(self, text):
        self.notes.append(text)


@needs_ffmpeg
class Pack(TempDirCase):
    def setUp(self):
        super().setUp()
        self.video = self.tmp / "выпуск" / "ролик.mp4"
        self.video.parent.mkdir()
        ffmpeg("-f", "lavfi", "-i", "testsrc=s=320x180:r=25:d=60", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
               "-t", "60", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
               str(self.video))
        # speech everywhere but four pauses: 9–11, 24–27, 40–41, 52–55 (source = finished video, nothing cut)
        self.pauses = [(9.0, 11.0), (24.0, 27.0), (40.0, 41.0), (52.0, 55.0)]
        edges = [0.0] + [x for p in self.pauses for x in p] + [60.0]
        self.words = []
        for a, b in zip(edges[0::2], edges[1::2]):
            t = a
            while t + 0.3 <= b:
                self.words.append({"text": "слово", "start": round(t, 2), "end": round(min(t + 0.3, b), 2)})
                t += 0.35

    def test_the_file_has_youtube_chapters_and_places_not_words(self):
        chapters = [{"start": 0.0, "title": "Начало"}, {"start": 20.0, "title": "Середина"}, {"start": 38.0, "title": "Итог"},
                    {"start": 55.0, "title": "Хвост"}]  # 5 s to the end: merged into «Итог»
        ctx = Ctx(self.video.parent, self.words, chapters, [(0.0, 60.0)])
        path = publish.write_pack(ctx, self.video)
        self.assertEqual(path, self.video.parent / "публикация.md")
        text = path.read_text(encoding="utf-8")
        block = re.findall(r"^(\d+:\d\d) (.+)$", text, re.M)
        self.assertEqual(block, [("0:00", "Начало"), ("0:20", "Середина"), ("0:38", "Итог")])
        self.assertEqual(len(re.findall(r"\[НАЗВАНИЕ \d — впиши", text)), 3)
        self.assertIn("100", text)
        self.assertIn("[ОПИСАНИЕ — впиши", text)
        self.assertIn("[ТЕГИ — впиши", text)
        self.assertIn("Хвост", text)  # what was merged is said, not lost silently
        self.assertIn("run.py covers", text)

    def test_frames_are_taken_in_the_pauses_of_the_speech(self):
        ctx = Ctx(self.video.parent, self.words, [], [(0.0, 60.0)])
        publish.write_pack(ctx, self.video)
        frames = sorted((self.video.parent / "обложки" / "кадры").glob("*.jpg"))
        self.assertGreaterEqual(len(frames), 4)
        text = (self.video.parent / "публикация.md").read_text(encoding="utf-8")
        listed = re.findall(r"кадр-\d\d\.jpg — (\d+):(\d\d)\.(\d)", text)
        self.assertEqual(len(listed), len(frames))
        for m, s, d in listed:
            at = int(m) * 60 + int(s) + int(d) / 10.0
            self.assertTrue(any(a <= at <= b for a, b in self.pauses), at)
        self.assertIn("Глав", text)  # no chapters: the file says so instead of an empty list

    def test_a_cut_and_a_speed_move_the_chapters_into_the_finished_video(self):
        ctx = Ctx(self.video.parent, self.words, [{"start": 0.0, "title": "А"}, {"start": 40.0, "title": "Б"},
                                                  {"start": 90.0, "title": "В"}], [(0.0, 20.0), (30.0, 110.0)], speed=1.25)
        text = publish.write_pack(ctx, self.video).read_text(encoding="utf-8")
        # 40 s of the source is 30 s of the cut, 24 s at 1.25; 90 s → 80 s → 64 s
        self.assertEqual(re.findall(r"^(\d+:\d\d) (.)$", text, re.M), [("0:00", "А"), ("0:24", "Б"), ("1:04", "В")])
