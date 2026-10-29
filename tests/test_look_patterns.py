"""Secret-looking text: e-mail, phone, card, API keys, money. Pure regex, no media."""
import unittest

import _support  # noqa: F401  (puts the skill on sys.path)

# Fake keys are glued from parts so that secret scanners do not flag this test file.
FAKE_OPENAI = "sk" + "-proj-" + "Ab12Cd34Ef56Gh78Ij90"
FAKE_GITHUB = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"


def kinds(text):
    from runtime.look.patterns import scan_text

    return [(hit["kind"], hit["text"]) for hit in scan_text(text)]


class Patterns(unittest.TestCase):
    def test_email(self):
        self.assertIn(("email", "test.user@example.com"), kinds("Почта: test.user@example.com, пишите"))

    def test_phone_russian_and_international(self):
        found = kinds("звоните +7 (916) 123-45-67 или 8 916 765 43 21, а также +44 20 7946 0958")
        phones = [t for k, t in found if k == "phone"]
        self.assertEqual(phones, ["+7 (916) 123-45-67", "8 916 765 43 21", "+44 20 7946 0958"])

    def test_card_needs_valid_checksum(self):
        found = kinds("карта 4111 1111 1111 1111 и 1234 5678 9012 3456")
        self.assertIn(("card", "4111 1111 1111 1111"), found)
        self.assertNotIn("1234 5678 9012 3456", [t for k, t in found if k == "card"])

    def test_keys(self):
        found = kinds("ключ {} и токен {}".format(FAKE_OPENAI, FAKE_GITHUB))
        self.assertIn(("key", FAKE_OPENAI), found)
        self.assertIn(("key", FAKE_GITHUB), found)

    def test_money(self):
        found = [t for k, t in kinds("оплата 12 500 ₽, потом $1,200 и 300 рублей, 5 тыс. руб") if k == "money"]
        self.assertEqual(found, ["12 500 ₽", "$1,200", "300 рублей", "5 тыс. руб"])

    def test_plain_text_and_years_are_quiet(self):
        self.assertEqual(kinds("Глава 2. В 2024 году мы открыли 3 потока по 25 человек"), [])


if __name__ == "__main__":
    unittest.main()
