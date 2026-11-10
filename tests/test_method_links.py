"""Every local handbook link shipped with the parent resolves inside its bundle."""
import re
import unittest
from urllib.parse import unquote

from _support import SKILL


class MethodLinks(unittest.TestCase):
    def test_internal_links_stay_in_the_installed_skill_bundle(self):
        for source in sorted((SKILL / "references").glob("*.md")):
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", source.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                rel = unquote(target.split("#", 1)[0].strip("<>"))
                resolved = (source.parent / rel).resolve()
                with self.subTest(source=source.name, link=target):
                    self.assertTrue(resolved.is_relative_to(SKILL.resolve()), target)
                    self.assertTrue(resolved.is_file(), target)
