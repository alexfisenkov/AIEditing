import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import _support  # noqa: F401  (puts the skill on sys.path)


def probe_streams(path):
    raw = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(raw)


@unittest.skipUnless(shutil.which("ffmpeg"), "нет ffmpeg")
class Deliver(unittest.TestCase):
    def source(self, folder, audio=True):
        src = Path(folder) / "вход файл.mp4"
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=2"]
        if audio:
            cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=2:sample_rate=44100", "-shortest"]
        subprocess.run(cmd + [str(src)], check=True)
        return src

    def test_the_lesson_preset(self):
        from runtime.media import deliver

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "выпуск.mp4"
            deliver(self.source(tmp), out, {"codec": "hevc", "kbps": 1700, "audio_kbps": 128})
            info = probe_streams(out)
        video = next(s for s in info["streams"] if s["codec_type"] == "video")
        audio = next(s for s in info["streams"] if s["codec_type"] == "audio")
        self.assertEqual((video["codec_name"], video["codec_tag_string"], video["pix_fmt"]), ("hevc", "hvc1", "yuv420p"))
        self.assertEqual(video["profile"], "Main")
        self.assertEqual(video["color_space"], "bt709")
        self.assertEqual((audio["codec_name"], audio["sample_rate"], audio["channels"]), ("aac", "48000", 2))
        self.assertAlmostEqual(float(info["format"]["duration"]), 2.0, delta=0.1)

    def test_a_video_without_sound(self):
        from runtime.media import deliver

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "выпуск.mp4"
            deliver(self.source(tmp, audio=False), out, {"kbps": 500})
            kinds = [s["codec_type"] for s in probe_streams(out)["streams"]]
        self.assertEqual(kinds, ["video"])

    def test_no_encoder_is_a_clear_error(self):
        from runtime.media import delivery

        self.assertEqual(delivery._chain(available=set()), [])
        self.assertEqual(delivery._chain(available={"libx265", "hevc_videotoolbox"}), ["libx265", "hevc_videotoolbox"])


if __name__ == "__main__":
    unittest.main()
