"""Laying inserts over a video with ffmpeg: the picture changes inside their windows, the length and the sound do not."""
import re
import subprocess
import unittest

import _support
from _support import TempDirCase, ffmpeg, make_av, needs_ffmpeg
from runtime.media import probe
from runtime.media.broll import lay_broll
from runtime.media.ffmpeg import run


def colour_at(video, t):
    """The mean (r, g, b) of the frame at `t` seconds."""
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", str(t), "-i", str(video),
                          "-frames:v", "1", "-vf", "scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE, check=True).stdout
    return tuple(raw[:3])


def edge_pixel(video, t, x=1, y=60, width=160):
    """The (r, g, b) of one pixel of the frame at `t` seconds."""
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", str(t), "-i", str(video),
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE, check=True).stdout
    i = (y * width + x) * 3
    return tuple(raw[i:i + 3])


def volume(video, a, b):
    err = run(["-ss", a, "-t", b - a, "-i", video, "-vn", "-af", "volumedetect", "-f", "null", "-"]).stderr
    found = re.search(r"mean_volume: (-?[\d.]+|-inf) dB", err)
    return float(found.group(1)) if found else -99.0


@needs_ffmpeg
class LayBroll(TempDirCase):
    def setUp(self):
        super().setUp()
        # 10 s of black with a tone only at 1–3 s: everything else is silent, so a leaked insert sound would show
        self.base = make_av(self.tmp / "основа.mp4", [(1.0, 3.0)], 10, size="160x120", rate=25)
        self.red = self.tmp / "красный.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=red:s=320x180:r=25:d=6", "-f", "lavfi", "-i", "sine=f=1000:d=6",
               "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(self.red))

    def lay(self, items, name="вставки.mp4"):
        return lay_broll(self.base, items, self.tmp / name, probe(self.base))

    def test_a_video_insert_replaces_the_picture_in_its_window_only(self):
        out = self.lay([{"start": 4.0, "end": 7.0, "file": str(self.red), "from": 0.0, "kind": "video"}])
        self.assertGreater(colour_at(out, 5.5)[0], 180)   # red inside the window
        self.assertLess(colour_at(out, 5.5)[1], 60)
        self.assertLess(colour_at(out, 8.5)[0], 40)       # black after it
        self.assertLess(colour_at(out, 3.5)[0], 40)       # black before it
        self.assertEqual(probe(out)["width"], 160)

    def test_the_length_and_the_speech_stay_and_the_insert_has_no_sound(self):
        out = self.lay([{"start": 4.0, "end": 7.0, "file": str(self.red), "from": 0.0, "kind": "video"}])
        self.assertAlmostEqual(probe(out)["duration"], probe(self.base)["duration"], delta=0.12)
        self.assertTrue(probe(out)["has_audio"])
        self.assertGreater(volume(out, 1.2, 2.8), -30)    # the speech of the base is there
        self.assertLess(volume(out, 4.2, 6.8), -60)       # the tone of the insert is not

    def test_the_insert_starts_at_its_own_offset(self):
        two = self.tmp / "два.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=red:s=160x120:r=25:d=6", "-vf",
               "drawbox=x=0:y=0:w=iw:h=ih:color=green:t=fill:enable='gte(t,3)'", "-c:v", "libx264",
               "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(two))
        out = self.lay([{"start": 4.0, "end": 7.0, "file": str(two), "from": 3.0, "kind": "stock"}])
        colour = colour_at(out, 5.0)
        self.assertGreater(colour[1], 80)                 # green: the part from 3 s on, not the red start
        self.assertLess(colour[0], 80)

    def test_a_photo_fills_the_frame_with_a_slow_push_in(self):
        photo = self.tmp / "фото.png"
        ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=200x100", "-frames:v", "1", str(photo))
        out = self.lay([{"start": 4.0, "end": 8.0, "file": str(photo), "from": 0.0, "kind": "photo"}])
        for t in (4.2, 6.0, 7.8):
            colour = colour_at(out, t)
            self.assertGreater(colour[2], 150, "photo missing at {}".format(t))
        self.assertEqual((probe(out)["width"], probe(out)["height"]), (160, 120))
        self.assertAlmostEqual(probe(out)["duration"], 10.0, delta=0.12)

    def test_the_push_in_of_a_photo_is_a_few_percent_not_a_jump(self):
        framed = self.tmp / "рамка.png"
        ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=640x480", "-vf", "drawbox=x=0:y=0:w=iw:h=ih:color=red:t=12",
               "-frames:v", "1", str(framed))
        out = self.lay([{"start": 2.0, "end": 6.0, "file": str(framed), "from": 0.0, "kind": "photo"}])
        self.assertGreater(edge_pixel(out, 2.05)[0], 200)   # the red border still touches the edge when it starts
        self.assertLess(edge_pixel(out, 5.9)[0], 150)       # a few percent later the edge has grown past it
        self.assertGreater(edge_pixel(out, 5.9, x=80)[2], 200)  # and the middle of the frame is still the photo

    def test_an_insert_past_the_end_is_cut_to_the_video(self):
        out = self.lay([{"start": 8.5, "end": 12.5, "file": str(self.red), "from": 0.0, "kind": "video"}])
        self.assertAlmostEqual(probe(out)["duration"], 10.0, delta=0.12)
        self.assertGreater(colour_at(out, 9.5)[0], 180)

    def test_no_inserts_leave_the_video_as_it_is(self):
        self.assertEqual(self.lay([]), self.base)


if __name__ == "__main__":
    unittest.main()
