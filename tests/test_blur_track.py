"""Moving area: with track on, the blur rides along with what it hides."""
import importlib.util
import unittest

from _support import TempDirCase, needs_ffmpeg
from test_blur_static import gray_frame, sharpness
from test_look_track import AREA, PATCH, SIZE, moving_patch, truth

HAVE_NUMPY = importlib.util.find_spec("numpy") is not None


@needs_ffmpeg
@unittest.skipUnless(HAVE_NUMPY, "numpy not installed (ae.py doctor installs it)")
class TrackedBlur(TempDirCase):
    def test_blur_stays_on_the_moving_patch(self):
        from runtime.media import blur_regions, probe

        src = moving_patch(self.tmp / "движется.mp4")
        out = blur_regions(src, [AREA], self.tmp / "закрыто.mp4")
        self.assertAlmostEqual(probe(out)["duration"], probe(src)["duration"], delta=0.05)
        for t in (0.5, 1.5, 2.5):
            x, y = (int(round(v)) for v in truth(t))
            box = (x + 6, y + 6, PATCH - 12, PATCH - 12)
            ratio = sharpness(gray_frame(out, t, SIZE), *box) / sharpness(gray_frame(src, t, SIZE), *box)
            self.assertLess(ratio, 0.35, "t={}: the patch is readable".format(t))

    def test_given_path_is_used_as_is(self):
        from runtime.media import blur_regions

        src = moving_patch(self.tmp / "по-пути.mp4")
        still = [{"t": 0.0, "x": 200, "y": 20}, {"t": 3.0, "x": 200, "y": 20}]  # deliberately off the patch
        out = blur_regions(src, [dict(AREA, path=still)], self.tmp / "мимо.mp4")
        x, y = (int(round(v)) for v in truth(1.5))
        box = (x + 6, y + 6, PATCH - 12, PATCH - 12)
        ratio = sharpness(gray_frame(out, 1.5, SIZE), *box) / sharpness(gray_frame(src, 1.5, SIZE), *box)
        self.assertGreater(ratio, 0.8)


if __name__ == "__main__":
    unittest.main()
