"""Candidates for blurring from the transcript and from text on frames, each with a frame as evidence."""
import importlib.util
import unittest

from _support import TempDirCase

HAVE_PIL = importlib.util.find_spec("PIL") is not None


def word(text, start, end):
    return {"text": text, "start": start, "end": end, "type": "word"}


TRANSCRIPT = {"language": "ru", "provider": "command", "words": [
    word("пишите", 1.0, 1.4), {"text": " ", "start": 1.4, "end": 1.5, "type": "spacing"},
    word("на", 1.5, 1.6), word("test.user@example.com", 1.6, 3.2),
    word("или", 10.0, 10.2), word("звоните", 10.2, 10.6), word("+7", 10.7, 10.9),
    word("916", 10.9, 11.2), word("123-45-67", 11.2, 12.0),
]}


def fake_frames(folder):
    """Files named the way look.frames names them: time is in the name."""
    paths = []
    for i, t in enumerate((2.0, 6.0, 11.0)):
        path = folder / "frame_{:03d}_t{:.3f}s.png".format(i + 1, t)
        path.write_bytes(b"")
        paths.append(path)
    return paths


class FromTranscript(TempDirCase):
    def test_transcript_only_marks_that_frames_were_not_read(self):
        from runtime.look import find_secrets

        shots = fake_frames(self.tmp)
        found = find_secrets(shots, TRANSCRIPT, ocr=False)
        by_kind = {c["kind"]: c for c in found}
        self.assertEqual(set(by_kind), {"email", "phone"})
        email, phone = by_kind["email"], by_kind["phone"]
        self.assertEqual(email["text"], "test.user@example.com")
        self.assertEqual((email["start"], email["end"]), (1.6, 3.2))
        self.assertEqual((phone["start"], phone["end"]), (10.7, 12.0))
        self.assertEqual(email["frame"], shots[0])  # nearest snapshot in time is the evidence
        self.assertEqual(phone["frame"], shots[2])
        for cand in found:
            self.assertIsNone(cand["rect"])
            self.assertEqual(cand["source"], "transcript")
            self.assertIn("без распознавания текста", cand["note"])


@unittest.skipUnless(HAVE_PIL, "Pillow not installed")
class FromFrames(TempDirCase):
    def setUp(self):
        super().setUp()
        from runtime.look import ocr_backend

        if not ocr_backend():
            self.skipTest("no OCR here (Apple Vision needs Xcode tools; else Tesseract in PATH)")

    def test_text_on_frame_found_with_its_place(self):
        from PIL import Image, ImageDraw, ImageFont

        from _support import SKILL
        from runtime.look import find_secrets

        font = ImageFont.truetype(str(SKILL / "design" / "chrome-graphite" / "fonts" / "Onest.ttf"), 40)
        img = Image.new("RGB", (1280, 720), "white")
        draw = ImageDraw.Draw(img)
        draw.text((100, 100), "Mail: test.user@example.com", fill="black", font=font)
        draw.text((100, 400), "Card 4111 1111 1111 1111", fill="black", font=font)
        shot = self.tmp / "frame_001_t5.000s.png"
        img.save(shot)
        found = {c["kind"]: c for c in find_secrets([shot], {"words": []})}
        self.assertIn("email", found)
        self.assertIn("card", found)
        email = found["email"]
        self.assertEqual(email["frame"], shot)
        self.assertEqual(email["source"], "ocr")
        self.assertEqual((email["start"], email["end"]), (5.0, 5.0))
        r = email["rect"]
        self.assertTrue(80 <= r["y"] <= 120 and r["h"] < 90, r)  # the e-mail line, not the card line
        self.assertTrue(r["x"] > 150, r)  # "Mail:" itself stays outside the area


if __name__ == "__main__":
    unittest.main()
