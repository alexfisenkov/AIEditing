"""Full FFmpeg readiness is based on the effective binary's actual filters."""
import os
import sys
import unittest
from unittest import mock

from _support import SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))
from aelib import catalog, checks  # noqa: E402

FILTERS = ["subtitles", "vidstabdetect", "vidstabtransform", "rubberband", "libvmaf"]


class FullFFmpeg(TempDirCase):
    def test_two_and_three_character_filter_flags_are_recognized(self):
        output = "\n".join(["Filters:", " .. subtitles V->V", " T.. vidstabdetect V->V",
                            " ... vidstabtransform V->V", " .SC rubberband A->A",
                            " .. libvmaf VV->V"])
        row = {"check": {"command": [sys.executable, "-c", "print({!r})".format(output)],
                         "required_filters": FILTERS}}
        self.assertTrue(checks.status(row)["ok"])

    def test_filter_name_in_description_does_not_count(self):
        output = " .. subtitles V->V\n .. libvmaf VV->V\nmetadata says vidstabdetect rubberband vidstabtransform"
        row = {"check": {"command": [sys.executable, "-c", "print({!r})".format(output)],
                         "required_filters": FILTERS}}
        got = checks.status(row)
        self.assertFalse(got["ok"])
        self.assertIn("vidstabdetect", got["note"])

    def test_effective_ffmpeg_and_ffprobe_use_explicit_override_pair(self):
        bin_dir = self.tmp / "custom bin"
        bin_dir.mkdir()
        for name in ("ffmpeg", "ffprobe"):
            (bin_dir / name).write_text("")
        with mock.patch.dict(os.environ, {"AIEDITING_FFMPEG": str(bin_dir / "ffmpeg")}, clear=False):
            self.assertEqual(checks.argv_of(["ffmpeg", "-version"])[0], str(bin_dir / "ffmpeg"))
            self.assertEqual(checks.argv_of(["ffprobe", "-version"])[0], str(bin_dir / "ffprobe"))

    def test_full_homebrew_bin_precedes_basic_bin_in_process_path(self):
        full = self.tmp / "ffmpeg-full" / "bin"
        full.mkdir(parents=True)
        with mock.patch.dict(os.environ, {"PATH": "/basic/bin"}), \
                mock.patch.object(checks, "_full_ffmpeg_bins", return_value=[str(full)]), \
                mock.patch.object(checks, "_system_path_entries", return_value=[]):
            checks.refresh_path()
            self.assertEqual(os.environ["PATH"].split(os.pathsep)[0], str(full))


if __name__ == "__main__":
    unittest.main()
