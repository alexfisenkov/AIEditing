"""The face check of a render: right after every change of the picture the speaker's face is whole inside the speaker's window.

The geometry and the choice of frames are pure; the rendering is a node helper and the detector is YuNet, both stood in for here.
"""
import argparse
import contextlib
import io
import json
import os
import re
import sys
from pathlib import Path
from unittest import mock

from _support import SKILL, TempDirCase

KIT = SKILL / "overlay-kit"
if str(KIT / "tools") not in sys.path:
    sys.path.insert(0, str(KIT / "tools"))

from overlaylib import commands, facecheck, facecmd, facejudge, final, scaffold, vinit  # noqa: E402
from overlaylib.common import ToolError  # noqa: E402

CIRCLE = (1542.0, 682.0, 318.0, 318.0, 159.0, 1.0)  # the layout pip of the long video
BAND = (0.0, 0.0, 1080.0, 880.0, 0.0, 1.0)           # the layout top of a vertical clip
TRACK = [[k * 0.5, 0.5, 0.45, 0.4, 0.0 if k < 12 else 6.0] for k in range(24)]  # one change of the picture at 6.0 s


def face_in(win, share=0.72):
    """A face box centred in a window, `share` of its height."""
    x, y, w, h = win[:4]
    fh = share * h
    fw = 0.78 * fh
    return (x + (w - fw) / 2, y + (h - fh) / 2, fw, fh)


class Geometry(TempDirCase):
    def test_a_face_in_the_middle_of_a_circle_passes(self):
        self.assertIsNone(facejudge.judge([face_in(CIRCLE)], CIRCLE))
        self.assertIsNone(facejudge.judge([face_in(BAND, 0.5)], BAND))

    def test_no_face_in_the_window_is_a_finding(self):
        self.assertEqual(facejudge.judge([], CIRCLE), facejudge.NO_FACE)
        far = (100.0, 100.0, 120.0, 150.0)  # a face on the stage, not in the speaker's circle
        self.assertEqual(facejudge.judge([far], CIRCLE), facejudge.NO_FACE)

    def test_a_face_cut_by_the_edge_is_a_finding(self):
        # what the detector returns on a real frame 0.2 s after a switch with a track smoothed through it: only the visible
        # part of the face, which ends on the rim of the circle
        self.assertEqual(facejudge.judge([(1541.0, 725.0, 137.0, 226.0)], CIRCLE), facejudge.CUT)
        self.assertEqual(facejudge.judge([(1544.0, 750.0, 110.0, 198.0)], CIRCLE), facejudge.CUT)
        bx, by, bw, bh = face_in(BAND, 0.5)
        self.assertEqual(facejudge.judge([(bx, 0.0, bw, bh)], BAND), facejudge.CUT, "a face that starts at the top edge of a band")

    def test_whole_faces_of_real_frames_pass(self):
        self.assertIsNone(facejudge.judge([(1641.0, 701.0, 167.0, 215.0)], CIRCLE))
        self.assertIsNone(facejudge.judge([(1605.0, 718.0, 168.0, 239.0)], CIRCLE))
        ring = (370.0, 1275.0, 340.0, 340.0, 170.0, 1.0)  # ringLow of a vertical clip
        self.assertIsNone(facejudge.judge([(436.0, 1334.0, 179.0, 261.0)], ring))

    def test_a_circle_and_a_box_are_told_apart_by_the_radius(self):
        self.assertTrue(facejudge.is_circle(CIRCLE))
        self.assertFalse(facejudge.is_circle((1168.0, 70.0, 690.0, 900.0, 26.0, 1.0)))
        corner = (1542.0 + 5, 682.0 + 5, 30.0, 30.0)  # inside the square around the circle, outside the circle
        self.assertLess(facejudge.clearance(CIRCLE, corner), 0)
        self.assertGreater(facejudge.clearance((1542.0, 682.0, 318.0, 318.0, 26.0, 1.0), corner), 0, "the same face in a box")

    def test_a_hidden_or_tiny_window_is_not_judged(self):
        self.assertTrue(facejudge.judgeable(CIRCLE))
        self.assertFalse(facejudge.judgeable(CIRCLE[:5] + (0.3,)))
        self.assertFalse(facejudge.judgeable((0, 0, 30, 30, 15, 1)))
        self.assertFalse(facejudge.judgeable(None))

    def test_the_largest_face_inside_decides(self):
        small_cut = (CIRCLE[0] + 250, CIRCLE[1] + 140, 60, 60)
        self.assertIsNone(facejudge.judge([small_cut, face_in(CIRCLE)], CIRCLE))


class Frames(TempDirCase):
    def test_the_long_video_is_looked_at_a_fifth_and_a_whole_second_after_a_change(self):
        self.assertEqual(facecheck.long_frames(TRACK, [], 360), [186, 210])
        self.assertEqual(facecheck.long_frames(TRACK, [], 200), [186], "past the end is not looked at")
        self.assertEqual(facecheck.long_frames([[0, 0.5, 0.45, 0.4, 0.0]], [], 360), [])

    def test_a_clip_is_looked_at_after_the_joint_of_its_spans_on_the_frame_the_picture_changes(self):
        data = {"rate": 1.2, "spans": {"c1": [[4.0, 6.37], [30.0, 32.0]]}}
        self.assertEqual(facecheck.span_edges(data["spans"]["c1"], 1.2), [0, 59, 109])
        self.assertEqual(facecheck.clip_frames([[0, 0.5, 0.45, 0.4, 0.0]], [], data, "c1"), [65, 89])

    def test_a_change_of_the_picture_inside_a_span_lands_on_its_frame_of_the_clip(self):
        data = {"rate": 1.0, "spans": {"c1": [[1.0, 10.0]]}}
        self.assertEqual(facecheck.clip_frames(TRACK, [], data, "c1"), [156, 180])  # second 6 of the file is frame 150 of the clip
        self.assertEqual(facecheck.clip_frames(TRACK, [], {"rate": 1.0, "spans": {"c1": [[7.0, 10.0]]}}, "c1"), [])

    def test_the_seconds_of_a_change_are_the_ones_the_stills_use(self):
        self.assertEqual(facecmd.cut_seconds(TRACK, []), [6.0])
        self.assertEqual(facecmd.cut_frames(TRACK, []), [6.2])


class Detector:
    """Stands in for YuNet: the faces of a frame by its file name."""

    def __init__(self, faces):
        self.by_frame = faces
        self.seen = []

    def faces(self, path, win):
        frame = int(Path(path).stem[2:])
        self.seen.append(frame)
        return self.by_frame.get(frame, [])


class Folder(TempDirCase):
    def write(self, frames, boxes):
        out = self.tmp / "check"
        out.mkdir()
        for f in frames:
            (out / "f-{:03d}.jpeg".format(f)).write_bytes(b"x")
        (out / "boxes.json").write_text(json.dumps({"id": "Full", "fps": 30, "frames": frames, "boxes": boxes}), encoding="utf-8")
        return out

    def test_a_frame_with_the_edge_of_the_picture_in_the_circle_is_named_with_its_second_and_file(self):
        out = self.write([186, 210], {"186": list(CIRCLE), "210": list(CIRCLE)})
        found, judged = facecheck.judge_folder(out, Detector({210: [face_in(CIRCLE)]}))
        self.assertEqual(found, ["6.20 с (f-186.jpeg): НЕТ ЛИЦА В РАМКЕ"])
        self.assertEqual(judged, 2)

    def test_a_hidden_window_is_skipped_and_a_missing_frame_stops_the_check(self):
        out = self.write([186], {"186": list(CIRCLE[:5]) + [0.0]})
        detector = Detector({})
        self.assertEqual(facecheck.judge_folder(out, detector), ([], 0))
        self.assertEqual(detector.seen, [])
        (out / "f-186.jpeg").unlink()
        with self.assertRaises(ToolError):
            facecheck.judge_folder(out, detector)

    def test_a_frame_without_a_reported_window_is_a_finding_not_a_pass(self):
        out = self.write([186, 210], {"186": list(CIRCLE)})
        found, judged = facecheck.judge_folder(out, Detector({186: [face_in(CIRCLE)]}))
        self.assertEqual(found, ["7.00 с (f-210.jpeg): " + facecheck.NO_BOX])
        self.assertEqual(judged, 1)


def folder(root, presenter="kit/Presenter.tsx", track=TRACK):
    """A working folder with the template's presenters, or with `presenter` of the earlier kit."""
    work = root / "work"
    for sub in ("src/data", "src/kit", "src/vertical", "public/clips"):
        (work / sub).mkdir(parents=True)
    (work / "src" / "Root.tsx").write_text("//", encoding="utf-8")
    (work / "src" / "data" / "face.json").write_text(json.dumps(track), encoding="utf-8")
    for rel in ("kit/Presenter.tsx", "vertical/VPresenter.tsx"):
        text = (KIT / "template" / "src" / rel).read_text(encoding="utf-8")
        if rel == presenter:  # 0.3.2: reads the track by pieces, reports no window
            text = text.replace("useSpeakerBox(", "noProbe(")
        (work / "src" / rel).write_text(text, encoding="utf-8")
    return work


class Unchecked(TempDirCase):
    def test_every_reason_not_to_judge_is_named(self):
        with mock.patch.object(facejudge, "ready", return_value=None):
            self.assertIsNone(facecheck.why_not(folder(self.tmp, presenter=""), "src/kit/Presenter.tsx"))
        cases = [
            (dict(), "нет OpenCV", "src/kit/Presenter.tsx"),
            (dict(presenter="kit/Presenter.tsx"), "speakerBox.ts", "src/kit/Presenter.tsx"),
            (dict(presenter="vertical/VPresenter.tsx"), "--renew", "src/vertical/VPresenter.tsx"),
            (dict(presenter="", track=[[0.0, 0.5, 0.45, 0.4]]), "трека лица нет", "src/kit/Presenter.tsx"),
            (dict(presenter="", track=[p[:4] for p in TRACK]), "прежнего образца", "src/kit/Presenter.tsx"),
        ]
        for i, (kw, said, reader) in enumerate(cases):
            root = self.tmp / str(i)
            root.mkdir()
            ready = "нет OpenCV (cv2) в этом Python" if not kw else None
            with mock.patch.object(facejudge, "ready", return_value=ready):
                self.assertIn(said, facecheck.why_not(folder(root, **kw), reader) or "", said)

    def test_a_presenter_without_the_window_report_is_named_by_the_face_command(self):
        work = folder(self.tmp)
        self.assertEqual(facecmd.stale_readers(work), ["src/kit/Presenter.tsx"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            facecmd.warn_stale(work)
        self.assertIn("не сообщает рамку спикера", out.getvalue())
        self.assertIn("speakerBox.ts", out.getvalue())

    def test_an_old_folder_gets_the_new_kit_modules_and_keeps_its_own(self):
        work = folder(self.tmp)
        (work / "src" / "kit" / "faceTrack.ts").write_text("// mine\n", encoding="utf-8")
        self.assertEqual(scaffold.add_kit_modules(work), ["src/kit/speakerBox.ts: добавлен"])
        self.assertEqual((work / "src" / "kit" / "faceTrack.ts").read_text(encoding="utf-8"), "// mine\n")
        self.assertEqual(scaffold.add_kit_modules(work), [])


class Gates(TempDirCase):
    def test_a_finding_or_an_unchecked_render_stops_a_release_unless_accepted(self):
        for found, unchecked in ((["6.20 с (f-186.jpeg): НЕТ ЛИЦА В РАМКЕ"], None), ([], "нет OpenCV (cv2) в этом Python")):
            with mock.patch.object(facecheck, "check_long", return_value=(found, unchecked)):
                with self.assertRaises(ToolError) as said:
                    final.face_gate(self.tmp, None)
                self.assertIn("--face-accepted", str(said.exception))
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    final.face_gate(self.tmp, "спикер отвернулся, кадры просмотрены")
                self.assertIn("принято человеком", out.getvalue())
        with mock.patch.object(facecheck, "check_long", return_value=([], None)):
            final.face_gate(self.tmp, None)

    def test_a_blank_reason_is_refused(self):
        with self.assertRaises(ToolError):
            facecheck.accepted_reason("   ")
        self.assertIsNone(facecheck.accepted_reason(None))
        self.assertEqual(facecheck.accepted_reason(" смотрел кадры "), "смотрел кадры")

    def test_draft_fails_on_an_unchecked_render_too(self):
        work = folder(self.tmp, presenter="")
        ns = argparse.Namespace(work=str(work))
        no_face = facecheck.NO_TRACK + ": в видео не нашлось лица"
        for result, code in ((([], None), 0), ((["x"], None), 1), (([], "нет OpenCV"), 1), (([], no_face), 0)):
            with mock.patch.object(commands.remotion, "ready"), mock.patch.object(commands.remotion, "typecheck"), \
                    mock.patch.object(commands.remotion, "render"), mock.patch.object(facecheck, "check_long", return_value=result), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(commands.cmd_draft(ns), code, result)

    def test_face_check_refuses_with_its_real_reason_instead_of_passing(self):
        work = folder(self.tmp, presenter="")
        ns = argparse.Namespace(work=str(work), rebuild=False, video=None, frames=False, check=True)
        with mock.patch.object(facecmd.remotion, "ready"), mock.patch.object(facecheck, "check_long", return_value=([], "трек прежнего образца")), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ToolError) as said:
                facecmd.run_face(ns)
        self.assertIn("трек прежнего образца", str(said.exception))
        self.assertNotIn("OpenCV", str(said.exception))
        with mock.patch.object(facecmd.remotion, "ready"), mock.patch.object(facecheck, "check_long", return_value=(["x"], None)), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(facecmd.run_face(ns), 1)
        (work / "src" / "data" / "face.json").write_text(json.dumps([[0.0, 0.5, 0.45, 0.4]]), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ToolError):
                facecmd.run_face(ns)

    def test_a_reused_render_older_than_the_scenes_is_refused(self):
        work = folder(self.tmp, presenter="")
        render = work / "out" / "render.mp4"
        render.parent.mkdir()
        render.write_bytes(b"x")
        old = render.stat().st_mtime - 100
        for p in (work / "src").rglob("*"):
            if p.is_file():
                os.utime(str(p), (old, old))
        final.stale_render(work, render)
        (work / "src" / "data" / "all-layouts.ts").write_text("// rewritten by every command\n", encoding="utf-8")
        final.stale_render(work, render)
        (work / "src" / "vertical" / "index-clips.ts").write_text("// rewritten by every vertical command\n", encoding="utf-8")
        final.stale_render(work, render)  # the clips' set is not read by the long video's composition
        (work / "src" / "data" / "layouts-a.ts").write_text("// a layout changed\n", encoding="utf-8")
        with self.assertRaises(ToolError) as said:
            final.stale_render(work, render)
        self.assertIn("layouts-a.ts", str(said.exception))

    def test_a_detector_that_does_not_load_is_a_reason_not_a_traceback(self):
        work = folder(self.tmp, presenter="")
        with mock.patch.object(facejudge, "ready", return_value=None), \
                mock.patch.object(facejudge, "Detector", side_effect=RuntimeError("can't open model")):
            detector, missing = facejudge.detector()
            self.assertEqual(facecheck.check_clip(work, self.tmp, {}, "c1", (None, missing)), ([], missing))
        self.assertIsNone(detector)
        self.assertIn("модель лица не загрузилась", missing)

    def test_another_check_taking_the_place_leaves_this_runs_frames_where_they_are(self):
        run_dir = self.tmp / "run-1"
        run_dir.mkdir()
        final_dir = self.tmp / "Full"
        with mock.patch.object(Path, "rename", side_effect=OSError(66, "Directory not empty")):
            self.assertEqual(facecheck._publish(run_dir, final_dir), run_dir)
        self.assertTrue(run_dir.is_dir())
        self.assertEqual(facecheck._publish(run_dir, final_dir), final_dir)
        self.assertFalse(run_dir.exists())

    def test_the_helper_travels_with_the_vertical_set_and_the_presenters_report_their_window(self):
        work = self.tmp / "work"
        work.mkdir()
        vinit.install_helper(work)
        self.assertTrue((work / "tools-local" / "face-frames.mjs").is_file())
        for rel in ("kit/Presenter.tsx", "vertical/VPresenter.tsx"):
            self.assertIn("useSpeakerBox(", (KIT / "template" / "src" / rel).read_text(encoding="utf-8"), rel)
        probe = (KIT / "template" / "src" / "kit" / "speakerBox.ts").read_text(encoding="utf-8")
        self.assertIn("faceProbe", probe, "an ordinary render prints nothing")
        helper = (KIT / "tools" / "face-frames.mjs").read_text(encoding="utf-8")
        self.assertIn("FACEBOX", helper)
        self.assertIsNone(re.search(r"rmSync\([^)]*recursive", helper), "the helper removes only its own frames, never a folder")
