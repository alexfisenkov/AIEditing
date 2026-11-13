"""`overlay.py peaks`: every sound cue of the scenes against the nearest peak of movement in a draft, shift in frames."""
import contextlib
import io
import json
import sys

from _support import SKILL, TempDirCase, ffmpeg, needs_ffmpeg

KIT_TOOLS = SKILL / "overlay-kit" / "tools"
if str(KIT_TOOLS) not in sys.path:
    sys.path.insert(0, str(KIT_TOOLS))

import overlay  # noqa: E402
from overlaylib import peaks  # noqa: E402

SCENE = """import { Cue } from "../kit/Sound";
export const scenes = [{ from: 1.0, to: 2.0, C: X }];
export const cues: Cue[] = [
  [1.42, "pop-soft"], // a small appearance
  { role: "hit", at: 1.5 },
  { at: 2.6, role: "hit", n: 0 },
];
"""


def draft(path):
    """3 s of black; a white box appears at 1.5 s and stays: the only sharp change of the picture."""
    ffmpeg("-f", "lavfi", "-i", "color=c=black:s=320x180:r=30:d=3", "-vf",
           "drawbox=x=100:y=50:w=120:h=80:color=white:t=fill:enable='gte(t,1.5)'",
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(path))


@needs_ffmpeg
class Peaks(TempDirCase):
    def setUp(self):
        super().setUp()
        self.work = self.tmp / "work"
        for sub in ("src/scenes", "src/data", "out"):
            (self.work / sub).mkdir(parents=True)
        (self.work / "src" / "Root.tsx").write_text("// root\n", encoding="utf-8")
        (self.work / "src" / "scenes" / "seg-a.tsx").write_text(SCENE, encoding="utf-8")
        (self.work / "src" / "data" / "time-map.json").write_text(json.dumps({"rows": []}), encoding="utf-8")
        (self.work / "src" / "data" / "sfx.json").write_text(json.dumps({
            "files": {"pop-soft": "sfx/pop-soft.wav"}, "music": None,
            "roles": {"pop": [{"file": "sfx/pop-soft.wav", "dur_ms": 90, "peak_ms": 20, "level_db": -3.0}],
                      "hit": [{"file": "sfx/hit/hit-01.ogg", "dur_ms": 500, "peak_ms": 40, "level_db": -3.0}]}}), encoding="utf-8")
        self.video = self.work / "out" / "draft.mp4"
        draft(self.video)

    def test_the_movement_peaks_where_the_picture_changes(self):
        found = peaks.motion_peaks(self.video)
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0], 1.5, delta=0.034)

    def test_each_cue_gets_its_nearest_peak_and_the_shift_in_frames(self):
        rows = peaks.report(self.work, self.video)
        self.assertEqual([r["sound"] for r in rows], ["pop-soft", "hit", "hit"])
        # pop-soft starts at 1.42 and peaks 20 ms later: 1.44 → the picture changes at 1.50: +2 frames (0.06 s at 30 fps)
        self.assertAlmostEqual(rows[0]["peak"], 1.44, places=2)
        self.assertEqual(rows[0]["shift"], 2)
        # a cue by role already puts its peak on `at`
        self.assertAlmostEqual(rows[1]["peak"], 1.5, places=2)
        self.assertEqual(rows[1]["shift"], 0)
        # nothing moves near 2.6 s
        self.assertIsNone(rows[2]["motion"])
        self.assertIsNone(rows[2]["shift"])

    def test_the_command_prints_a_line_per_sound(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = overlay.main(["peaks", str(self.work), str(self.video)])
        self.assertEqual(code, 0, err.getvalue())
        text = out.getvalue()
        self.assertIn("pop-soft", text)
        self.assertIn("+2 кадр", text)
        self.assertIn("пика движения рядом нет", text)
