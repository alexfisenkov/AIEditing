"""Still area blurred inside its time span only; nothing else in the picture or the length changes."""
import subprocess
import unittest

from _support import TempDirCase, ffmpeg, needs_ffmpeg


def gray_frame(path, t, size):
    """Luma bytes of the frame at `t` seconds, as rows of ints."""
    w, h = size
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-ss", "{:.3f}".format(t),
           "-i", str(path), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, stdout=subprocess.PIPE, check=True).stdout
    return [list(raw[y * w:(y + 1) * w]) for y in range(h)]


def sharpness(rows, x, y, w, h):
    """Mean brightness step between neighbouring pixels inside a box: high for text, ~0 for blur."""
    steps = [abs(rows[j][i + 1] - rows[j][i]) for j in range(y, y + h) for i in range(x, x + w - 1)]
    return sum(steps) / float(len(steps))


def checker_video(path, duration=3.0, size=(320, 240), cell=4):
    """A fine checkerboard (stands in for small text) with a tone, so blur has something to kill."""
    w, h = size
    ffmpeg("-f", "lavfi", "-i", "nullsrc=s={}x{}:r=25:d={},geq=lum='if(mod(floor(X/{c})+floor(Y/{c}),2),235,16)'"
           ":cb=128:cr=128".format(w, h, duration, c=cell),
           "-f", "lavfi", "-i", "sine=f=440:d={}".format(duration),
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "12", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-shortest", str(path))
    return path


SIZE = (320, 240)
AREA = {"x": 80, "y": 60, "w": 120, "h": 80, "start": 1.0, "end": 2.0, "track": False}


@needs_ffmpeg
class StaticBlur(TempDirCase):
    def setUp(self):
        super().setUp()
        self.src = checker_video(self.tmp / "эфир с секретом.mp4", size=SIZE)

    def test_area_unreadable_only_inside_span_and_length_kept(self):
        from runtime.media import blur_regions, probe

        out = blur_regions(self.src, [AREA], self.tmp / "выход" / "эфир.mp4")
        before, after = probe(self.src), probe(out)
        self.assertAlmostEqual(after["duration"], before["duration"], delta=0.05)
        self.assertAlmostEqual(after["audio_duration"], before["audio_duration"], delta=0.05)
        box = (AREA["x"] + 4, AREA["y"] + 4, AREA["w"] - 8, AREA["h"] - 8)
        outside = (220, 160, 80, 60)
        for t, inside_blurred in ((0.5, False), (1.5, True), (2.5, False)):
            src_rows, out_rows = gray_frame(self.src, t, SIZE), gray_frame(out, t, SIZE)
            ratio = sharpness(out_rows, *box) / sharpness(src_rows, *box)
            if inside_blurred:
                self.assertLess(ratio, 0.15, "t={}: area still readable".format(t))
            else:
                self.assertGreater(ratio, 0.8, "t={}: area touched outside its span".format(t))
            kept = sharpness(out_rows, *outside) / sharpness(src_rows, *outside)
            self.assertGreater(kept, 0.8, "t={}: picture outside the area changed".format(t))

    def test_area_reaching_past_the_edge_is_clipped_not_an_error(self):
        from runtime.media import blur_regions, probe

        edge = dict(AREA, x=280, y=200, w=100, h=100)
        out = blur_regions(self.src, [edge, AREA], self.tmp / "край.mp4")
        self.assertAlmostEqual(probe(out)["duration"], probe(self.src)["duration"], delta=0.05)


if __name__ == "__main__":
    unittest.main()
