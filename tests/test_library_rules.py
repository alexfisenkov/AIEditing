"""Personal rules, the «never» list and the search of inserts under a phrase."""
import datetime as dt
import unittest

from test_library_paths import LibraryCase

DAY = dt.date(2026, 11, 13)


class Rules(LibraryCase):
    def setUp(self):
        super().setUp()
        from runtime.library.paths import set_library

        self.lib = set_library(self.tmp / "библиотека")

    def test_a_rule_goes_with_its_date_into_the_general_or_the_format_section(self):
        from runtime.library import rules

        rules.add_rule(self.lib, "паузы  короче", today=DAY)
        rules.add_rule(self.lib, "без музыки", fmt="урок", video="2026-11-13-тема", today=DAY)
        rules.add_rule(self.lib, "вставки чаще", fmt="влог", today=DAY)
        rules.add_rule(self.lib, "титры крупнее", today=DAY)
        text = (self.lib / "правила.md").read_text(encoding="utf-8")
        self.assertIn("- 2026-11-13: паузы короче", text)
        self.assertIn("- 2026-11-13 · 2026-11-13-тема: без музыки", text)
        self.assertLess(text.index("паузы короче"), text.index("титры крупнее"))
        self.assertLess(text.index("титры крупнее"), text.index("## Формат: урок"))
        lesson = rules.rules_text(self.lib, "урок")
        self.assertIn("паузы короче", lesson)
        self.assertIn("без музыки", lesson)
        self.assertNotIn("вставки чаще", lesson)
        self.assertNotIn("без музыки", rules.rules_text(self.lib, "влог"))

    def test_an_empty_rule_is_refused(self):
        from runtime.library import rules
        from runtime.library.paths import LibraryError

        with self.assertRaises(LibraryError):
            rules.add_rule(self.lib, "   ")

    def test_forbid_writes_once_and_forbidden_reads_it_back(self):
        from runtime.library import rules

        rules.forbid(self.lib, "Петю")
        rules.forbid(self.lib, "петю")
        rules.forbid(self.lib, "кадры с пляжа")
        self.assertEqual(rules.forbidden(self.lib), ["Петю", "кадры с пляжа"])
        self.assertIn("Петю", (self.lib / "чего-нельзя.md").read_text(encoding="utf-8"))


ROWS = [
    {"f": "фото/море.jpg", "what": "закат на море", "tags": ["море", "закат"], "phrases": ["отпуск на море"],
     "who": [], "date": "2019-07-14", "never": False},
    {"f": "фото/петя.jpg", "what": "Петя у моря", "tags": ["море"], "phrases": ["отпуск на море"],
     "who": ["Петя"], "date": "2019-07-15", "never": False},
    {"f": "фото/тайное.jpg", "what": "море ночью", "tags": ["море"], "phrases": ["отпуск на море"],
     "who": [], "date": "2019-07-16", "never": True},
    {"f": "фото/горы.jpg", "what": "горы", "tags": ["горы"], "phrases": ["поход"], "who": [], "date": "2021-08-01",
     "never": False},
    {"f": "фото/море2015.jpg", "what": "море", "tags": [], "phrases": [], "who": [], "date": "2015-06-01",
     "never": False},
]


class Search(unittest.TestCase):
    def test_candidates_match_the_phrase_by_phrases_tags_and_what(self):
        from runtime.library.search import candidates

        found = [r["f"] for r in candidates(ROWS, "Мы поехали в отпуск на море", None)]
        self.assertEqual(found[0], "фото/море.jpg")
        self.assertNotIn("фото/горы.jpg", found)
        self.assertNotIn("фото/тайное.jpg", found)  # «never» is never offered

    def test_people_from_the_never_list_are_left_out_in_any_word_form(self):
        from runtime.library.search import candidates

        found = [r["f"] for r in candidates(ROWS, "отпуск на море", None, forbidden=["Петю не брать"])]
        self.assertNotIn("фото/петя.jpg", found)
        self.assertIn("фото/море.jpg", found)

    def test_a_banned_first_name_leaves_out_the_full_name(self):
        from runtime.library.search import candidates

        rows = [{"f": "а.jpg", "what": "рыбалка", "who": ["Петя Иванов"]}, {"f": "б.jpg", "what": "рыбалка"}]
        self.assertEqual([r["f"] for r in candidates(rows, "рыбалка", None, forbidden=["Петя"])], ["б.jpg"])
        self.assertEqual([r["f"] for r in candidates(rows, "рыбалка", None, forbidden=["Петю не брать"])], ["б.jpg"])

    def test_a_two_letter_name_is_banned_too(self):
        from runtime.library.search import candidates

        rows = [{"f": "а.jpg", "what": "рыбалка", "who": ["Ян"]}, {"f": "б.jpg", "what": "рыбалка", "who": ["Анна"]}]
        self.assertEqual([r["f"] for r in candidates(rows, "рыбалка", None, forbidden=["Ян"])], ["б.jpg"])

    def test_a_banned_name_does_not_touch_a_longer_word_that_starts_the_same(self):
        from runtime.library.search import candidates

        rows = [{"f": "а.jpg", "what": "набережная", "tags": ["Петербург"]}]
        self.assertEqual([r["f"] for r in candidates(rows, "набережная", None, forbidden=["Петя"])], ["а.jpg"])

    def test_a_ban_in_another_case_closes_the_name_with_a_fleeting_vowel_or_a_yo(self):
        from runtime.library.search import candidates

        for ban, name in (("Павла", "Павел"), ("Льва", "Лев"), ("Петра", "Пётр"), ("Артёма", "Артем"),
                          ("Пётр", "Петр"), ("Федю", "Фёдор"), ("Павла не брать", "Павел Сидоров")):
            rows = [{"f": "а.jpg", "what": "рыбалка", "who": [name]}, {"f": "б.jpg", "what": "рыбалка"}]
            found = [r["f"] for r in candidates(rows, "рыбалка", None, forbidden=[ban])]
            self.assertEqual(found, ["б.jpg"], "{} → {}".format(ban, name))

    def test_a_fleeting_vowel_does_not_close_another_word(self):
        from runtime.library.search import candidates

        for ban, name in (("Олег", "Ольга"), ("Ольгу", "Олег"), ("Павел", "павлин"), ("Льва", "Ольга")):
            rows = [{"f": "а.jpg", "what": "рыбалка", "who": [name]}]
            found = [r["f"] for r in candidates(rows, "рыбалка", None, forbidden=[ban])]
            self.assertEqual(found, ["а.jpg"], "{} ↛ {}".format(ban, name))

    def test_the_year_lifts_a_file_of_that_year(self):
        from runtime.library.search import candidates

        found = [r["f"] for r in candidates(ROWS, "море", 2015)]
        self.assertEqual(found[0], "фото/море2015.jpg")

    def test_limit_and_nothing_found(self):
        from runtime.library.search import candidates

        self.assertEqual(len(candidates(ROWS, "отпуск на море", None, limit=1)), 1)
        self.assertEqual(candidates(ROWS, "квантовая физика", None), [])


if __name__ == "__main__":
    unittest.main()
