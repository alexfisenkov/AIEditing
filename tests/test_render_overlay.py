"""PNG overlays on video through ffmpeg's overlay filter — works on builds without drawtext."""
import subprocess
import unittest

from _support import TempDirCase, ffmpeg, needs_ffmpeg
from test_blur_static import gray_frame

SIZE = (320, 240)


def has_drawtext():
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], stdout=subprocess.PIPE,
                         encoding="utf-8", errors="replace").stdout
    return " drawtext " in out


@needs_ffmpeg
class OverlayPng(TempDirCase):
    def setUp(self):
        super().setUp()
        self.src = self.tmp / "чёрный.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=black:s={}x{}:r=25:d=3".format(*SIZE),
               "-f", "lavfi", "-i", "sine=f=440:d=3", "-c:v", "libx264", "-preset", "ultrafast",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(self.src))
        self.png = self.tmp / "плашка.png"  # a white 40x20 box made by ffmpeg, no Pillow needed
        ffmpeg("-f", "lavfi", "-i", "color=c=white:s=40x20", "-frames:v", "1", str(self.png))

    def test_picture_shows_only_in_its_span_at_its_place(self):
        from runtime.media import overlay_png, probe

        out = overlay_png(self.src, [{"png": self.png, "x": 100, "y": 50, "start": 1.0, "end": 2.0,
                                      "fade": 0.0}], self.tmp / "с плашкой.mp4")
        self.assertAlmostEqual(probe(out)["duration"], probe(self.src)["duration"], delta=0.05)
        self.assertAlmostEqual(probe(out)["audio_duration"], probe(self.src)["audio_duration"], delta=0.05)
        inside = lambda rows: rows[60][120]  # noqa: E731
        self.assertGreater(inside(gray_frame(out, 1.5, SIZE)), 200)
        self.assertLess(inside(gray_frame(out, 0.5, SIZE)), 40)
        self.assertLess(inside(gray_frame(out, 2.5, SIZE)), 40)
        self.assertLess(gray_frame(out, 1.5, SIZE)[200][300], 40)  # elsewhere untouched

    def test_frame_sized_layers_stack_and_fade(self):
        from runtime.media import overlay_png

        layers = [{"png": self.png, "x": 10, "y": 10, "start": 0.0, "end": 3.0, "fade": 0.5},
                  {"png": self.png, "x": 200, "y": 150, "start": 0.5, "end": 1.5}]
        out = overlay_png(self.src, layers, self.tmp / "два.mp4")
        rows = gray_frame(out, 1.0, SIZE)
        self.assertGreater(rows[20][20], 200)
        self.assertGreater(rows[160][210], 200)
        self.assertLess(gray_frame(out, 0.1, SIZE)[20][20], 120)  # still fading in

    @unittest.skipIf(has_drawtext(), "this ffmpeg has drawtext; the no-drawtext case is not shown here")
    def test_this_ffmpeg_has_no_drawtext(self):
        self.assertFalse(has_drawtext())  # the overlays above passed without it


if __name__ == "__main__":
    unittest.main()
