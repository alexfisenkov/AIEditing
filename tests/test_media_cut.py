"""Pause removal on a synthetic clip: a tone with a white frame marks 'speech', silence marks pauses."""
import subprocess
import unittest

from _support import TempDirCase, make_av, make_tone, needs_ffmpeg

# Tones (speech) at known times inside a 9 s clip; 7.1–7.4 is a 0.3 s pause, shorter than the 0.5 s gap.
TONES = [(0.6, 1.6), (3.1, 3.9), (5.9, 7.1), (7.4, 7.9)]
DURATION = 9.0
# Hand-worked: pauses >= 0.5 s go, every speech run keeps 0.12 s on each side.
EXPECTED_SPANS = [(0.48, 1.72), (2.98, 4.02), (5.78, 8.02)]


def white_onsets(path):
    """Times where the frame turns white, read with ffmpeg's signalstats."""
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path), "-vf",
           "signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-an", "-f", "null", "-"]
    err = subprocess.run(cmd, stderr=subprocess.PIPE, encoding="utf-8", errors="replace").stderr
    onsets, t, was_white = [], None, False
    for line in err.splitlines():
        if "pts_time:" in line:
            t = float(line.split("pts_time:")[1].split()[0])
        elif "YAVG=" in line:
            white = float(line.split("YAVG=")[1]) > 128
            if white and not was_white:
                onsets.append(t)
            was_white = white
    return onsets


@needs_ffmpeg
class CutPauses(TempDirCase):
    def setUp(self):
        super().setUp()
        self.src = make_av(self.tmp / "исходник.mp4", TONES, DURATION)

    def test_speech_spans_find_speech_with_margin(self):
        from runtime.media import speech_spans

        spans = speech_spans(self.src, gap=0.5, pad=0.12, db=-30)
        self.assertEqual(len(spans), len(EXPECTED_SPANS), spans)
        for (a, b), (ea, eb) in zip(spans, EXPECTED_SPANS):
            self.assertAlmostEqual(a, ea, delta=0.05)
            self.assertAlmostEqual(b, eb, delta=0.05)

    def test_cut_shortens_keeps_every_word_and_stays_in_sync(self):
        from runtime.media import cut_spans, drift_ms, probe, speech_spans

        out = cut_spans(self.src, speech_spans(self.src), self.tmp / "склейка.mp4")
        kept = sum(b - a for a, b in EXPECTED_SPANS)
        self.assertAlmostEqual(probe(out)["duration"], kept, delta=0.1)
        # Every tone survives whole: same lengths, in order, nothing clipped.
        tones_out = speech_spans(out, gap=0.1, pad=0.0)
        self.assertEqual(len(tones_out), len(TONES), tones_out)
        for (a, b), (ta, tb) in zip(tones_out, TONES):
            self.assertAlmostEqual(b - a, tb - ta, delta=0.06)
        # Picture and sound still start together after every splice.
        flashes = white_onsets(out)
        self.assertEqual(len(flashes), len(TONES), flashes)
        for flash, (a, _b) in zip(flashes, tones_out):
            self.assertLess(abs(flash - a) * 1000, 40)
        self.assertLess(drift_ms(out), 40)


def pcm(path, tmp):
    """The first audio stream as mono 48 kHz floats in −1…1."""
    import array

    raw = tmp / "звук.raw"
    subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-i", str(path), "-vn", "-ac", "1",
                    "-ar", "48000", "-f", "s16le", "-c:a", "pcm_s16le", str(raw)], check=True)
    samples = array.array("h")
    samples.frombytes(raw.read_bytes())
    return [s / 32768.0 for s in samples]


@needs_ffmpeg
class NoClickOnSeams(TempDirCase):
    """A 250 Hz sine cut where it is at its crest and joined where it is at its trough: a raw splice jumps by the
    whole swing (a click); a short fade on each side of the seam takes the jump away and keeps the length."""

    def test_seam_of_a_broken_sine_does_not_jump(self):
        from _support import ffmpeg
        from runtime.media import cut_spans, probe

        src = self.tmp / "синус.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=black:s=160x120:r=25:d=4", "-f", "lavfi", "-i",
               "aevalsrc='0.5*sin(2*PI*250*t)':s=48000:d=4", "-c:v", "libx264", "-preset", "ultrafast",
               "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-shortest", str(src.with_suffix(".mov")))
        src = src.with_suffix(".mov")
        # 1.001 s: crest (250 × 1.001 = 250.25 turns); 2.003 s: trough (500.75 turns). By hand: a jump of 1.0 at the seam.
        out = cut_spans(src, [(0.0, 1.001), (2.003, 3.5)], self.tmp / "склейка.mp4")
        self.assertAlmostEqual(probe(out)["duration"], 1.001 + 1.497, delta=0.04)  # not longer or shorter than a frame
        x = pcm(out, self.tmp)
        steady = 0.5 * 2 * 3.14159 * 250 / 48000  # the largest step of the sine itself, 0.016
        near = x[int(0.95 * 48000):int(1.05 * 48000)]
        jump = max(abs(b - a) for a, b in zip(near, near[1:]))
        self.assertLess(jump, 4 * steady, "a click at the seam: {:.3f}".format(jump))


@needs_ffmpeg
class ManySplices(TempDirCase):
    def test_hundreds_of_spans_fit_on_any_command_line(self):
        from runtime.media import cut_spans, drift_ms, probe

        src = make_tone(self.tmp / "длинный.mp4", duration=12.0)
        spans = [(i * 0.08, i * 0.08 + 0.04) for i in range(150)]
        out = cut_spans(src, spans, self.tmp / "нарезка.mp4")
        self.assertAlmostEqual(probe(out)["duration"], 150 * 0.04, delta=0.1)
        self.assertLess(drift_ms(out), 40)


if __name__ == "__main__":
    unittest.main()
