"""The texts the agent and the person read: phases exist, instructions in English, the rules and README promises."""
import re
import sys
import unittest

from _support import ROOT, SKILL

sys.path.insert(0, str(SKILL / "tools"))

PHASES = ["start", "formats", "sources", "interview", "design", "trial", "build", "refine", "resume"]
CYR = re.compile(r"[А-Яа-яЁё]")
LAT = re.compile(r"[A-Za-z]")


def read(path):
    return path.read_text(encoding="utf-8")


def cyrillic_share(text):
    plain = re.sub(r"```.*?```", "", text, flags=re.S)          # examples for the person are Russian
    plain = re.sub(r"«[^»]*»|`[^`]*`", "", plain)               # quoted words the person sees
    cyr, lat = len(CYR.findall(plain)), len(LAT.findall(plain))
    return cyr / max(1, cyr + lat)


class SkillTexts(unittest.TestCase):
    def test_every_phase_named_in_skill_md_exists(self):
        text = read(SKILL / "SKILL.md")
        for name in PHASES:
            self.assertIn("phases/{}.md".format(name), text)
            self.assertTrue((SKILL / "phases" / (name + ".md")).is_file(), name)
        for ref in re.findall(r"prompts/[\w-]+\.md", text):
            self.assertTrue((SKILL / ref).is_file(), ref)

    def test_skill_md_states_what_it_never_does(self):
        text = read(SKILL / "SKILL.md").lower()
        for phrase in ("never publishes", "never voices", "never generates"):
            self.assertIn(phrase, text)

    def test_instructions_are_english(self):
        files = [SKILL / "SKILL.md"] + sorted((SKILL / "phases").glob("*.md")) + sorted((SKILL / "prompts").glob("*.md"))
        files.append(SKILL / "templates" / "format-skill" / "SKILL.md.tmpl")
        for path in files:
            self.assertLess(cyrillic_share(read(path)), 0.2, path.name)

    def test_commands_named_in_phases_exist(self):
        from aelib.cli import parser

        known = set(parser()._subparsers._group_actions[0].choices)
        for path in list((SKILL / "phases").glob("*.md")) + [SKILL / "SKILL.md"]:
            for cmd in re.findall(r"ae\.py\"? ([a-z][a-z-]+)", read(path)):
                self.assertIn(cmd, known, "{}: {}".format(path.name, cmd))


class Readme(unittest.TestCase):
    def test_both_readmes_keep_the_promises(self):
        for name in ("README.md", "README.ru.md"):
            text = read(ROOT / name)
            self.assertIn("npx skills add alexfisenkov/AIEditing -g", text, name)
            self.assertIn("npx skills update aiediting -g", text, name)
            self.assertIn("Remotion", text, name)
            self.assertIn("OpenMontage", text, name)
            self.assertIn("Scribe", text, name)
            self.assertNotIn("kinetic", text.lower(), name)

    def test_same_sections_in_both_languages(self):
        heads = [re.findall(r"(?m)^## ", read(ROOT / n)) for n in ("README.md", "README.ru.md")]
        self.assertEqual(len(heads[0]), len(heads[1]))


if __name__ == "__main__":
    unittest.main()
