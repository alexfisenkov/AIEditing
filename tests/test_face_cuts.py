"""The speaker's frame after a cut: the face track is smoothed inside a piece of the picture and never through a cut.

A track smoothed through a scene change glides from the old face to the new one for seconds, and the frame cuts the face.
`prepare` finds the cuts (overlaylib/facecuts.py), the kit reads the track by pieces (template/src/kit/faceTrack.ts).
"""
import argparse
import contextlib
import io
import json
import shutil
import subprocess
import sys
import unittest
from unittest import mock

from _support import SKILL, TempDirCase

KIT = SKILL / "overlay-kit"
if str(KIT / "tools") not in sys.path:
    sys.path.insert(0, str(KIT / "tools"))

from overlaylib import face, facecmd, facecuts, vinit, vmap  # noqa: E402
from overlaylib.common import ToolError  # noqa: E402

FACE_TRACK = KIT / "template" / "src" / "kit" / "faceTrack.ts"
SPAN_TIME = KIT / "template" / "src" / "vertical" / "spanTime.ts"
CAMERA = (0.5, 0.45, 0.4)    # the speaker over the whole frame
CIRCLE = (0.89, 0.8, 0.1)    # the speaker as a small circle over a screen recording
AVATAR = (0.2, 0.3, 0.05)    # a small face on the shared screen
STEP = 15                    # frames between two samples at 30 fps
AFTER = 0.2                  # seconds after a cut by which the frame must be on the new face


def recording(shots, length):
    """look(frame, near) of a synthetic recording: `shots` is [(first frame, what)], where `what` is a face, None,
    a list of faces on screen together, or a callable(frame) that gives any of these."""
    def look(frame, near=None):
        shown = [what for first, what in shots if first <= frame][-1]
        shown = shown(frame) if callable(shown) else shown
        return facecuts.pick(shown, near) if isinstance(shown, list) else shown
    return look, length


def sample(look, length):
    """What face.py does with a video: a point per half second, holes filled, blips dropped, cuts found, smoothed by pieces."""
    points, last = [], None
    for k, frame in enumerate(range(0, length, STEP)):
        found = look(frame, last)
        points.append([k * 0.5] + (list(found) if found else [None, None, None]))
        last = found or last
    assert face._fill(points)
    facecuts.drop_blips(points)
    cuts = facecuts.find_cuts(points, STEP, look)
    return facecuts.smooth(points, facecuts.pieces(len(points), STEP, 0.5 / STEP, cuts)), cuts


class Cuts(unittest.TestCase):
    def test_a_scene_change_is_found_to_the_frame(self):
        track, cuts = sample(*recording([(0, CAMERA), (307, CIRCLE)], 900))
        self.assertEqual(cuts, [307])
        self.assertEqual(sorted({p[4] for p in track}), [0.0, round(307 / 30, 4)])

    def test_the_track_does_not_glide_through_the_cut(self):
        track, _ = sample(*recording([(0, CAMERA), (307, CIRCLE)], 900))
        before = [p for p in track if p[0] < 307 / 30]
        after = [p for p in track if p[0] >= 307 / 30]
        for p in before:
            self.assertEqual(p[1:4], list(CAMERA), p)
        for p in after:
            self.assertEqual(p[1:4], list(CIRCLE), p)

    def test_a_head_that_moves_fast_is_not_a_cut(self):
        def lean(frame):  # half a face height to the side within 15 frames, frame by frame
            return (0.5 + 0.11 * min(1.0, max(0.0, (frame - 300) / 15)), 0.45, 0.4)
        track, cuts = sample(*recording([(0, lean)], 900))
        self.assertEqual(cuts, [])
        self.assertEqual({p[4] for p in track}, {0.0})

    def test_a_face_that_comes_back_elsewhere_after_a_hole_starts_a_piece(self):
        _, cuts = sample(*recording([(0, CAMERA), (200, None), (410, CIRCLE)], 900))
        self.assertEqual(cuts, [410])

    def test_a_face_that_comes_back_to_its_place_does_not(self):
        _, cuts = sample(*recording([(0, CAMERA), (200, None), (410, CAMERA)], 900))
        self.assertEqual(cuts, [])

    def test_a_second_of_misdetection_is_held_and_starts_no_piece(self):
        track, cuts = sample(*recording([(0, CAMERA), (300, CIRCLE), (330, CAMERA)], 900))
        self.assertEqual(cuts, [])
        self.assertEqual({tuple(p[1:4]) for p in track}, {CAMERA})

    def test_a_blurred_frame_of_a_fast_head_is_not_a_cut(self):
        def lean(frame):  # the same lean, and the detector loses the face on two frames in the middle of it
            if frame in (306, 307):
                return None
            return (0.5 + 0.11 * min(1.0, max(0.0, (frame - 300) / 15)), 0.45, 0.4)
        _, cuts = sample(*recording([(0, lean)], 900))
        self.assertEqual(cuts, [])

    def test_the_largest_face_is_followed_and_two_of_one_size_do_not_take_turns(self):
        twin = (0.3, 0.4, 0.11)
        self.assertEqual(facecuts.pick([twin, CIRCLE], CIRCLE), CIRCLE, "about the same size: the one followed stays")
        self.assertEqual(facecuts.pick([twin, CIRCLE], None), twin)
        self.assertEqual(facecuts.pick([CAMERA, CIRCLE], CIRCLE), CAMERA, "a clearly larger face wins, as it always did")
        self.assertEqual(facecuts.pick([AVATAR], CIRCLE), AVATAR)
        self.assertIsNone(facecuts.pick([], CIRCLE))

    def test_the_track_does_not_stay_on_a_small_face_after_one_frame_without_the_speaker(self):
        both = [CIRCLE, AVATAR]
        track, cuts = sample(*recording([(0, both), (300, [AVATAR]), (315, both)], 900))
        self.assertEqual(cuts, [])
        self.assertEqual({tuple(p[1:4]) for p in track}, {CIRCLE})


class Track(TempDirCase):
    def build(self, read):
        model = self.tmp / "model.onnx"
        model.write_bytes(b"x")
        (self.tmp / "src" / "data").mkdir(parents=True, exist_ok=True)
        with mock.patch.dict(sys.modules, {"cv2": mock.Mock()}), mock.patch.dict("os.environ", {"AIEDITING_YUNET_MODEL": str(model)}), \
                mock.patch.object(face, "_read", return_value=read):
            note = face.build_track(self.tmp / "source.mp4", self.tmp)
        return note, json.loads((self.tmp / "src" / "data" / "face.json").read_text(encoding="utf-8"))

    def test_the_file_carries_the_piece_of_every_point_and_the_report_names_the_cuts(self):
        points = [[k * 0.5] + list(CAMERA if k < 6 else CIRCLE) for k in range(12)]
        note, track = self.build((points, 12, [0.0] * 6 + [2.9] * 6))
        self.assertEqual(track[5], [2.5, 0.5, 0.45, 0.4, 0.0])
        self.assertEqual(track[6], [3.0, 0.89, 0.8, 0.1, 2.9])
        self.assertIn("смен кадра и склеек со скачком лица: 1 (2.9)", note)

    def test_no_face_holds_the_centre(self):
        note, track = self.build(([[0.0, None, None, None]], 0, []))
        self.assertEqual(track, [face.CENTRE])
        self.assertIn("не найдено", note)

    def test_a_track_of_the_earlier_kind_is_kept_and_named(self):
        target = self.tmp / "src" / "data" / "face.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps([[0.0, 0.4, 0.4, 0.3], [0.5, 0.41, 0.4, 0.3]]), encoding="utf-8")
        note = face.build_track(self.tmp / "source.mp4", self.tmp)
        self.assertIn("уже построен", note)
        self.assertIn("прежнего образца", note)
        target.write_text(json.dumps([[0.0, 0.4, 0.4, 0.3, 0.0], [0.5, 0.41, 0.4, 0.3, 0.0]]), encoding="utf-8")
        self.assertNotIn("прежнего образца", face.build_track(self.tmp / "source.mp4", self.tmp))

    def test_in_a_folder_edited_by_markers_the_kept_track_is_not_to_be_deleted(self):
        data = self.tmp / "src" / "data"
        data.mkdir(parents=True)
        (data / "face.json").write_text(json.dumps([[0.0, 0.4, 0.4, 0.3, 0.0], [0.5, 0.41, 0.4, 0.3, 0.0]]), encoding="utf-8")
        self.assertNotIn("не удаляйте", face.build_track(self.tmp / "source.mp4", self.tmp))
        (data / "time-map.json").write_text(json.dumps({"rows": MARKED}), encoding="utf-8")
        note = face.build_track(self.tmp / "source.mp4", self.tmp)
        self.assertIn("не удаляйте", note)
        self.assertNotIn("удалите src/data/face.json", note)

    def test_a_track_built_anew_in_such_a_folder_is_named_as_being_in_the_wrong_seconds(self):
        (self.tmp / "src" / "data").mkdir(parents=True)
        (self.tmp / "src" / "data" / "time-map.json").write_text(json.dumps({"rows": MARKED}), encoding="utf-8")
        points = [[k * 0.5] + list(CAMERA) for k in range(4)]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.build((points, 4, [0.0] * 4))
        self.assertIn("в секундах этого файла", out.getvalue())


MARKED = [[0, 10, 0, 10, 0], [10, 25, 20, 35, 0]]  # an edit by markers took seconds 10-20 out
NEW_KIND = [[k * 0.5, 0.5, 0.45, 0.4, 0.0 if k < 20 else 10.2] for k in range(71)]  # 35 s, one cut at 10.2
OLD_KIND = [[k * 0.5, 0.5, 0.45, 0.4] for k in range(71)]


class Command(TempDirCase):
    """`overlay.py face`: the cuts of a folder's track, a rebuild that cannot lose the track, what still reads it the old way."""

    def setUp(self):
        super().setUp()
        self.work = self.tmp / "work"
        for sub in ("src/data", "src/kit", "public/clips"):
            (self.work / sub).mkdir(parents=True)
        (self.work / "src" / "Root.tsx").write_text("//", encoding="utf-8")
        (self.work / "public" / "clips" / "source.mp4").write_bytes(b"x")
        self.track = self.work / "src" / "data" / "face.json"

    def put(self, track, rows=()):
        self.track.write_text(json.dumps(track), encoding="utf-8")
        (self.work / "src" / "data" / "time-map.json").write_text(json.dumps({"rows": list(rows)}), encoding="utf-8")

    def run_face(self, detected=None, **flags):
        ns = argparse.Namespace(work=str(self.work), rebuild=False, video=None, frames=False)
        for key, value in flags.items():
            setattr(ns, key, value)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(face, "detect", return_value=detected or (None, "нет OpenCV")), \
                mock.patch.object(facecmd, "_source", side_effect=lambda work, rows, given: self.work / "public" / "clips" / "source.mp4"):
            code = facecmd.run_face(ns)
        return code, out.getvalue()

    def test_it_lists_every_cut_in_scene_and_file_seconds(self):
        self.put(NEW_KIND, MARKED)
        _, out = self.run_face()
        self.assertIn("смен кадра и склеек со скачком лица: 1", out)
        self.assertIn("10.20 с сцены", out)
        self.assertEqual(facecmd.cut_frames(NEW_KIND, []), [10.4])
        self.assertEqual(facecmd.cut_frames(NEW_KIND, MARKED), [], "the cut lies in the seconds the edit removed")
        moved = [p[:4] + [0.0 if p[0] < 25 else 25.0] for p in NEW_KIND]
        self.assertEqual(facecmd.cut_frames(moved, MARKED), [15.2], "scene second 25 is second 15 of the file")

    def test_a_track_of_the_earlier_kind_and_old_readers_are_named(self):
        self.put(OLD_KIND)
        (self.work / "src" / "kit" / "Presenter.tsx").write_text("const track = (col) => Math.exp(col);", encoding="utf-8")
        _, out = self.run_face()
        self.assertIn("прежнего образца (четыре числа", out)
        self.assertIn("src/kit/Presenter.tsx прежнего образца", out)
        shutil.copyfile(str(KIT / "template" / "src" / "kit" / "Presenter.tsx"), str(self.work / "src" / "kit" / "Presenter.tsx"))
        self.assertEqual(facecmd.stale_readers(self.work), [])

    def test_a_rebuild_that_fails_leaves_the_track_alone(self):
        self.put(OLD_KIND)
        with self.assertRaises(ToolError):
            self.run_face(rebuild=True)
        self.assertEqual(json.loads(self.track.read_text(encoding="utf-8")), OLD_KIND)

    def test_a_rebuild_keeps_the_earlier_track_beside_the_new_one(self):
        self.put(OLD_KIND)
        self.run_face(detected=(NEW_KIND, "готово"), rebuild=True)
        self.assertEqual(json.loads(self.track.read_text(encoding="utf-8")), NEW_KIND)
        self.assertEqual(json.loads((self.work / facecmd.BACKUP).read_text(encoding="utf-8")), OLD_KIND)
        self.run_face(detected=(OLD_KIND, "готово"), rebuild=True)
        self.assertEqual(json.loads((self.work / facecmd.BACKUP).read_text(encoding="utf-8")), OLD_KIND, "the first copy is not written over")
        second = self.work / "raw" / "face-before-rebuild-2.json"
        self.assertEqual(json.loads(second.read_text(encoding="utf-8")), NEW_KIND, "and the next rebuild keeps what it replaced too")

    def test_in_a_folder_edited_by_markers_a_rebuild_needs_the_first_accepted_video(self):
        self.put(OLD_KIND, MARKED)
        with self.assertRaises(ToolError) as refused:
            facecmd._source(self.work, MARKED, None)
        self.assertIn("--video", str(refused.exception))
        with self.assertRaises(ToolError):
            facecmd._source(self.work, [], "any.mp4")
        with self.assertRaises(ToolError) as wrong:  # a track of another length is a track of another video
            self.run_face(detected=(NEW_KIND[:50], "готово"), rebuild=True, video="x.mp4")
        self.assertIn("не первый принятый ролик", str(wrong.exception))
        self.assertEqual(json.loads(self.track.read_text(encoding="utf-8")), OLD_KIND)
        self.run_face(detected=(NEW_KIND, "готово"), rebuild=True, video="x.mp4")
        self.assertEqual(json.loads(self.track.read_text(encoding="utf-8")), NEW_KIND)
        own = self.work / "public" / "clips" / "source.mp4"
        with self.assertRaises(ToolError) as same:  # the video after the edits is not the first accepted one
            facecmd._source(self.work, MARKED, str(own))
        self.assertIn("нынешний", str(same.exception))

    def test_a_track_built_by_mistake_from_the_edited_video_does_not_stand_in_the_way_of_the_right_one(self):
        # `prepare` without --keep-face wrote a track of the file after the edits: 25 s, while the scenes' seconds go to 35
        wrong = NEW_KIND[:51]
        self.put(wrong, MARKED)
        with self.assertRaises(ToolError):  # the same short video again is still refused
            self.run_face(detected=(wrong, "готово"), rebuild=True, video="x.mp4")
        self.run_face(detected=(NEW_KIND, "готово"), rebuild=True, video="x.mp4")
        self.assertEqual(json.loads(self.track.read_text(encoding="utf-8")), NEW_KIND)
        tail_cut = [[0, 10, 0, 10, 0], [10, 20, 20, 30, 0]]  # the edit also took the last five seconds: the scenes reach 30, the first video 35
        self.put(wrong, tail_cut)
        self.run_face(detected=(NEW_KIND, "готово"), rebuild=True, video="x.mp4")
        self.assertEqual(json.loads(self.track.read_text(encoding="utf-8")), NEW_KIND)

    def test_a_joint_of_an_edit_by_markers_across_which_the_face_jumps_gets_a_still(self):
        moved = [[k * 0.5, 0.3 if k < 30 else 0.7, 0.45, 0.4, 0.0] for k in range(71)]  # elsewhere after second 15, inside what was cut
        self.assertEqual(facecmd.joint_seconds(moved, MARKED), [10])
        self.assertEqual(facecmd.cut_frames(moved, MARKED), [10.2])
        self.assertEqual(facecmd.joint_seconds(NEW_KIND, MARKED), [], "the face stayed where it was: nothing to look at")
        self.put(moved, MARKED)
        self.assertIn("Стыков, через которые лицо в треке скачет: 1", self.run_face()[1])


def node_json(test, module, body, **data):
    """Run a pure .ts module of the kit in node; an older node needs a flag to take the types off, a still older one is skipped."""
    code = "const d = {}; import('{}').then((m) => {{ {} }}).then((v) => console.log(JSON.stringify(v)))".format(
        json.dumps(data), module.as_uri(), body)
    for flags in ([], ["--experimental-strip-types"]):
        done = subprocess.run(["node", "--no-warnings", *flags, "-e", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if done.returncode == 0:
            return json.loads(done.stdout)
        if "ERR_UNKNOWN_FILE_EXTENSION" not in done.stderr and "bad option" not in done.stderr:
            break
    else:
        test.skipTest("this node cannot run TypeScript")
    test.fail(done.stderr[-600:])


@unittest.skipUnless(shutil.which("node"), "node is missing")
class Frame(unittest.TestCase):
    """template/src/kit/faceTrack.ts itself, run in node: where the speaker's frame is centred at a second."""

    def js(self, body, **data):
        return node_json(self, FACE_TRACK, body, **data)

    def centres(self, track, seconds, cuts=()):
        return self.js("const at = m.makeFace(d.track, d.cuts); return d.seconds.map((t) => at(t));", track=track, seconds=seconds, cuts=list(cuts))

    def test_the_frame_is_on_the_new_face_a_fifth_of_a_second_after_a_cut(self):
        track, cuts = sample(*recording([(0, CAMERA), (307, CIRCLE), (640, CAMERA)], 1200))
        first, second = cuts[0] / 30, cuts[1] / 30
        seen = self.centres(track, [first - 1 / 30, first, first + AFTER, second - 1 / 30, second, second + AFTER])
        for got, want in zip(seen, [CAMERA, CIRCLE, CIRCLE, CIRCLE, CAMERA, CAMERA]):
            self.assertAlmostEqual(got["cx"], want[0], places=3)
            self.assertAlmostEqual(got["cy"], want[1], places=3)
            self.assertAlmostEqual(got["fh"], want[2], places=3)

    def test_inside_a_piece_the_frame_still_glides_without_steps(self):
        def sway(frame):  # a slow sway of the head, 0.1 of the frame width in 8 s
            return (0.5 + 0.05 * (1 if (frame // 240) % 2 else -1) * (1 - abs((frame % 240) - 120) / 120), 0.45, 0.4)
        track, cuts = sample(*recording([(0, sway)], 1800))
        self.assertEqual(cuts, [])
        seen = [f["cx"] for f in self.centres(track, [k / 30 for k in range(0, 1800)])]
        self.assertLess(max(abs(a - b) for a, b in zip(seen, seen[1:])) * 1920, 1.0, "less than a pixel per frame")
        self.assertGreater(max(seen) - min(seen), 0.02, "and it does follow the head")

    def test_an_edit_by_markers_cuts_the_track_at_the_edges_of_its_rows(self):
        # a track of the earlier kind with no pieces of its own: the head is elsewhere after the seconds the edit removed
        track = [[k * 0.5, 0.3 if k < 30 else 0.7, 0.45, 0.4] for k in range(80)]
        rows = [[0, 10, 0, 10, 0], [10, 25, 20, 35, 0]]
        seen = self.js("const at = m.makeFace(d.track, m.rowCuts(d.rows)); return d.file.map((n) => at(m.faceSecond(d.rows, n)).cx);",
                       track=track, rows=rows, file=[10 - 1 / 30, 10, 10 + AFTER])
        self.assertAlmostEqual(seen[0], 0.3, places=3)
        self.assertAlmostEqual(seen[1], 0.7, places=3)
        self.assertAlmostEqual(seen[2], 0.7, places=3)

    def test_a_row_held_at_its_end_keeps_its_own_face(self):
        # the take was made half a second longer: the scene second stands at 10 while the old take is still in the picture
        track, _ = sample(*recording([(0, CAMERA), (300, CIRCLE)], 900))
        rows = [[0, 10.5, 0, 10, 0], [10.5, 20.5, 10, 20, 0]]
        seen = self.js("const at = m.makeFace(d.track, m.rowCuts(d.rows)); return d.file.map((n) => at(m.faceSecond(d.rows, n)).cx);",
                       track=track, rows=rows, file=[10.3, 10.5, 10.5 + AFTER])
        self.assertAlmostEqual(seen[0], CAMERA[0], places=3)
        self.assertAlmostEqual(seen[1], CIRCLE[0], places=3)
        self.assertAlmostEqual(seen[2], CIRCLE[0], places=3)

    def test_without_a_map_the_face_is_read_at_the_second_of_the_file(self):
        self.assertEqual(self.js("return [m.faceSecond([], 7.25), m.rowCuts([])];"), [7.25, []])

    def test_the_spans_of_a_vertical_clip_are_cuts_too(self):
        # a track with no pieces of its own, the head is elsewhere from second 29.5; the clip joins seconds 4-6 to seconds 30-32
        track = [[k * 0.5, 0.3 if k < 59 else 0.7, 0.45, 0.4] for k in range(80)]
        plain = self.centres(track, [30.0])[0]["cx"]
        split = self.centres(track, [5.99, 30.0, 30.0 + AFTER], cuts=[4, 6, 30, 32])
        self.assertAlmostEqual(split[0]["cx"], 0.3, places=3)
        self.assertAlmostEqual(split[1]["cx"], 0.7, places=3)
        self.assertAlmostEqual(split[2]["cx"], 0.7, places=3)
        self.assertNotAlmostEqual(plain, 0.7, places=2, msg="the same track without the cuts is still on its way")

    def test_a_piece_too_short_to_hold_a_point_reads_its_own_face_not_the_take_next_door(self):
        # the track changes face at 10.2; an edit by markers left a sliver of the old take, seconds 10.05-10.15 of the scenes
        track, _ = sample(*recording([(0, CAMERA), (306, CIRCLE)], 900))
        seen = self.centres(track, [10.1], cuts=[10.05, 10.15])
        self.assertAlmostEqual(seen[0]["cx"], CAMERA[0], places=3)

    def test_the_face_second_is_the_scene_second_everywhere_but_at_the_held_end_of_a_row(self):
        rows = [[0, 10.5, 0, 10, 0], [10.5, 20.5, 10, 20, 0], [20.5, 30, 24, 33.5, 0.5]]
        file = [k / 10 for k in range(0, 300)]
        seen = self.js("return d.file.map((n) => m.faceSecond(d.rows, n));", rows=rows, file=file)
        for n, got in zip(file, seen):
            want = vmap.to_old(rows, n)  # the mirror of toOld in kit/time.ts
            held = want == [r for r in rows if r[0] <= n][-1][3]  # the row this second of the file lies in stands at its end
            self.assertAlmostEqual(got, want - 0.01 if held else want, places=6, msg=str(n))


@unittest.skipUnless(shutil.which("node"), "node is missing")
class Joint(unittest.TestCase):
    """template/src/vertical/spanTime.ts in node: at a joint of two spans the second belongs to the picture that is shown."""

    SPANS = [[4.0, 6.37], [30.0, 32.0]]  # at 30 fps and rate 1.2 the joint falls on frame 59.25: the video layer starts span two at 59

    def js(self, body, **data):
        return node_json(self, SPAN_TIME, body, spans=self.SPANS, **data)

    def test_the_first_frame_of_a_span_already_has_its_second(self):
        edges = self.js("return m.spanEdges(d.spans, 30, 1.2);")
        self.assertEqual(edges, [0, 59, 109])
        seen = self.js("const at = m.frameSecond(d.spans, 30, 1.2); return d.frames.map((f) => at(f));", frames=[0, 58, 59, 60, 108, 109, 500])
        self.assertEqual(seen[0], 4.0)
        self.assertLess(seen[1], 6.37)
        self.assertEqual(seen[2], 30.0, "frame 59 shows span two, so it reads second 30")
        self.assertAlmostEqual(seen[3], 30.04, places=6)
        self.assertLess(seen[4], 32.0)
        self.assertEqual(seen[5:], [32.0, 32.0], "after the speech the second stands at the end")

    def test_a_frame_of_a_span_never_reaches_the_second_of_its_end(self):
        seen = self.js("const at = m.frameSecond([[0, 1.0], [5, 5.99]], 30, 1); return [29, 30, 59].map((f) => at(f));")
        self.assertLess(seen[0], 1.0)
        self.assertEqual(seen[1], 5.0)
        self.assertLessEqual(seen[2], 5.98)


class Kit(TempDirCase):
    def test_both_presenters_read_the_face_only_through_the_track_by_pieces(self):
        for rel, cuts in (("kit/Presenter.tsx", "rowCuts(ROWS)"), ("vertical/VPresenter.tsx", "spans.flatMap")):
            text = (KIT / "template" / "src" / rel).read_text(encoding="utf-8")
            self.assertIn("makeFace(", text, rel)
            self.assertIn("faceSecond(ROWS", text, rel)
            self.assertIn(cuts, text, rel)
            for own in ("Math.exp", "const spline", "const track"):  # a smoothing of its own would go through the cuts again
                self.assertNotIn(own, text, rel)

    def test_the_pure_modules_run_without_the_project(self):
        for path in (FACE_TRACK, SPAN_TIME):
            self.assertNotIn("import ", path.read_text(encoding="utf-8").replace("no imports", ""), path.name)
        clips = (KIT / "template" / "src" / "vertical" / "clips.ts").read_text(encoding="utf-8")
        self.assertIn("frameSecond(SPANS[id], FPS, RATE)", clips, "the seconds of a clip's frame come from the same edges as the video layer")
        self.assertIn("spanTime.ts", vinit.SET_FILES)

    def test_a_folder_made_before_the_pieces_gets_the_module_with_the_vertical_set(self):
        work = self.tmp / "work"
        for sub in ("src/kit", "src/data"):
            (work / sub).mkdir(parents=True)
        (work / "src" / "kit" / "time.ts").write_text("export const setFrameMap = 1;\n", encoding="utf-8")
        (work / "src" / "kit" / "tokens.ts").write_text("export const MARK = 1;\n", encoding="utf-8")
        done = vinit.patch_kit(work)
        self.assertEqual((work / "src" / "kit" / "faceTrack.ts").read_text(encoding="utf-8"), FACE_TRACK.read_text(encoding="utf-8"))
        self.assertEqual(len(done), 1)
        self.assertFalse((work / "src" / "data" / "time-map.json").exists(), "a missing time map is never made up: it must fail loudly")
        (work / "src" / "kit" / "faceTrack.ts").write_text("// mine\n", encoding="utf-8")
        self.assertEqual(vinit.patch_kit(work), [])
        self.assertEqual((work / "src" / "kit" / "faceTrack.ts").read_text(encoding="utf-8"), "// mine\n")

    def test_the_module_arrives_even_when_the_rest_of_an_old_kit_is_refused(self):
        work = self.tmp / "work"
        (work / "src" / "kit").mkdir(parents=True)
        (work / "src" / "kit" / "time.ts").write_text("// not the template's\n", encoding="utf-8")
        with self.assertRaises(ToolError):
            vinit.patch_kit(work)
        self.assertTrue((work / "src" / "kit" / "faceTrack.ts").is_file())


if __name__ == "__main__":
    unittest.main()
