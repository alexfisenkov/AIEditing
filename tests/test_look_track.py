"""Following a moving area over frames (a scrolled window, a dragged chat)."""
import importlib.util
import unittest

from _support import TempDirCase, ffmpeg, needs_ffmpeg

HAVE_NUMPY = importlib.util.find_spec("numpy") is not None
SIZE = (320, 240)
PATCH = 48


def truth(t):
    """Where the moving patch's top-left corner is at time t (hand-set motion of the test clip)."""
    return 20 + 60 * t, 100 + 10 * t


def moving_patch(path, duration=3.0):
    """Grey background with a detailed 48x48 patch drifting right and slightly down."""
    ffmpeg("-f", "lavfi", "-i", "color=c=gray:s={}x{}:r=25:d={}".format(SIZE[0], SIZE[1], duration),
           "-f", "lavfi", "-i", "testsrc=s={0}x{0}:r=25:d={1}".format(PATCH, duration),
           "-filter_complex", "[0:v][1:v]overlay=x='20+60*t':y='100+10*t'",
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "12", "-pix_fmt", "yuv420p", str(path))
    return path


AREA = {"x": 20, "y": 100, "w": PATCH, "h": PATCH, "start": 0.0, "end": 3.0, "track": True}


@needs_ffmpeg
@unittest.skipUnless(HAVE_NUMPY, "numpy not installed (ae.py doctor installs it)")
class Track(TempDirCase):
    def test_path_follows_the_patch(self):
        from runtime.look import track_region

        src = moving_patch(self.tmp / "чат едет.mp4")
        path = track_region(src, AREA)
        self.assertGreaterEqual(len(path), 10)
        self.assertAlmostEqual(path[0]["t"], 0.0, delta=0.01)
        self.assertGreater(path[-1]["t"], 2.5)
        for point in path:
            x, y = truth(point["t"])
            self.assertLessEqual(abs(point["x"] - x), 6, point)
            self.assertLessEqual(abs(point["y"] - y), 6, point)


if __name__ == "__main__":
    unittest.main()
