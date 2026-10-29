"""Lesson pipeline on a synthetic recording: pauses, «э-э», retakes, movement by layout, chapters, .srt."""
import importlib.util
import unittest

from _support import TempDirCase, ffmpeg, make_av, needs_ffmpeg
from test_blur_static import gray_frame
from test_pipelines_helpers import LESSON, LESSON_SECONDS, Approver, asr_config, bursts, hear, profile, sha

HAVE_PIL = importlib.util.find_spec("PIL") is not None
STEPS = ["speech_spans", "cut_spans", "verify_words", "drift_ms", "loudnorm", "write_srt"]
ALL_WORDS = ["Привет", "ну", "сегодня", "мы", "сегодня", "мы", "смотрите", "говорим.", "Опус"]
LAST_TAKE = ["Привет", "ну", "сегодня", "мы", "смотрите", "говорим.", "Опус"]


@needs_ffmpeg
class Lesson(TempDirCase):
    def setUp(self):
        super().setUp()
        self.src = make_av(self.tmp / "урок.mp4", [(a, b) for a, b, _ in LESSON], LESSON_SECONDS, size="320x180")
        self.table = bursts(LESSON)
        self.asr = asr_config(self.tmp, self.table)
        self.out = self.tmp / "выпуски" / "2026-10-29-урок"

    def lesson(self, steps=STEPS, **params):
        base = dict(gap=0.5, pad=0.12, lufs=-16, fillers_cut=["э-э", "м-м"], fillers_keep=["ну", "вот"],
                    retakes="last_good", glossary={"Опус": "Opus"})
        base.update(params)
        return profile(steps, self.asr, **base)

    def test_pauses_and_hesitation_go_retake_waits_for_yes(self):
        from runtime import pipelines
        from runtime.media import probe

        before = sha(self.src)
        approve = Approver(answers={"retakes": False})
        report = pipelines.run(self.src, self.lesson(), self.out, approve)
        self.assertIn("retakes", approve.asked)
        self.assertEqual(hear(self.tmp, report["output"], self.table), ALL_WORDS, "«э-э» cut, «ну» kept, no retake")
        self.assertEqual(report["words_lost"], [])
        self.assertLess(report["drift_ms"], 40)
        self.assertLess(probe(report["output"])["duration"], LESSON_SECONDS - 1.5)  # the 1.2 s pause and more
        self.assertTrue(any("пауза" in c["why"] for c in report["cuts"]))
        self.assertTrue(any("э-э" in c["why"] for c in report["cuts"]))
        self.assertEqual(sha(self.src), before)

    def test_approved_retake_keeps_the_last_take(self):
        from runtime import pipelines

        report = pipelines.run(self.src, self.lesson(), self.out, Approver())
        self.assertEqual(hear(self.tmp, report["output"], self.table), LAST_TAKE)
        self.assertEqual(report["words_lost"], [])

    def test_srt_proofread_by_glossary_and_by_the_person(self):
        from runtime import pipelines

        fix = Approver(edits={"srt": lambda p: p["replace"].update({"говорим": "поговорим"})})
        report = pipelines.run(self.src, self.lesson(), self.out, fix)
        srt = report["srt"].read_text(encoding="utf-8")
        self.assertIn("Opus", srt)
        self.assertNotIn("Опус", srt)
        self.assertIn("поговорим", srt)
        text = report["report"].read_text(encoding="utf-8")
        self.assertIn("«Опус» → «Opus»", text)
        self.assertIn("«говорим» → «поговорим»", text)
        self.assertEqual(report["srt"].parent, self.out.resolve())

    def test_motion_follows_the_layout(self):
        from runtime import pipelines

        steps = ["detect_layout", "speech_spans", "cut_spans", "motion"]
        approve = Approver()
        window = pipelines.run(self.src, self.lesson(steps, layout="screen_face_window",
                                                     face={"x": 200, "y": 100, "w": 100, "h": 70}),
                               self.out, approve)
        self.assertEqual(window["motion"], [])
        self.assertNotIn("motion", approve.asked, "nothing to propose: no close-ups over a screen")
        face = pipelines.run(self.src, self.lesson(steps, layout="face_full",
                                                   face={"x": 120, "y": 40, "w": 80, "h": 100}),
                             self.tmp / "лицо", Approver())
        self.assertEqual([m["cue"] for m in face["motion"]], ["смотрите"])
        self.assertEqual(face["motion"][0]["move"], "zoom")

    def test_separate_tracks_move_only_where_approved(self):
        from runtime import pipelines

        screen = self.tmp / "экран.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=0x404040:s=320x180:r=50:d={}".format(LESSON_SECONDS),
               "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(screen))
        steps = ["detect_layout", "speech_spans", "cut_spans", "motion"]
        prof = self.lesson(steps, layout="separate_tracks", face={"x": 110, "y": 40, "w": 100, "h": 100})
        no = pipelines.run(self.src, prof, self.out, Approver(answers={"motion": False}), screen=screen)
        self.assertEqual(no["motion"], [])
        yes = pipelines.run(self.src, prof, self.tmp / "да", Approver(), screen=screen)
        self.assertEqual(len(yes["motion"]), 1)
        m = yes["motion"][0]
        rows = gray_frame(yes["output"], (m["start"] + m["end"]) / 2, (320, 180))
        self.assertLess(abs(rows[90][60] - 70), 25, "the grey screen came in on the left")
        self.assertGreater(rows[90][300], 200, "the camera (white while speaking) stays on the right")

    def test_file_approver_stops_and_resumes_until_done(self):
        import json
        import sys

        from _support import SKILL
        from runtime import pipelines

        sys.path.insert(0, str(SKILL / "templates" / "format-skill"))
        try:
            from approvals import FileApprover, NeedsApproval
        finally:
            sys.path.pop(0)
        asked, answers = [], {}
        for _ in range(6):
            try:
                report = pipelines.run(self.src, self.lesson(), self.out, FileApprover(self.out))
                break
            except NeedsApproval:
                question = json.loads((self.out / "вопросы.json").read_text(encoding="utf-8"))
                asked.append(question["key"])
                answers[question["key"]] = True
                (self.out / "ответы.json").write_text(json.dumps(answers), encoding="utf-8")
        else:
            self.fail("the run never finished: {}".format(asked))
        self.assertEqual(asked, ["retakes", "srt"], "questions come first, in a fixed order")
        self.assertEqual(hear(self.tmp, report["output"], self.table), LAST_TAKE)
        self.assertFalse(any(p.name.startswith(".aiediting") for p in self.out.iterdir()), "no work left")

    @unittest.skipUnless(HAVE_PIL, "Pillow not installed (ae.py doctor installs it)")
    def test_chapters_become_plates_from_the_design(self):
        from runtime import pipelines

        src = make_av(self.tmp / "урок640.mp4", [(a, b) for a, b, _ in LESSON], LESSON_SECONDS, size="640x360")
        steps = ["speech_spans", "cut_spans", "plate", "overlay_png"]
        title = Approver(edits={"chapters": lambda p: p["items"][0].update(title="Знакомство")})
        report = pipelines.run(src, self.lesson(steps, chapters={"plates": True, "timecodes": True}),
                               self.out, title)
        self.assertEqual([c["title"] for c in report["chapters"]], ["Знакомство"])
        self.assertIn("Знакомство", report["report"].read_text(encoding="utf-8"))
        rows = gray_frame(report["output"], 0.45, (640, 360))
        self.assertLess(min(rows[y][320] for y in range(300, 345)), 120, "a dark plate low in the frame")
        self.assertGreater(rows[100][320], 200, "the rest of the white frame is untouched")


if __name__ == "__main__":
    unittest.main()
