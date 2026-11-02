import unittest

import _support  # noqa: F401  (puts the skill on sys.path)


class ReplaceTaste(unittest.TestCase):
    def profile(self):
        from aelib import profiles

        return profiles.add_taste(profiles.add_taste({}, "ускорено на 5%", date="2026-11-01"), "плашка мельче", date="2026-11-01")

    def test_the_old_line_gives_way_to_the_new_one(self):
        from aelib import profiles

        notes = [row["note"] for row in profiles.replace_taste(self.profile(), "5%", "ускорено на 7%")["taste"]]
        self.assertEqual(notes, ["плашка мельче", "ускорено на 7%"])

    def test_no_line_or_several_lines_are_refused(self):
        from aelib import profiles

        with self.assertRaises(ValueError):
            profiles.replace_taste(self.profile(), "нет такой", "x")
        with self.assertRaises(ValueError):
            profiles.replace_taste(self.profile(), "а", "x")


if __name__ == "__main__":
    unittest.main()
