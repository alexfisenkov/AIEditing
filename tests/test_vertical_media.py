"""9:16 from any source: stack «screen over face», face close-up, native vertical; platform exports."""
import json
import re
import subprocess
import unittest

from _support import TempDirCase, ffmpeg, needs_ffmpeg
from test_blur_static import gray_frame

OUT = (1080, 1920)


def screen_with_window(path, duration=2.0):
    """1280x720: grey 'screen', a white square 'camera window' at bottom-right, a tone."""
    ffmpeg("-f", "lavfi", "-i", "color=c=0x606060:s=1280x720:r=25:d={}".format(duration),
           "-f", "lavfi", "-i", "sine=f=440:d={}".format(duration),
           "-vf", "drawbox=x=1000:y=460:w=240:h=240:color=white:t=fill",
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-shortest", str(path))
    return path


def loudness(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path), "-vn", "-af",
                          "loudnorm=print_format=json", "-f", "null", "-"],
                         stderr=subprocess.PIPE, encoding="utf-8", errors="replace").stderr
    return float(json.loads(re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", err, re.S)[-1])["input_i"])


@needs_ffmpeg
class Vertical(TempDirCase):
    def setUp(self):
        super().setUp()
        self.src = screen_with_window(self.tmp / "экран и окно.mp4")
        self.window = {"x": 1000, "y": 460, "w": 240, "h": 240}

    def test_stack_puts_screen_on_top_and_window_below(self):
        from runtime.media import probe, vertical

        out = vertical(self.src, {"kind": "stack", "face": self.window, "screen": None},
                       self.tmp / "стек.mp4")
        info = probe(out)
        self.assertEqual((info["width"], info["height"]), OUT)
        self.assertAlmostEqual(info["duration"], 2.0, delta=0.1)
        self.assertTrue(info["has_audio"])
        rows = gray_frame(out, 1.0, OUT)
        # Hand-worked: a 16:9 screen fit to 1080 wide takes the top 608 rows; the window fills the rest.
        self.assertLess(abs(rows[300][100] - 96), 20, "top is the grey screen")
        self.assertGreater(rows[1500][540], 220, "bottom is the white camera window")

    def test_face_close_up_fills_the_frame_from_the_window(self):
        from runtime.media import probe, vertical
        from runtime.media.vertical import face_upscale

        out = vertical(self.src, {"kind": "face", "face": self.window, "screen": None}, self.tmp / "лицо.mp4")
        self.assertEqual((probe(out)["width"], probe(out)["height"]), OUT)
        self.assertGreater(gray_frame(out, 1.0, OUT)[960][540], 220)
        # 240 px of window stretched to 1920 rows: eight times — far too soft.
        self.assertGreater(face_upscale((1280, 720), {"kind": "face", "face": self.window}), 4.0)

    def test_native_vertical_is_not_reframed(self):
        from runtime.media import probe, vertical

        src = self.tmp / "вертикаль.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=black:s=540x960:r=25:d=1",
               "-vf", "drawbox=x=0:y=0:w=60:h=960:color=white:t=fill",
               "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(src))
        out = vertical(src, {"kind": "native", "face": None, "screen": None}, self.tmp / "как есть.mp4")
        self.assertEqual((probe(out)["width"], probe(out)["height"]), OUT)
        rows = gray_frame(out, 0.5, OUT)
        self.assertGreater(rows[960][20], 200, "the left stripe stays at the left edge: nothing cropped")
        self.assertLess(rows[960][300], 40)


@needs_ffmpeg
class Export(TempDirCase):
    def test_three_platform_files_at_their_loudness(self):
        from runtime.media import export_platforms, probe, vertical
        from runtime.media.export import PLATFORMS, safe_zone

        src = screen_with_window(self.tmp / "исходник.mp4", duration=4.0)
        tall = vertical(src, {"kind": "face", "face": {"x": 400, "y": 0, "w": 400, "h": 720}},
                        self.tmp / "вертикаль.mp4")
        outdir = self.tmp / "выгрузка"
        files = export_platforms(tall, outdir)
        self.assertEqual(sorted(p.name for p in files),
                         sorted("вертикаль-{}.mp4".format(k) for k in ("reels", "shorts", "tiktok")))
        for path in files:
            self.assertEqual(path.parent, outdir)
            info = probe(path)
            self.assertEqual((info["width"], info["height"]), OUT)
            platform = path.stem.rsplit("-", 1)[1]
            self.assertAlmostEqual(loudness(path), PLATFORMS[platform]["lufs"], delta=1.5)
        zone = safe_zone()
        for p in PLATFORMS.values():  # the shared zone keeps clear of every platform's buttons
            self.assertGreaterEqual(zone["bottom"], p["safe"]["bottom"])
            self.assertGreaterEqual(zone["top"], p["safe"]["top"])
            self.assertGreaterEqual(zone["side"], max(p["safe"]["left"], p["safe"]["right"]))


if __name__ == "__main__":
    unittest.main()
