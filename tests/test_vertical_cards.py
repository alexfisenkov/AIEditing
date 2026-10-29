"""A card in a 9:16 piece is placed by that piece's own layout, in the finished frame: never on the face."""
import importlib.util
import unittest

from _support import TempDirCase, needs_ffmpeg
from test_blur_static import gray_frame
from test_pipelines_helpers import Approver, asr_config, profile
from test_vertical_media import screen_with_window

OUT = (1080, 1920)
WINDOW = {"x": 1000, "y": 460, "w": 240, "h": 240}
SCREEN_PART = 608  # stack: the 1280x720 screen scaled to 1080 wide is 608 px tall; the face is below it
HAVE_PIL = importlib.util.find_spec("PIL") is not None


def changed_rows(a, b, threshold=40):
    """Rows of the frame where anything differs between two pictures of the same static source."""
    return [y for y, (ra, rb) in enumerate(zip(a, b)) if any(abs(p - q) > threshold for p, q in zip(ra, rb))]


@needs_ffmpeg
@unittest.skipUnless(HAVE_PIL, "Pillow not installed (ae.py doctor installs it)")
class VerticalCard(TempDirCase):
    def test_card_stays_off_the_face_in_a_stack(self):
        from runtime import pipelines

        src = screen_with_window(self.tmp / "экран и окно.mp4", duration=6.0)
        words = {"words": [{"text": "Привет", "start": 0.5, "end": 0.9}, {"text": "всем.", "start": 1.0, "end": 1.4}]}

        def fill(payload):
            payload["items"][0]["text"] = "Заголовок\nпояснение"

        prof = profile(["detect_layout", "vertical", "plate", "overlay_png"], asr_config(self.tmp, words),
                       layout="screen_face_window", face=WINDOW, cards={"on_screen": "corner"})
        approve = Approver(edits={"cards": fill})
        report = pipelines.run(src, prof, self.tmp / "выпуск", approve)
        self.assertIn("cards", approve.asked)
        with_card, without = gray_frame(report["output"], 2.5, OUT), gray_frame(report["output"], 5.6, OUT)
        rows = changed_rows(with_card, without)
        self.assertTrue(rows, "the card is not on the frame at all")
        self.assertLess(max(rows), SCREEN_PART, "the card reaches the face part of the stack")


if __name__ == "__main__":
    unittest.main()
