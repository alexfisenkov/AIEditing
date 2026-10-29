import re
import unittest

from _support import ROOT, SKILL


def skill_md_version():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    head = text.split("---")[1]
    match = re.search(r'^\s+version:\s*"([^"]+)"', head, re.M)
    return match.group(1) if match else None


def changelog_version():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(r"^## (\S+) — ", text, re.M)
    return match.group(1) if match else None


class VersionInOnePlace(unittest.TestCase):
    def test_skill_md_runtime_and_changelog_agree(self):
        import runtime

        self.assertRegex(runtime.__version__, r"^\d+\.\d+\.\d+$")
        self.assertEqual(skill_md_version(), runtime.__version__)
        self.assertEqual(changelog_version(), runtime.__version__)

    def test_skill_md_names_the_skill(self):
        head = (SKILL / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
        self.assertRegex(head, r"(?m)^name: aiediting$")


if __name__ == "__main__":
    unittest.main()
