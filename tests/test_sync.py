"""Finding how far apart two recordings of the same sound started: tone bursts of an irregular rhythm, shifted."""
import unittest

from _support import TempDirCase, ffmpeg, needs_ffmpeg

# Bursts of an irregular rhythm: no shift of it lines up with itself except the true one.
RHYTHM = [(0.5, 0.9), (1.3, 2.4), (2.6, 2.8), (3.5, 4.6), (5.0, 5.2), (5.9, 7.3), (7.6, 7.8), (8.4, 9.9),
          (10.5, 10.7), (11.2, 12.6), (13.4, 13.6), (14.1, 15.8)]
SECONDS = 16.0
FRAME = 1 / 25.0


def bursts_file(path, tones, duration, freq=440, amp=0.5, video=None):
    """Sound (and, with `video` = a colour, a picture of that colour) with a `freq` Hz tone inside `tones` only."""
    on = "+".join("between(t,{:.3f},{:.3f})".format(a, b) for a, b in tones if b > 0) or "0"
    args = []
    if video:
        args += ["-f", "lavfi", "-i", "color=c={}:s=160x120:r=25:d={}".format(video, duration)]
    args += ["-f", "lavfi", "-i", "aevalsrc='if({},{}*sin(2*PI*{}*t),0)':s=48000:d={}".format(on, amp, freq, duration)]
    if video:
        args += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest"]
    ffmpeg(*args, str(path))
    return path


def shifted(tones, started_later):
    """The same sound as heard by a recorder switched on `started_later` s after the reference."""
    return [(max(0.0, a - started_later), b - started_later) for a, b in tones if b - started_later > 0]


@needs_ffmpeg
class Offset(TempDirCase):
    def setUp(self):
        super().setUp()
        self.ref = bursts_file(self.tmp / "камера 1.wav", RHYTHM, SECONDS)

    def test_a_recorder_switched_on_later(self):
        from runtime.media.sync import offset

        other = bursts_file(self.tmp / "рекордер.wav", shifted(RHYTHM, 1.36), SECONDS - 1.36, freq=900, amp=0.2)
        self.assertAlmostEqual(offset(self.ref, other), 1.36, delta=FRAME)

    def test_a_camera_switched_on_earlier(self):
        from runtime.media.sync import offset

        other = bursts_file(self.tmp / "камера 2.mp4", shifted(RHYTHM, -2.72), SECONDS + 2.72, freq=600, video="blue")
        self.assertAlmostEqual(offset(self.ref, other), -2.72, delta=FRAME)

    def test_silence_says_so(self):
        from runtime.media import MediaError
        from runtime.media.sync import offset

        quiet = bursts_file(self.tmp / "тишина.wav", [], SECONDS)
        with self.assertRaises(MediaError):
            offset(self.ref, quiet)


@needs_ffmpeg
class Envelope(TempDirCase):
    def test_the_quietest_moment_of_a_window(self):
        from runtime.media.sync import envelope, quietest

        path = bursts_file(self.tmp / "звук.wav", [(0.0, 1.0), (1.12, 2.0)], 2.0)
        env = envelope(path)
        self.assertAlmostEqual(quietest(env, 0.95, 1.2), 1.06, delta=0.04)  # the 120 ms hole between the bursts


if __name__ == "__main__":
    unittest.main()
