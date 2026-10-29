"""A secret on screen is closed for all the time it may be there and in every place it shows up."""
import importlib.util
import unittest

from _support import SKILL, TempDirCase, ffmpeg, needs_ffmpeg

HAVE_PIL = importlib.util.find_spec("PIL") is not None
FRAME = (640, 360)
MAIL = "Mail: test.user@example.com"


def picture(path, lines):
    """A white frame with each (text, (x, y)) drawn large enough for OCR."""
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype(str(SKILL / "design" / "chrome-graphite" / "fonts" / "Onest.ttf"), 30)
    img = Image.new("RGB", FRAME, "white")
    draw = ImageDraw.Draw(img)
    for text, at in lines:
        draw.text(at, text, fill="black", font=font)
    img.save(path)
    return path


def ocr_or_skip(case):
    from runtime.look import ocr_backend

    if not ocr_backend():
        case.skipTest("no OCR here (Apple Vision needs Xcode tools; else Tesseract in PATH)")


@unittest.skipUnless(HAVE_PIL, "Pillow not installed")
class EveryPlace(TempDirCase):
    def test_reappearing_or_elsewhere_is_a_new_candidate(self):
        from runtime.look import find_secrets

        ocr_or_skip(self)
        top, low = (40, 40), (40, 280)
        shots = [picture(self.tmp / "frame_001_t1.000s.png", [(MAIL, top)]),
                 picture(self.tmp / "frame_002_t3.000s.png", []),
                 picture(self.tmp / "frame_003_t5.000s.png", [(MAIL, top)]),
                 picture(self.tmp / "frame_004_t7.000s.png", [(MAIL, top), (MAIL, low)])]
        mails = [c for c in find_secrets(shots, {"words": []}) if c["kind"] == "email"]
        got = sorted((c["start"], c["end"], c["rect"]["y"] < 180) for c in mails)
        self.assertEqual(got, [(1.0, 1.0, True), (5.0, 7.0, True), (7.0, 7.0, False)])
        for c in mails:
            self.assertEqual(c["text"], "test.user@example.com")


@needs_ffmpeg
@unittest.skipUnless(HAVE_PIL, "Pillow not installed")
class WholeStretch(TempDirCase):
    def test_ticked_ocr_candidate_closed_from_snapshot_before_to_snapshot_after(self):
        from runtime import pipelines
        from test_blur_static import gray_frame, sharpness
        from test_pipelines_helpers import Approver, profile

        ocr_or_skip(self)
        blank = picture(self.tmp / "пусто.png", [])
        text = picture(self.tmp / "почта.png", [(MAIL, (40, 160))])
        src = self.tmp / "эфир.mp4"
        ffmpeg("-loop", "1", "-t", "4", "-i", blank, "-loop", "1", "-t", "4", "-i", text,
               "-loop", "1", "-t", "4", "-i", blank, "-filter_complex",
               "[0:v][1:v][2:v]concat=n=3:v=1:a=0,fps=25,format=yuv420p[v]", "-map", "[v]",
               "-c:v", "libx264", "-preset", "ultrafast", "-crf", "12", src)

        def tick(payload):
            for c in payload["candidates"]:
                c["blur"] = c["source"] == "ocr" and c["kind"] == "email"

        prof = profile(["find_secrets", "blur_regions"], {"provider": "command", "command": ["нет"]},
                       secret_frames=6)  # snapshots at 1, 3, 5, 7, 9, 11 s; the mail is on screen 4–8 s
        report = pipelines.run(src, prof, self.tmp / "выпуск", Approver(edits={"secrets": tick}))
        spans = [(r["start"], r["end"]) for r in report["blurred"]]
        self.assertEqual(len(spans), 1, report["blurred"])
        self.assertAlmostEqual(spans[0][0], 3.0, delta=0.01)
        self.assertAlmostEqual(spans[0][1], 9.0, delta=0.01)
        rect = report["blurred"][0]
        box = (rect["x"] + 4, rect["y"] + 4, rect["w"] - 8, rect["h"] - 8)
        for t in (4.2, 7.8):  # on screen, but before the first and after the last snapshot that saw it
            ratio = sharpness(gray_frame(report["output"], t, FRAME), *box) / sharpness(gray_frame(src, t, FRAME), *box)
            self.assertLess(ratio, 0.35, "t={}: the mail is readable".format(t))


if __name__ == "__main__":
    unittest.main()
