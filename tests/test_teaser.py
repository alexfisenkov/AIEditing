"""The teaser: a Play button on black, fragments and fast-forwards, a bar that shows where in the whole video it is."""
import unittest

from _support import TempDirCase, needs_ffmpeg
from test_bands import said
from test_pipelines_helpers import Approver, asr_config, profile
from test_vertical_source import horizontal

FRAGMENTS = [{"start": 2.0, "end": 8.0, "rate": 1.2}, {"start": 20.0, "end": 50.0, "rate": 10},
             {"start": 60.0, "end": 66.0, "rate": 1.2}]


class Moments(unittest.TestCase):
    def test_every_frame_knows_its_place_in_the_whole_video(self):
        from runtime.pipelines.teaser import FPS, moments

        got = moments(FRAGMENTS)
        self.assertEqual(len(got), int(round(5.0 * FPS)) + 3 * FPS + int(round(5.0 * FPS)))
        self.assertAlmostEqual(got[0]["t"], 2.0)
        self.assertEqual(got[int(5.0 * FPS)]["rate"], 10)
        self.assertAlmostEqual(got[int(5.0 * FPS)]["t"], 20.0)
        self.assertEqual(sorted(m["t"] for m in got), [m["t"] for m in got], "полоса идёт только вперёд")

    def test_atempo_is_chained_above_two(self):
        from runtime.media.teaser import _tempo

        self.assertEqual(_tempo(8.0), "atempo=2,atempo=2,atempo=2.0000")
        self.assertEqual(_tempo(1.2), "atempo=1.2000")

    def test_a_wild_rate_is_refused(self):
        from runtime.pipelines.errors import PipelineError
        from runtime.pipelines.teaser import rate_of_fragment

        with self.assertRaises(PipelineError):
            rate_of_fragment({"rate": 1000})

    def test_time_stamps(self):
        from runtime.render.player import stamp

        self.assertEqual(stamp(1583.8), "26:23")
        self.assertEqual(stamp(3700), "1:01:40")


@needs_ffmpeg
class Teaser(TempDirCase):
    def run_teaser(self, edit):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("нет Pillow")
        from runtime import pipelines

        src = horizontal(self.tmp / "готовый.mp4", 90)
        prof = profile(["speech_spans", "teaser"], asr_config(self.tmp, {"words": said(0.0, 44)}), teaser_name="Тизер")
        approve = Approver(edits={"teaser": edit})
        return pipelines.run(src, prof, self.tmp / "выпуск", approve), approve

    def test_the_teaser_is_written_with_the_length_of_its_fragments(self):
        from runtime.media import probe
        from runtime.pipelines.teaser import INTRO

        report, approve = self.run_teaser(lambda p: p.update(fragments=FRAGMENTS))
        self.assertIn("teaser", approve.asked)
        teaser = next(o for o in report["outputs"] if o["id"] == "teaser")
        self.assertEqual(teaser["video"].name, "Тизер.mp4")
        info = probe(teaser["video"])
        self.assertEqual((info["width"], info["height"]), (320, 180))
        self.assertTrue(info["has_audio"])
        self.assertAlmostEqual(info["duration"], INTRO + 5.0 + 3.0 + 5.0, delta=0.4)

    def test_refusing_the_teaser_leaves_the_run_whole(self):
        from runtime import pipelines

        src = horizontal(self.tmp / "готовый.mp4", 20)
        prof = profile(["speech_spans", "vertical", "teaser"], asr_config(self.tmp, {"words": said(0.0, 9)}),
                       layout={"kind": "native"}, vertical_source="native")
        report = pipelines.run(src, prof, self.tmp / "выпуск", Approver(answers={"teaser": False}))
        self.assertEqual([o["id"] for o in report["outputs"]], ["v01"])
        self.assertTrue((self.tmp / "выпуск" / "отчёт.md").is_file())

    def test_a_fragment_past_the_end_is_refused_before_anything_is_made(self):
        from runtime.pipelines.errors import PipelineError
        from runtime.pipelines.teaser import check_fragments

        with self.assertRaises(PipelineError):
            check_fragments([{"start": 80.0, "end": 120.0}], 90.0)
        with self.assertRaises(PipelineError):
            check_fragments([{"start": 50.0, "end": 60.0}, {"start": 20.0, "end": 30.0}], 90.0)
        with self.assertRaises(PipelineError):
            check_fragments([{"start": 1.0, "end": 2.0, "rate": 1000}], 90.0)

    def test_a_percent_in_the_folder_is_not_a_number_of_a_frame(self):
        from runtime.render.player import frames_pattern

        self.assertTrue(frames_pattern(self.tmp / "скидка 50%").endswith("50%%/%05d.png".replace("/", __import__("os").sep)))

    def test_the_draft_stays_in_the_order_of_the_video_even_without_short_phrases(self):
        seen = []
        report, _ = self.run_teaser(lambda p: seen.extend(p["fragments"]))
        self.assertTrue(report["outputs"])
        self.assertGreater(len(seen), 2)
        starts = [f["start"] for f in seen]
        self.assertEqual(starts, sorted(starts))
        self.assertTrue(all(f["end"] <= 90 for f in seen))


if __name__ == "__main__":
    unittest.main()
