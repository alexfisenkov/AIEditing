"""The toolbox report distinguishes native steps, composable tools and missing prerequisites."""
import sys
import unittest
import os
from unittest import mock

from _support import SKILL

sys.path.insert(0, str(SKILL / "tools"))


class Capabilities(unittest.TestCase):
    def test_filter_inventory_honours_explicit_ffmpeg_override(self):
        from aelib.capabilities import filters
        from types import SimpleNamespace

        with mock.patch.dict(os.environ, {"AIEDITING_FFMPEG": "/custom/ffmpeg"}), \
                mock.patch("aelib.capabilities.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=" TS crop V->V Crop\n")) as run:
            self.assertEqual(filters(), {"crop"})
        self.assertEqual(run.call_args.args[0][0], "/custom/ffmpeg")

    def test_filters_parse_current_and_legacy_ffmpeg_flags(self):
        from aelib.capabilities import filters
        from types import SimpleNamespace

        listing = "Filters:\n TS afftdn A->A Reduce noise\n TSC lut3d V->V Apply LUT\n .. scale V->V Scale\n"
        with mock.patch("aelib.capabilities.shutil.which", return_value="ffmpeg"), \
                mock.patch("aelib.capabilities.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=listing)):
            self.assertEqual(filters(), {"afftdn", "lut3d", "scale"})

    def test_missing_filter_does_not_claim_the_operation_is_ready(self):
        from aelib.capabilities import inspect_capabilities

        with mock.patch("aelib.capabilities.filters", return_value=set()), \
                mock.patch("aelib.capabilities.status", return_value={"ok": True, "note": "test"}):
            data = inspect_capabilities()
        colour = next(row for row in data["capabilities"] if row["id"] == "colour")
        self.assertFalse(colour["ready"])
        self.assertIn("lut3d", colour["missing_filters"])
        self.assertEqual(data["verification"], "tool-readiness; output must be checked separately")

    def test_registry_covers_editing_families_and_names_execution_mode(self):
        from aelib.capabilities import inspect_capabilities

        with mock.patch("aelib.capabilities.filters", return_value={"lut3d", "eq", "xfade"}), \
                mock.patch("aelib.capabilities.status", return_value={"ok": True, "note": "test"}):
            rows = inspect_capabilities()["capabilities"]
        by_id = {row["id"]: row for row in rows}
        self.assertEqual(by_id["background"]["method"], "native")
        self.assertEqual(by_id["colour"]["method"], "tool-composition")
        for name in ("cuts", "audio", "subtitles", "colour", "stabilization", "multicam", "broll", "background", "graphics", "delivery"):
            self.assertIn(name, by_id)
