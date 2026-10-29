"""The Chrome & Graphite example: tokens complete, fonts only under an open licence, nothing private inside."""
import json
import re
import unittest

from _support import SKILL

DESIGN = SKILL / "design" / "chrome-graphite"
OPEN_FONT_LICENCES = {"OFL-1.1", "Apache-2.0", "MIT"}


class ChromeGraphite(unittest.TestCase):
    def setUp(self):
        self.tokens = json.loads((DESIGN / "tokens.json").read_text(encoding="utf-8"))

    def test_tokens_have_colours_fonts_radii_and_video_layer(self):
        for key in ("color", "font", "radius", "video", "rules"):
            self.assertIn(key, self.tokens)
        for kind in ("chapter", "caption", "card"):
            self.assertIn(kind, self.tokens["video"])
            self.assertGreaterEqual(len(self.tokens["video"]["variants"][kind]), 3)
        self.assertTrue((DESIGN / "rules.md").is_file())

    def test_colour_references_resolve(self):
        palette = self.tokens["color"]
        for kind in ("chapter", "caption", "card"):
            spec = self.tokens["video"][kind]
            for variant in [spec] + self.tokens["video"]["variants"][kind]:
                for key in ("bg", "fg", "line", "body_fg", "stroke_color"):
                    if key in variant:
                        self.assertIn(variant[key], palette, (kind, key))

    def test_every_font_file_is_openly_licensed_and_has_its_licence_text(self):
        files = sorted((DESIGN / "fonts").glob("*.[ot]tf"))
        self.assertTrue(files)
        declared = {_basename(spec["file"]): spec for spec in self.tokens["font"].values()}
        for font in files:
            self.assertIn(font.name, declared, "font file not declared in tokens: " + font.name)
            self.assertIn(declared[font.name]["license"], OPEN_FONT_LICENCES)
            licence = DESIGN / "fonts" / "OFL-{}.txt".format(font.stem)
            self.assertTrue(licence.is_file(), "no licence text for " + font.name)
            self.assertIn("Open Font License", licence.read_text(encoding="utf-8"))

    def test_nothing_private_inside(self):
        private = re.compile(r"/Users/|C:\\\\Users|@[A-Za-z0-9-]+\.[a-z]{2,}|sk-[A-Za-z0-9]{8}|gh[pousr]_|"
                             r"\.env\b", re.IGNORECASE)
        for path in DESIGN.rglob("*"):
            if path.suffix in (".json", ".md"):
                text = path.read_text(encoding="utf-8")
                self.assertIsNone(private.search(text), (path.name, private.search(text)))
            self.assertIn(path.suffix, (".json", ".md", ".ttf", ".otf", ".txt", ""), path.name)


def _basename(rel):
    return rel.rsplit("/", 1)[-1]


if __name__ == "__main__":
    unittest.main()
