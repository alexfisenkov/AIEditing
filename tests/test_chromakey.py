"""A green-screen request produces real alpha, with audio and the source intact."""
from _support import TempDirCase, ffmpeg, needs_ffmpeg


@needs_ffmpeg
class ChromaKey(TempDirCase):
    def test_green_pixels_become_transparent(self):
        from runtime.media.chromakey import chromakey
        from runtime.media import probe
        import subprocess
        from runtime.media.ffmpeg import tool

        src, out = self.tmp / "green.mp4", self.tmp / "cutout.mov"
        ffmpeg("-f", "lavfi", "-i", "color=c=green:s=64x64:r=10:d=0.5",
               "-f", "lavfi", "-i", "sine=frequency=440:duration=0.5",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(src))
        before = src.read_bytes()
        self.assertEqual(chromakey(src, out, key_color="#008000"), out.resolve())
        self.assertEqual(src.read_bytes(), before)
        self.assertTrue(probe(out)["has_audio"])
        alpha = subprocess.run([tool("ffmpeg"), "-v", "error", "-i", str(out), "-frames:v", "1",
                                "-vf", "alphaextract", "-pix_fmt", "gray", "-f", "rawvideo", "pipe:1"],
                               capture_output=True, check=True).stdout
        self.assertEqual(len(alpha), 64 * 64)
        self.assertLess(max(alpha), 3)
