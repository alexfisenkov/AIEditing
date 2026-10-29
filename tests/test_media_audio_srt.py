import re
import subprocess
import unittest

from _support import TempDirCase, make_tone, needs_ffmpeg


def integrated_lufs(path):
    """Measured with ffmpeg's ebur128 meter, independent of the loudnorm filter under test."""
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path), "-vn",
           "-af", "ebur128", "-f", "null", "-"]
    err = subprocess.run(cmd, stderr=subprocess.PIPE, encoding="utf-8", errors="replace").stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])


@needs_ffmpeg
class Loudness(TempDirCase):
    def test_brings_quiet_clip_to_target(self):
        from runtime.media import loudnorm, probe

        src = make_tone(self.tmp / "тихо.mp4", duration=6.0, volume=0.02)
        self.assertLess(integrated_lufs(src), -30)
        for target in (-16, -20):
            out = loudnorm(src, self.tmp / "громкость {}.mp4".format(target), lufs=target)
            self.assertAlmostEqual(integrated_lufs(out), target, delta=1.0)
            self.assertTrue(probe(out)["has_video"])


def word(text, start, end, kind="word"):
    return {"text": text, "start": start, "end": end, "type": kind}


SRT_BLOCK = re.compile(
    r"(\d+)\n(\d\d:\d\d:\d\d,\d\d\d) --> (\d\d:\d\d:\d\d,\d\d\d)\n(.+?)(?:\n\n|\n?$)", re.S)


def to_s(stamp):
    h, m, rest = stamp.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


class Subtitles(TempDirCase):
    TRANSCRIPT = {"language": "ru", "provider": "command", "words": [
        word("Сегодня", 0.0, 0.5), word(" ", 0.5, 0.5, "spacing"), word("ставим", 0.5, 0.9),
        word("э-э", 0.9, 1.3, "filler"), word("клод", 1.3, 1.6), word("код.", 1.6, 2.0),
        word("Потом", 4.0, 4.4), word("открываем", 4.4, 5.0), word("ремоушен", 5.0, 5.6),
    ]}

    def test_writes_valid_srt_and_reports_glossary_fixes(self):
        from runtime.media import write_srt

        out = self.tmp / "субтитры.srt"
        fixes = write_srt(self.TRANSCRIPT, out, {"клод код": "Claude Code", "ремоушен": "Remotion"})
        text = out.read_text(encoding="utf-8")
        blocks = SRT_BLOCK.findall(text)
        self.assertGreaterEqual(len(blocks), 2)
        self.assertEqual([int(b[0]) for b in blocks], list(range(1, len(blocks) + 1)))
        ends = 0.0
        for _i, start, end, _t in blocks:
            self.assertLessEqual(ends, to_s(start))
            self.assertLess(to_s(start), to_s(end))
            ends = to_s(end)
        self.assertIn("Claude Code", text)
        self.assertIn("Remotion", text)
        self.assertNotIn("э-э", text)
        self.assertEqual(sorted((f["from"], f["to"]) for f in fixes),
                         [("клод код", "Claude Code"), ("ремоушен", "Remotion")])
        self.assertEqual(blocks[0][1], "00:00:00,000")


if __name__ == "__main__":
    unittest.main()
