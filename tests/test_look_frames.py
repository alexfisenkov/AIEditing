"""Snapshots of a source: n frames spread over the clip, each file knows its time."""
import unittest

from _support import TempDirCase, make_tone, needs_ffmpeg


@needs_ffmpeg
class Frames(TempDirCase):
    def test_n_frames_spread_evenly_with_times(self):
        from runtime.look import frame_time, frames

        src = make_tone(self.tmp / "исходник с пробелом.mp4", duration=8.0)
        shots = frames(src, 4, outdir=self.tmp / "кадры")
        self.assertEqual(len(shots), 4)
        for shot in shots:
            self.assertTrue(shot.is_file() and shot.stat().st_size > 0, shot)
            self.assertEqual(shot.parent, self.tmp / "кадры")
        times = [frame_time(s) for s in shots]
        # Middles of four equal parts of 8 s: 1, 3, 5, 7.
        for got, want in zip(times, [1.0, 3.0, 5.0, 7.0]):
            self.assertAlmostEqual(got, want, delta=0.05)

    def test_default_outdir_is_a_fresh_temp_folder(self):
        from runtime.look import frames

        src = make_tone(self.tmp / "a.mp4", duration=2.0)
        shots = frames(src, 2)
        self.assertEqual(len(shots), 2)
        self.assertNotEqual(shots[0].parent, src.parent)

    def test_foreign_file_has_no_time(self):
        from runtime.look import frame_time

        self.assertIsNone(frame_time(self.tmp / "скриншот.png"))


if __name__ == "__main__":
    unittest.main()
