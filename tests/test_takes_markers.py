"""Clean speech and edits by markers: markers read by the file's own arithmetic, a cut moves no scene, the camera has no steps, the format builds."""
import json
import re
import sys
import unittest
from pathlib import Path

from _support import SKILL, TempDirCase

KIT = SKILL / "overlay-kit"
if str(KIT / "tools") not in sys.path:
    sys.path.insert(0, str(KIT / "tools"))

import markers  # noqa: E402
import recut  # noqa: E402

FCPXML = """<?xml version="1.0"?><fcpxml version="1.14"><project><sequence format="r1" duration="100s"><spine>
<asset-clip offset="10s" start="5s" duration="90s"><marker start="7s" value="Резко с этого кадра"/><marker start="6s" value=""/></asset-clip>
</spine></sequence></project></fcpxml>"""


class Markers(TempDirCase):
    def test_time_is_offset_plus_start_minus_clip_start_in_order(self):
        path = Path(self.tmp) / "Info.fcpxml"
        path.write_text(FCPXML, encoding="utf-8")
        got, length = markers.read_markers(path)
        self.assertEqual(length, 100.0)
        self.assertEqual([m["t"] for m in got], [11.0, 12.0])
        self.assertEqual(got[1]["text"], "Резко с этого кадра")


class Recut(unittest.TestCase):
    PIECES = [
        {"from": 0.0, "to": 10.0, "c": "A", "a": 100.0, "b": 110.0, "clip": 0},
        {"from": 10.0, "to": 20.0, "c": "A", "a": 200.0, "b": 210.0, "clip": 1},
    ]

    def test_a_cut_shortens_the_video_and_old_seconds_stay_addressable(self):
        new, meta = recut.edit_pieces(self.PIECES, [[4.0, 6.0]], [], [], [], 1.0)
        self.assertEqual(meta["duration"], 18.0)
        self.assertEqual([(p["a"], p["b"]) for p in new], [(100.0, 104.0), (106.0, 110.0), (200.0, 210.0)])
        self.assertEqual(meta["rows"][1][:4], [4.0, 8.0, 6.0, 10.0])

    def test_a_longer_end_adds_time_and_holds_the_scene(self):
        new, meta = recut.edit_pieces(self.PIECES, [], [["A", 110.0, 110.5]], [], [], 1.0)
        self.assertEqual(new[0]["b"], 110.5)
        self.assertEqual(meta["rows"][0], [0.0, 10.5, 0.0, 10.0, 0.0])
        self.assertEqual(meta["rows"][1][0], 10.5)

    def test_an_earlier_start_leads_and_a_later_start_skips(self):
        _, earlier = recut.edit_pieces(self.PIECES, [], [], [["A", 200.0, 199.5]], [], 1.0)
        self.assertEqual(earlier["rows"][1][4], 0.5)
        _, later = recut.edit_pieces(self.PIECES, [], [], [["A", 200.0, 200.5]], [], 1.0)
        self.assertEqual(later["rows"][1][2], 10.5)

    def test_an_edge_that_is_not_a_piece_edge_is_refused(self):
        with self.assertRaises(SystemExit):
            recut.edit_pieces(self.PIECES, [], [["A", 105.0, 106.0]], [], [], 1.0)

    def test_a_mute_lands_in_new_time(self):
        _, meta = recut.edit_pieces(self.PIECES, [[1.0, 2.0]], [], [], [[5.0, 5.5]], 1.0)
        self.assertEqual(meta["mute"], [[4.0, 4.5]])


class Template(unittest.TestCase):
    def test_the_camera_reads_no_nearest_point(self):
        text = (KIT / "template/src/kit/Presenter.tsx").read_text(encoding="utf-8")
        self.assertNotIn("Math.floor(t * 2)", text)
        self.assertIn("spline", text)

    def test_an_empty_map_means_no_edits(self):
        self.assertEqual(json.loads((KIT / "template/src/data/time-map.json").read_text(encoding="utf-8")), {"rows": []})
        self.assertRegex((KIT / "template/src/kit/time.ts").read_text(encoding="utf-8"), re.compile(r"if \(!ROWS\.length\) return n;"))


class Format(TempDirCase):
    def test_the_format_is_offered_and_its_skill_has_the_method(self):
        from aelib import skillmd
        from aelib.formats import parse_answer
        from aelib.profiles import new_profile

        fmt = parse_answer("ютуб")[0]
        self.assertEqual((fmt["skill"], fmt["preset"]), ("монтаж-ютуб", "youtube-graphics"))
        profile = new_profile(fmt)
        self.assertIn("graphics", profile["steps"])
        self.assertTrue(skillmd.METHOD_IF["takes.md"](profile))
        self.assertIn("takes-and-markers.md", skillmd._method(profile))

    def test_a_whole_recording_format_does_not_read_about_cuts(self):
        from aelib import skillmd
        from aelib.formats import parse_answer
        from aelib.profiles import new_profile

        self.assertFalse(skillmd.METHOD_IF["takes.md"](new_profile(parse_answer("наложения")[0])))


if __name__ == "__main__":
    unittest.main()
