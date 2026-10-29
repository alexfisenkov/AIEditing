import os
import unittest
from unittest import mock

from _support import TempDirCase, make_tone, needs_ffmpeg


@needs_ffmpeg
class Probe(TempDirCase):
    def test_passport_of_synthetic_video(self):
        from runtime.media import probe

        src = make_tone(self.tmp / "клип с пробелом.mp4", duration=3.0, size="320x240")
        info = probe(src)
        self.assertAlmostEqual(info["duration"], 3.0, delta=0.1)
        self.assertEqual((info["width"], info["height"]), (320, 240))
        self.assertAlmostEqual(info["fps"], 25.0, places=2)
        self.assertEqual(info["rotation"], 0)
        self.assertTrue(info["has_audio"])
        self.assertTrue(info["has_video"])

    def test_missing_file_is_a_clear_error(self):
        from runtime.media import MediaError, probe

        with self.assertRaises(MediaError) as ctx:
            probe(self.tmp / "нет такого.mp4")
        self.assertIn("нет такого.mp4", str(ctx.exception))


class CodecChoice(unittest.TestCase):
    @mock.patch.dict(os.environ, {"AIEDITING_VCODEC": ""})
    def test_windows_gets_libx264_mac_gets_videotoolbox_when_present(self):
        from runtime.media import codec_chain

        both = {"h264_videotoolbox", "libx264"}
        self.assertEqual(codec_chain("win32", both), ["libx264"])
        self.assertEqual(codec_chain("darwin", both), ["h264_videotoolbox", "libx264"])
        self.assertEqual(codec_chain("darwin", {"libx264"}), ["libx264"])


if __name__ == "__main__":
    unittest.main()
