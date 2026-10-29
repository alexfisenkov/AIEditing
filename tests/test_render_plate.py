"""Design layer as pictures: chapter plate, caption, card — sizes and places checked on the alpha channel."""
import importlib.util
import unittest

from _support import SKILL, TempDirCase

HAVE_PIL = importlib.util.find_spec("PIL") is not None
DESIGN = SKILL / "design" / "chrome-graphite"
FRAME = (1920, 1080)


def opaque_box(path):
    from PIL import Image

    with Image.open(path) as img:
        return img.size, img.getchannel("A").getbbox()


@unittest.skipUnless(HAVE_PIL, "Pillow not installed (ae.py doctor installs it)")
class Plates(TempDirCase):
    def test_chapter_is_small_dark_at_the_bottom_and_as_wide_as_its_text(self):
        from PIL import Image

        from runtime.render import plate

        short = plate("Глава 2", DESIGN, "chapter", frame_size=FRAME, out=self.tmp / "коротко.png")
        long_ = plate("Глава 2. Подключаем распознавание речи", DESIGN, "chapter", frame_size=FRAME,
                      out=self.tmp / "длинно.png")
        size, (x0, y0, x1, y1) = opaque_box(short)
        self.assertEqual(size, FRAME)
        self.assertGreater(y1, FRAME[1] * 0.85)  # sits at the bottom
        self.assertLess(y1 - y0, FRAME[1] * 0.08)  # small
        self.assertLess(x1 - x0, FRAME[0] * 0.2)
        self.assertAlmostEqual((x0 + x1) / 2, FRAME[0] / 2, delta=4)
        _, (lx0, _, lx1, _) = opaque_box(long_)
        self.assertGreater(lx1 - lx0, (x1 - x0) * 2)  # width follows the text
        with Image.open(short) as img:
            r, g, b, a = img.getpixel((x0 + 6, (y0 + y1) // 2))
        self.assertLess(max(r, g, b), 60)  # graphite, not a colour
        self.assertTrue(150 < a < 255)  # slightly see-through

    def test_cyrillic_is_drawn_with_real_glyphs(self):
        from PIL import Image, ImageChops

        from runtime.render import plate

        a = plate("Ж", DESIGN, "chapter", frame_size=FRAME, out=self.tmp / "ж.png")
        b = plate("Щ", DESIGN, "chapter", frame_size=FRAME, out=self.tmp / "щ.png")
        with Image.open(a) as ia, Image.open(b) as ib:
            self.assertIsNotNone(ImageChops.difference(ia, ib).getbbox())  # missing glyphs look identical

    def test_card_goes_to_the_requested_corner_on_a_darkened_background(self):
        from PIL import Image

        from runtime.render import plate

        card = plate("Что важно\nКлюч кладём в .env, не в чат", DESIGN, "card", frame_size=FRAME,
                     where="top-right", out=self.tmp / "карточка.png")
        _, (x0, y0, x1, y1) = opaque_box(card)
        self.assertGreater(x0, FRAME[0] / 2)
        self.assertLess(y1, FRAME[1] / 2)
        self.assertLess(x1 - x0, FRAME[0] * 0.4)  # smaller scale than the picture
        with Image.open(card) as img:
            r, g, b, a = img.getpixel((x0 + 8, y1 - 8))
        self.assertLess(max(r, g, b), 60)
        self.assertTrue(120 < a < 250)

    def test_opposite_corner_of_a_face_window(self):
        from runtime.render import opposite_corner

        self.assertEqual(opposite_corner({"x": 1488, "y": 648, "w": 408, "h": 408}, FRAME), "top-left")
        self.assertEqual(opposite_corner({"x": 40, "y": 40, "w": 300, "h": 300}, FRAME), "bottom-right")

    def test_vertical_frame_keeps_plates_inside_the_safe_zone(self):
        from runtime.render import plate

        out = plate("Подписывайтесь", DESIGN, "caption", frame_size=(1080, 1920), out=self.tmp / "9x16.png")
        _, (_, _, _, y1) = opaque_box(out)
        self.assertLessEqual(y1, 1920 * 0.8)  # getbbox's bottom is exclusive


if __name__ == "__main__":
    unittest.main()
