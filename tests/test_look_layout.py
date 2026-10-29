"""Layout guess on synthetic frames: screen + round camera window, vertical, screen only, face, two tracks."""
import importlib.util
import json
import random
import unittest

from _support import TempDirCase

HAVE_IMAGING = all(importlib.util.find_spec(m) for m in ("PIL", "numpy"))
HAVE_CV2 = importlib.util.find_spec("cv2") is not None
needs_imaging = unittest.skipUnless(HAVE_IMAGING, "Pillow/numpy not installed (ae.py doctor installs them)")

CIRCLE = (1110, 570, 120)  # centre x, centre y, radius on a 1280x720 frame (OBS-style webcam circle)


def screen(path, size=(1280, 720), circle=None, seed=1):
    """A desktop-like frame: light background, a title bar, rows of 'text'; optionally a camera circle."""
    from PIL import Image, ImageDraw

    rnd = random.Random(seed)
    w, h = size
    img = Image.new("RGB", size, (240, 241, 243))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w, 36], fill=(40, 42, 46))
    for y in range(70, h - 30, 26):
        x = 40
        while x < w - 80:
            word = rnd.randint(20, 90)
            draw.rectangle([x, y, x + word, y + 12], fill=(rnd.randint(20, 90),) * 3)
            x += word + rnd.randint(8, 16)
    if circle:
        cx, cy, r = circle
        face = Image.new("RGB", (2 * r, 2 * r))
        fd = ImageDraw.Draw(face)
        for row in range(2 * r):  # warm vertical gradient: a lit face against a darker room
            fd.line([0, row, 2 * r, row], fill=(200 - row // 3, 150 - row // 3, 120 - row // 4))
        fd.ellipse([r // 2, r // 3, 3 * r // 2, 3 * r // 2], fill=(222, 180, 150))
        mask = Image.new("L", (2 * r, 2 * r), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=255)
        img.paste(face, (cx - r, cy - r), mask)
    img.save(path)
    return path


def no_faces(_path):
    return []


def big_face(_path):
    return [{"x": 420, "y": 120, "w": 420, "h": 480, "score": 0.95}]


@needs_imaging
class Layout(TempDirCase):
    def test_screen_with_round_camera_window(self):
        from runtime.look import detect_layout

        shots = [screen(self.tmp / "кадр {}.png".format(i), circle=CIRCLE, seed=i) for i in range(3)]
        guess = detect_layout(shots, detector=no_faces)
        self.assertEqual(guess["kind"], "screen_face_window")
        cx, cy, r = CIRCLE
        face = guess["face"]
        for key, want in (("x", cx - r), ("y", cy - r), ("w", 2 * r), ("h", 2 * r)):
            self.assertAlmostEqual(face[key], want, delta=1280 * 0.03, msg=(key, face))
        self.assertGreater(guess["confidence"], 0.5)
        json.dumps(guess)  # the guess is stored in the session as is

    def test_vertical_frame(self):
        from runtime.look import detect_layout

        shot = screen(self.tmp / "вертикаль.png", size=(720, 1280))
        self.assertEqual(detect_layout([shot], detector=no_faces)["kind"], "vertical")

    def test_screen_without_face(self):
        from runtime.look import detect_layout

        guess = detect_layout([screen(self.tmp / "экран.png")], detector=no_faces)
        self.assertEqual(guess["kind"], "screen_only")
        self.assertIsNone(guess["face"])

    def test_face_filling_the_frame(self):
        from runtime.look import detect_layout

        guess = detect_layout([screen(self.tmp / "лицо.png")], detector=big_face)
        self.assertEqual(guess["kind"], "face_full")
        self.assertEqual(guess["face"]["w"], 420)

    def test_two_sources_camera_and_screen_are_separate_tracks(self):
        from runtime.look import detect_layout

        cam, scr = screen(self.tmp / "камера.png"), screen(self.tmp / "экран.png")
        guess = detect_layout([[cam], [scr]], detector=lambda p: big_face(p) if p == cam else [])
        self.assertEqual(guess["kind"], "separate_tracks")

    @unittest.skipIf(HAVE_CV2, "opencv is installed here; the refusal path cannot be seen")
    def test_without_opencv_refuses_with_doctor_hint(self):
        from runtime.look import LookError, detect_layout

        with self.assertRaises(LookError) as ctx:
            detect_layout([screen(self.tmp / "кадр.png")])
        self.assertIn("doctor", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
