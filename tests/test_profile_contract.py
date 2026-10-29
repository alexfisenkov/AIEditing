"""What the interview may put into a profile is exactly what the pipeline does: steps, keys, presets, texts."""
import json
import re
import subprocess
import sys
import unittest

from _support import ROOT, SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))

CATALOG = json.loads((SKILL / "catalog" / "steps.json").read_text(encoding="utf-8"))
PRESETS = SKILL / "templates" / "profiles"
NOT_BUILT = ("graphics", "behind_head")  # named in the step vocabulary, not done by the runtime yet


def read(path):
    return path.read_text(encoding="utf-8")


def preset(name):
    return json.loads(read(PRESETS / (name + ".json")))


def params_read_by_pipeline():
    """Every profile key the pipeline code reads: ctx.p("<key>", ...)."""
    names = set()
    for path in (SKILL / "runtime" / "pipelines").glob("*.py"):
        names.update(re.findall(r'ctx\.p\("([a-z_0-9]+)"', read(path)))
    return names


def interview_rows():
    rows = [line for line in read(SKILL / "phases" / "interview.md").splitlines() if line.startswith("| ")]
    return rows[2:]  # header and rule


class StepVocabulary(unittest.TestCase):
    def test_catalog_steps_are_the_pipeline_steps(self):
        from runtime.pipelines import STEPS

        self.assertEqual(sorted(CATALOG["steps"]), sorted(STEPS))

    def test_lesson_preset_checks_the_words_after_the_cut(self):
        self.assertIn("verify_words", preset("lesson")["steps"])

    def test_layout_and_movement_come_into_steps_from_the_interview(self):
        row = next(r for r in interview_rows() if r.startswith("| Layout"))
        for step in ("detect_layout", "motion"):
            self.assertIn("`{}`".format(step), row)

    def test_steps_not_built_install_nothing_and_are_not_offered(self):
        from aelib import catalog

        self.assertEqual(catalog.needs(list(NOT_BUILT), "command")["tools"], [])
        for step in NOT_BUILT:
            self.assertTrue(CATALOG["steps"][step].get("not_built"), step)
        for name in ("interview.md", "refine.md"):
            text = read(SKILL / "phases" / name)
            for word in ("HyperFrames", "Remotion", "«за головой»") + tuple("`{}`".format(s) for s in NOT_BUILT):
                self.assertNotIn(word, text, "{} offers {}".format(name, word))

    def test_readmes_say_the_heavy_layers_are_not_there_yet(self):
        for name, mark in (("README.md", "not yet"), ("README.ru.md", "пока нет")):
            for line in read(ROOT / name).splitlines():
                if "HyperFrames" in line and line.startswith("|") or "Remotion + " in line:
                    self.assertIn(mark, line, "{}: {}".format(name, line))


class ProfileKeys(unittest.TestCase):
    def test_every_key_of_the_interview_table_is_read_by_the_pipeline(self):
        read_keys = params_read_by_pipeline()
        named = set()
        for row in interview_rows():
            named.update(re.findall(r"`params\.([a-z_0-9]+)`", row))
        self.assertTrue(named)
        self.assertEqual(sorted(named - read_keys), [])

    def test_every_preset_key_is_read_by_the_pipeline(self):
        read_keys = params_read_by_pipeline()
        for path in sorted(PRESETS.glob("*.json")):
            unread = sorted(set(json.loads(read(path))["params"]) - read_keys)
            self.assertEqual(unread, [], path.name)


class BuildWithEveryStep(TempDirCase):
    def build(self, steps, approval="plan"):
        profile = {"format": "урок", "skill_name": "монтаж-урок", "language": "ru",
                   "asr": {"provider": "command", "language": "ru", "model": None, "base_url": None,
                           "api_key_env": None, "command": ["нет"]},
                   "steps": steps, "params": {}, "approval": approval, "design": "design/", "taste": [],
                   "output_dir": "выпуски"}
        folder = self.tmp / "work" / "монтаж-урок"
        folder.mkdir(parents=True)
        (folder / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(SKILL / "tools" / "ae.py"), "build-skill",
                               str(folder / "profile.json"), str(self.tmp / "out")],
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return self.tmp / "out" / "монтаж-урок"

    def test_lesson_with_layout_movement_and_second_listening_builds(self):
        steps = ["detect_layout", "speech_spans", "cut_spans", "motion", "verify_words", "drift_ms"]
        skill = self.build(steps)
        text = read(skill / "SKILL.md")
        for step in steps:
            self.assertIn("`{}`".format(step), text)
        self.assertTrue((skill / "runtime" / "look" / "__init__.py").is_file(), "detect_layout needs look")

    def test_parts_approval_promises_nothing_the_pipeline_does_not_do(self):
        text = read(self.build(["speech_spans", "cut_spans"], approval="parts") / "SKILL.md")
        self.assertNotIn("approved before the next", text)
        self.assertIn("not built yet", text)


if __name__ == "__main__":
    unittest.main()
