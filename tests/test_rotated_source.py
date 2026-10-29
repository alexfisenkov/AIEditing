"""A phone clip stored sideways with a 90° rotation flag: blur and tracking work in the picture as shown."""
import importlib.util
import unittest

from _support import TempDirCase, ffmpeg, needs_ffmpeg
from test_blur_static import gray_frame, sharpness

HAVE_NUMPY = importlib.util.find_spec("numpy") is not None
SHOWN = (240, 320)  # width, height of the picture as the player shows it
PATCH = 48


def rotated(upright, out):
    """The same picture stored turned 90° clockwise, with a flag telling players to turn it back."""
    coded = out.with_name(out.stem + "-coded.mp4")
    ffmpeg("-i", upright, "-vf", "transpose=1", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "12",
           "-pix_fmt", "yuv420p", "-c:a", "copy", coded)
    ffmpeg("-display_rotation", "90", "-i", coded, "-c", "copy", out)
    return out


def checker_upright(path, duration=2.0):
    w, h = SHOWN
    ffmpeg("-f", "lavfi", "-i", "nullsrc=s={}x{}:r=25:d={},geq=lum='if(mod(floor(X/4)+floor(Y/4),2),235,16)'"
           ":cb=128:cr=128".format(w, h, duration),
           "-f", "lavfi", "-i", "sine=f=440:d={}".format(duration),
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "12", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-shortest", path)
    return path


def truth(t):
    """Top-left corner of the moving patch at time t, in the picture as shown (hand-set motion)."""
    return 20 + 40 * t, 200 + 20 * t


def moving_upright(path, duration=3.0):
    ffmpeg("-f", "lavfi", "-i", "color=c=gray:s={}x{}:r=25:d={}".format(SHOWN[0], SHOWN[1], duration),
           "-f", "lavfi", "-i", "testsrc=s={0}x{0}:r=25:d={1}".format(PATCH, duration),
           "-filter_complex", "[0:v][1:v]overlay=x='20+40*t':y='200+20*t'",
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "12", "-pix_fmt", "yuv420p", path)
    return path


@needs_ffmpeg
class RotatedSource(TempDirCase):
    def test_probe_sees_the_rotation(self):
        from runtime.media import probe

        src = rotated(checker_upright(self.tmp / "прямо.mp4"), self.tmp / "телефон.mp4")
        self.assertIn(probe(src)["rotation"], (90, 270))

    def test_blur_covers_an_area_low_in_the_shown_picture(self):
        from runtime.media import blur_regions, probe

        src = rotated(checker_upright(self.tmp / "прямо.mp4"), self.tmp / "телефон.mp4")
        area = {"x": 60, "y": 240, "w": 120, "h": 60, "start": 0.5, "end": 1.5, "track": False}
        out = blur_regions(src, [area], self.tmp / "закрыто.mp4")
        self.assertAlmostEqual(probe(out)["duration"], probe(src)["duration"], delta=0.05)
        before, after = gray_frame(src, 1.0, SHOWN), gray_frame(out, 1.0, SHOWN)
        box = (area["x"] + 4, area["y"] + 4, area["w"] - 8, area["h"] - 8)
        self.assertLess(sharpness(after, *box) / sharpness(before, *box), 0.15, "the area is still readable")
        above = (60, 40, 120, 60)
        self.assertGreater(sharpness(after, *above) / sharpness(before, *above), 0.8, "the wrong place is blurred")

    @unittest.skipUnless(HAVE_NUMPY, "numpy not installed (ae.py doctor installs it)")
    def test_tracking_follows_the_patch_in_the_shown_picture(self):
        from runtime.look import track_region

        src = rotated(moving_upright(self.tmp / "прямо.mp4"), self.tmp / "телефон.mp4")
        x0, y0 = truth(0.0)
        path = track_region(src, {"x": x0, "y": y0, "w": PATCH, "h": PATCH, "start": 0.0, "end": 3.0,
                                  "track": True})
        self.assertGreater(path[-1]["t"], 2.5)
        for point in path:
            x, y = truth(point["t"])
            self.assertLessEqual(abs(point["x"] - x), 6, point)
            self.assertLessEqual(abs(point["y"] - y), 6, point)


if __name__ == "__main__":
    unittest.main()
