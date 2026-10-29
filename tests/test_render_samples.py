"""Variants of an element drawn on the person's own frame, for choosing on the dashboard."""
import importlib.util
import unittest

from _support import SKILL, TempDirCase

HAVE_PIL = importlib.util.find_spec("PIL") is not None
DESIGN = SKILL / "design" / "chrome-graphite"


@unittest.skipUnless(HAVE_PIL, "Pillow not installed (ae.py doctor installs it)")
class Samples(TempDirCase):
    def setUp(self):
        super().setUp()
        from PIL import Image

        self.frame = self.tmp / "кадр человека.png"
        Image.new("RGB", (1280, 720), (90, 110, 130)).save(self.frame)

    def test_three_or_more_distinct_variants_per_element_on_the_frame(self):
        from PIL import Image, ImageChops

        from runtime.render import samples

        for kind in ("chapter", "caption", "card"):
            shots = samples(DESIGN, self.frame, kind=kind, outdir=self.tmp / kind)
            self.assertGreaterEqual(len(shots), 3, kind)
            images = [Image.open(p).convert("RGB") for p in shots]
            with Image.open(self.frame) as base:
                for img in images:
                    self.assertEqual(img.size, base.size)
                    self.assertIsNotNone(ImageChops.difference(img, base.convert("RGB")).getbbox())
            for i in range(len(images)):
                for j in range(i + 1, len(images)):
                    self.assertIsNotNone(ImageChops.difference(images[i], images[j]).getbbox(), (kind, i, j))

    def test_card_variant_without_own_place_avoids_the_face(self):
        from PIL import Image, ImageChops

        from runtime.render import samples

        face = {"x": 980, "y": 420, "w": 280, "h": 280}  # camera circle bottom-right
        first = samples(DESIGN, self.frame, kind="card", face=face, outdir=self.tmp / "лицо")[0]
        with Image.open(first) as img, Image.open(self.frame) as base:
            x0, y0, x1, y1 = ImageChops.difference(img.convert("RGB"), base.convert("RGB")).getbbox()
        self.assertLess(x1, 640)
        self.assertLess(y1, 360)


if __name__ == "__main__":
    unittest.main()
