"""Shared test helpers: repository paths and synthetic media made with ffmpeg."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "aiediting"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
if str(SKILL) not in sys.path:
    sys.path.insert(0, str(SKILL))
# No test asks GitHub for a newer version; tests of that check turn it back on with a fake answer (test_updates.py).
os.environ.setdefault("AIEDITING_NO_UPDATE_CHECK", "1")

HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
needs_ffmpeg = unittest.skipUnless(HAVE_FFMPEG, "ffmpeg/ffprobe not in PATH")


def ffmpeg(*args):
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", *map(str, args)]
    subprocess.run(cmd, check=True)


def _between(spans):
    return "+".join("between(t,{},{})".format(a, b) for a, b in spans)


def make_av(path, tones, duration, size="160x120", rate=50):
    """Video+audio: a 440 Hz tone and a white frame exactly inside `tones`, silence/black elsewhere."""
    on = _between(tones)
    ffmpeg(
        "-f", "lavfi", "-i", "color=c=black:s={}:r={}:d={}".format(size, rate, duration),
        "-f", "lavfi", "-i", "aevalsrc='if({},0.5*sin(2*PI*440*t),0)':s=48000:d={}".format(on, duration),
        "-vf", "drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='{}'".format(on),
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-shortest", str(path),
    )
    return Path(path)


def make_tone(path, duration=6.0, volume=0.05, size="160x120"):
    """testsrc video with a steady sine tone at a low level."""
    ffmpeg(
        "-f", "lavfi", "-i", "testsrc=s={}:r=25:d={}".format(size, duration),
        "-f", "lavfi", "-i", "sine=f=1000:d={}".format(duration),
        "-af", "volume={}".format(volume),
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(path),
    )
    return Path(path)


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="aiediting тест ")
        self.tmp = Path(self._tmp.name)
        # A cleanup, not tearDown: a test's own cleanups (leaving the folder) run first, or Windows refuses to delete it.
        self.addCleanup(self._tmp.cleanup)
