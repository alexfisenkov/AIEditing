"""The parent's path holds together, and it opens in every agent: Claude Code, Codex, Cursor, Gemini CLI, OpenClaw."""
import ast
import re
import sys
import unittest

from _support import ROOT, SKILL

sys.path.insert(0, str(SKILL / "tools"))


def read(*parts):
    return SKILL.joinpath(*parts).read_text(encoding="utf-8")


def flat(text):
    return " ".join(text.split())


def description(text):
    head = text.split("---")[1]
    return re.search(r"(?m)^description: (.*)$", head).group(1)


class Agents(unittest.TestCase):
    def test_codex_does_not_call_the_workshop_by_itself(self):
        text = read("agents", "openai.yaml")
        self.assertRegex(text, r"(?m)^policy:\n\s+allow_implicit_invocation: false$")

    def test_the_description_says_how_each_agent_calls_it_and_stays_valid_yaml(self):
        line = description(read("SKILL.md"))
        self.assertNotIn(": ", line)  # a plain YAML scalar breaks on a colon and a space
        self.assertNotIn("Starts only on /aiediting", line)
        for call in ("/aiediting", "$aiediting", "/skill aiediting", "Gemini CLI"):
            self.assertIn(call, line, call)
        self.assertIn("/aiediting", line[:160])
        self.assertLess(len(line), 1024)

    def test_skill_md_names_its_folder_where_agents_fill_it_in(self):
        text = read("SKILL.md")
        self.assertIn("${CLAUDE_SKILL_DIR}", text)
        self.assertIn("{baseDir}", text)

    def test_the_tool_is_looked_for_in_the_project_first_and_in_every_agent(self):
        text = read("phases", "start.md")
        block = text.split("```bash", 1)[1].split("```", 1)[0]
        self.assertLess(block.index(" .agents/skills"), block.index("~/.agents/skills"))
        for root in ("~/.openclaw/skills", "~/.gemini/skills", "~/.codex/skills", " skills "):
            self.assertIn(root, block, root)
        self.assertIn("folder of the `SKILL.md` you loaded", text)

    def test_a_format_skill_says_what_and_when_first_and_how_openclaw_calls_it(self):
        from aelib import skillmd

        profile = {"format": "урок", "skill_name": "монтаж-урок", "steps": []}
        self.assertIn("«смонтируй как урок»", skillmd._description(profile)[:150])
        self.assertIn("/skill {{name}}", read("templates", "format-skill", "SKILL.md.tmpl"))

    def test_both_readmes_name_gemini_and_openclaw(self):
        for name in ("README.md", "README.ru.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            for mark in ("Gemini CLI", "OpenClaw", "-a gemini-cli", "-a openclaw", "/skill aiediting", "/skill монтаж-урок",
                         "AIEDITING_NO_UPDATE_CHECK"):
                self.assertIn(mark, text, "{}: {}".format(name, mark))


class ThePath(unittest.TestCase):
    def test_the_plan_comes_after_the_environment_and_starts_with_the_choice(self):
        text = read("phases", "start.md")
        plan = text.split("**The personal plan.**", 1)[1].split("```", 2)[1]
        self.assertNotIn("DaVinci", plan)  # offered once, in the interview
        self.assertNotIn("пробного монтажа", plan)
        self.assertIn("новый скилл", plan)
        self.assertNotIn("лог-профиль", text)
        self.assertIn("обо-мне/блог.md", text)

    def test_later_phases_take_the_intro_instead_of_asking(self):
        for phase in ("formats.md", "interview.md", "design.md", "trial.md", "refine.md"):
            self.assertIn("ae.py intro", read("phases", phase), phase)

    def test_the_interview_says_which_themes_a_format_asks(self):
        text = read("phases", "interview.md")
        self.assertIn("## Which themes this format asks", text)
        self.assertNotIn("Chosen means proved", text)
        self.assertIn("«The proof, by a fact» above", text)
        self.assertIn("refuses without one", flat(text))  # stock lives in the library

    def test_the_library_is_described_after_the_first_trial_and_cameras_are_tried(self):
        text = flat(read("phases", "trial.md"))
        self.assertIn('--camera "<file>"', text)
        self.assertIn("begin the description now", text)
        self.assertIn("ask it now, once", text)

    def test_a_refinement_offers_what_is_new_as_a_list(self):
        self.assertIn("offered as a list to pick from", flat(read("phases", "refine.md")))

    def test_one_camera_is_one_rule(self):
        self.assertIn("One camera: no `angles`, as before", read("phases", "interview.md"))
        self.assertIn("on one camera, only when they asked for changes of crop and a push-in", read("phases", "no-questions.md"))

    def test_the_toolbox_knows_the_inserts_and_names_no_outside_editor(self):
        text = read("references", "toolbox.md")
        self.assertNotIn("Final Cut", text)
        self.assertNotIn("no universal B-roll selector", text)

    def test_the_way_back_to_a_refinement_is_a_call_that_starts_the_workshop(self):
        for path in (SKILL / "SKILL.md", ROOT / "README.md", ROOT / "README.ru.md", ROOT / "CHANGELOG.md"):
            self.assertNotIn("«доработай монтаж-<слово>»", path.read_text(encoding="utf-8"), path.name)
        tmpl = flat(read("templates", "format-skill", "SKILL.md.tmpl"))
        self.assertIn("«Мастерская обновилась до …»", tmpl)
        self.assertIn("go on editing", tmpl)
        self.assertIn("ae.py intro apply <skill>", read("phases", "trial.md"))

    def test_the_head_of_ae_py_names_every_command(self):
        from aelib.cli import parser

        doc = ast.get_docstring(ast.parse(read("tools", "ae.py")))
        for name in parser()._subparsers._group_actions[0].choices:
            self.assertRegex(doc, r"(?<![\w-]){}(?![\w-])".format(re.escape(name)), name)


if __name__ == "__main__":
    unittest.main()
