"""Interview answers about movement and sound are obeyed: zoom_face, moves and denoise change what happens."""
from _support import TempDirCase, ffmpeg, make_av, needs_ffmpeg
from test_pipelines_helpers import LESSON, LESSON_SECONDS, Approver, asr_config, bursts, profile

STEPS = ["detect_layout", "motion"]


@needs_ffmpeg
class MotionAnswers(TempDirCase):
    def setUp(self):
        super().setUp()
        self.src = make_av(self.tmp / "урок.mp4", [(a, b) for a, b, _ in LESSON], LESSON_SECONDS, size="320x180")
        self.asr = asr_config(self.tmp, bursts(LESSON))  # the words include «смотрите»

    def run_with(self, out, approve=None, screen=None, **params):
        from runtime import pipelines

        approve = approve or Approver()
        return pipelines.run(self.src, profile(STEPS, self.asr, **params), self.tmp / out, approve,
                             screen=screen), approve

    def test_no_face_zoom_when_the_person_said_no(self):
        face = {"x": 120, "y": 40, "w": 80, "h": 100}
        report, approve = self.run_with("нет", layout="face_full", face=face, zoom_face=False)
        self.assertNotIn("motion", approve.asked)
        self.assertEqual(report["motion"], [])
        report, approve = self.run_with("да", layout="face_full", face=face, zoom_face=True)
        self.assertIn("motion", approve.asked)

    def test_no_side_by_side_when_the_person_said_no(self):
        screen = self.tmp / "экран.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=0x404040:s=320x180:r=50:d={}".format(LESSON_SECONDS),
               "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(screen))
        face = {"x": 110, "y": 40, "w": 100, "h": 100}
        report, approve = self.run_with("нет", screen=screen, layout="separate_tracks", face=face, moves=False)
        self.assertNotIn("motion", approve.asked)
        self.assertEqual(report["motion"], [])

    def test_noise_reduction_asked_for_is_named_in_the_report(self):
        report, _ = self.run_with("шум", layout="screen_face_window", denoise=True)
        self.assertTrue(any("Шумодав" in n for n in report["notes"]), report["notes"])
