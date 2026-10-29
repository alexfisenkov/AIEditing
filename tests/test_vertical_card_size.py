"""A card on a 9:16 frame is as readable as on 16:9: sizes from the short side, width from the long one."""
import importlib.util
import unittest
from unittest import mock

from _support import SKILL, TempDirCase

HAVE_PIL = importlib.util.find_spec("PIL") is not None
DESIGN = SKILL / "design" / "chrome-graphite"
PORTRAIT, WIDE = (1080, 1920), (1920, 1080)
TEXT = "Почти не тратит токены\nвашего ИИ-агента"
LONG = "Любые агрегаторы нейросетей\nHiggsfield · Syntx · Magnific и все остальные, что только бывают"
FACE = {"x": 350, "y": 630, "w": 520, "h": 770}  # head and shoulders of a talking head, 1080x1920


def box(path):
    from PIL import Image

    with Image.open(str(path)) as img:
        return img.getchannel("A").getbbox()


def meets(box_, face):
    x0, y0, x1, y1 = box_
    return x0 < face["x"] + face["w"] and face["x"] < x1 and y0 < face["y"] + face["h"] and face["y"] < y1


def vertical_design():
    """The design as a 9:16 run uses it: the platforms' shared safe zone on top of the design's own."""
    from runtime.media.export import safe_zone
    from runtime.render import load_design

    d = dict(load_design(DESIGN))
    mine = d["video"]["safe_zone_vertical"]
    d["video"] = dict(d["video"], safe_zone_vertical={k: max(float(mine.get(k, 0)), v)
                                                      for k, v in safe_zone().items()})
    return d


@unittest.skipUnless(HAVE_PIL, "Pillow not installed (ae.py doctor installs it)")
class VerticalCardSize(TempDirCase):
    def test_a_vertical_card_is_as_large_as_a_horizontal_one(self):
        from runtime.render import plate

        tall = box(plate(TEXT, DESIGN, "card", frame_size=PORTRAIT, out=self.tmp / "9x16.png"))
        wide = box(plate(TEXT, DESIGN, "card", frame_size=WIDE, out=self.tmp / "16x9.png"))
        self.assertAlmostEqual(tall[2] - tall[0], wide[2] - wide[0], delta=3)
        self.assertAlmostEqual(tall[3] - tall[1], wide[3] - wide[1], delta=3)
        self.assertGreater(tall[2] - tall[0], PORTRAIT[0] * 0.45, "a narrow strip again")

    def test_horizontal_card_is_as_before(self):
        from runtime.render import plate

        got = box(plate(TEXT, DESIGN, "card", frame_size=WIDE, out=self.tmp / "прежняя.png"))
        self.assertEqual(got, (48, 48, 569, 201))  # measured before the change

    def test_no_ellipsis_for_a_long_title_and_a_two_line_explanation(self):
        from runtime.render import plate
        from runtime.render.panel import wrap

        seen = []

        def spy(fnt, text, max_px, max_lines):
            lines = wrap(fnt, text, max_px, max_lines)
            seen.append(lines)
            return lines

        for k, text in enumerate((TEXT, LONG)):
            seen.clear()
            with mock.patch("runtime.render.plate.wrap", spy):
                plate(text, DESIGN, "card", frame_size=PORTRAIT, out=self.tmp / "{}.png".format(k))
            self.assertEqual(len(seen), 2, "title and explanation are wrapped separately")
            self.assertFalse([ln for lines in seen for ln in lines if "…" in ln], seen)
        self.assertLessEqual(len(seen[1]), 3)

    def test_card_is_in_the_safe_zone_off_the_face_and_off_the_caption_strip(self):
        from runtime.render import plate

        design, w, h = vertical_design(), *PORTRAIT
        zone = design["video"]["safe_zone_vertical"]
        card = box(plate(TEXT, design, "card", frame_size=PORTRAIT, where="top-left", out=self.tmp / "к.png"))
        caption = box(plate("часть работы, когда у", design, "caption", frame_size=PORTRAIT,
                            out=self.tmp / "с.png"))
        self.assertGreaterEqual(card[0], zone["side"] * w - 1)
        self.assertLessEqual(card[2], w - zone["side"] * w + 1)
        self.assertGreaterEqual(card[1], zone["top"] * h - 1)
        self.assertLessEqual(card[3], h - zone["bottom"] * h + 1)
        self.assertFalse(meets(card, FACE), "the card is on the face")
        self.assertFalse(meets(card, dict(x=caption[0], y=caption[1], w=caption[2] - caption[0],
                                          h=caption[3] - caption[1])), "the card is on the caption strip")


if __name__ == "__main__":
    unittest.main()
