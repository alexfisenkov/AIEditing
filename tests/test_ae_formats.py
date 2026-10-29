"""Answer to «which formats?»: list items by number or word, plus your own through commas."""
import unittest

import _support  # noqa: F401  (paths)
from _support import SKILL

import sys

sys.path.insert(0, str(SKILL / "tools"))


class ParseFormats(unittest.TestCase):
    def parse(self, answer):
        from aelib.formats import parse_answer

        return parse_answer(answer)

    def test_list_words_and_own_through_commas(self):
        got = self.parse("эфир, урок, подкаст")
        self.assertEqual([f["word"] for f in got], ["эфир", "урок", "подкаст"])
        self.assertEqual([f["custom"] for f in got], [False, False, True])
        self.assertEqual(got[2]["skill"], "монтаж-подкаст")
        self.assertEqual(got[2]["preset"], "custom")
        self.assertEqual(got[0]["preset"], "stream")

    def test_numbers_from_the_offered_list(self):
        got = self.parse("1, 3 и интервью с гостем")
        self.assertEqual([f["word"] for f in got], ["эфир", "youtube", "интервью-с-гостем"])
        self.assertEqual(got[2]["skill"], "монтаж-интервью-с-гостем")

    def test_case_duplicates_and_prefix(self):
        got = self.parse("Урок; урок\nмонтаж-Вертикаль")
        self.assertEqual([f["skill"] for f in got], ["монтаж-урок", "монтаж-вертикаль"])

    def test_empty_answer_is_refused(self):
        with self.assertRaises(ValueError):
            self.parse(" , ;")

    def test_number_outside_list_is_refused(self):
        with self.assertRaises(ValueError):
            self.parse("9")

    def test_own_format_goes_the_same_path_as_a_listed_one(self):
        from aelib.profiles import new_profile
        from runtime.profile import check_profile

        own, listed = self.parse("подкаст, урок")
        for fmt in (own, listed):
            profile = new_profile(fmt)
            self.assertEqual(check_profile(profile), [], fmt["word"])
            self.assertEqual(profile["skill_name"], fmt["skill"])
            self.assertTrue(profile["steps"])


if __name__ == "__main__":
    unittest.main()
