"""The texts of the library, inserts, timeline, voice, music, publishing, cameras and preparation: asked by choice, proved, worded for a format skill."""
import datetime as dt
import json
import re
import subprocess
import sys
import unittest

from _support import ROOT, SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))

AE = SKILL / "tools" / "ae.py"
NEW_KEYS = ("broll", "timeline", "voice", "music", "sfx", "cleanup", "repeats")
NEW_STEPS = ("broll", "timeline", "voice_clean", "publish_pack", "angles")
METHODS = {"library.md": "The person's library", "broll.md": "Inserts from their life", "sound.md": "Voice, music and sounds",
           "publish.md": "The publishing pack", "timeline.md": "The timeline file", "angles.md": "Several cameras",
           "prep.md": "Preparation before a shoot", "help.md": "How to give remarks"}


def read(*parts):
    return SKILL.joinpath(*parts).read_text(encoding="utf-8")


def rows():
    return [line for line in read("phases", "interview.md").splitlines() if line.startswith("| ")][2:]


class Meeting(unittest.TestCase):
    def test_the_start_meets_the_person_in_one_message_and_explains_the_library(self):
        text = read("phases", "start.md")
        # the environment is checked before the plan, and the plan's first step is the choice of new or refine
        self.assertLess(text.index("## 3. Check the environment"), text.index("## 4. Get to know the person"))
        self.assertLess(text.index("## 4. Get to know the person"), text.index("## 5. The first question: create or refine"))
        self.assertIn("ae.py intro set", text)
        for mark in ("one message", "personal plan", "ae.py library set", "Auphonic", "DaVinci", "«Нет» or silence", "never invented",
                     "Never ask twice", "может, ещё сделать побольше"):
            self.assertIn(mark, " ".join(text.split()), mark)
        self.assertNotIn("Final Cut", text)

    def test_the_interview_has_a_row_for_every_new_key_and_step_and_proves_the_choice(self):
        from runtime.pipelines import STEPS

        table = "\n".join(rows())
        for key in NEW_KEYS:
            self.assertIn("`params.{}`".format(key), table, key)
        for step in NEW_STEPS:
            self.assertIn("`{}`".format(step), table, step)
            self.assertIn(step, STEPS)
        text = read("phases", "interview.md")
        for mark in ("Everything new is by choice, and what is chosen is proved", "a key is never asked for", "ae.py voice-try",
                     "ae.py library status", "`overlay.py sfxcat <folder>`", "осталось сделать", "Nothing at all → no music"):
            self.assertIn(mark.lower(), " ".join(text.split()).lower(), mark)
        self.assertNotIn("Final Cut", text)

    def test_no_questions_refine_and_build_know_the_new(self):
        nq = read("phases", "no-questions.md")
        self.assertIn("What of the new is already set up", nq)
        self.assertIn("a key that merely lies on the disk does not choose it", nq)
        self.assertIn("правила.md", nq)
        self.assertIn("`run.py note --format`", read("phases", "refine.md"))
        self.assertIn("proved by a fact", read("phases", "build.md"))
        self.assertIn("Everything new is by choice", read("SKILL.md"))
        self.assertIn("own rules", read("SKILL.md"))

    def test_the_readmes_and_the_env_example_name_the_new_keys(self):
        for name in ("README.md", "README.ru.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            for word in ("AUPHONIC_API_KEY", "PEXELS_API_KEY", "run.py prep", "run.py covers", "sfxcat", "DaVinci"):
                self.assertIn(word, text, name + " " + word)
            self.assertNotIn("Final Cut Pro", text)
        env = (ROOT / ".env.example").read_text(encoding="utf-8")
        for key in ("AUPHONIC_API_KEY=", "PEXELS_API_KEY=", "PIXABAY_API_KEY="):
            self.assertIn(key, env)


class Methods(unittest.TestCase):
    def render(self, steps, params=None):
        from aelib import skillmd

        profile = {"format": "ф", "skill_name": "монтаж-ф", "language": "ru", "asr": {"provider": "whispercpp"},
                   "steps": steps, "params": params or {}, "taste": []}
        text = skillmd.render(profile, {"tools": []}, {"steps": {s: {"what": "x"} for s in steps}}, {}, "0")
        self.assertNotIn("{{", text)
        return text

    def test_every_method_file_is_wired_and_in_english(self):
        from aelib import skillmd

        for name, head in METHODS.items():
            self.assertIn(name, skillmd.METHOD_IF)
            body = read("templates", "format-skill", "method", name)
            self.assertTrue(body.startswith("## " + head), name)
            plain = re.sub(r"```.*?```|«[^»]*»|`[^`]*`", "", body, flags=re.S)
            cyr, lat = len(re.findall(r"[А-Яа-яЁё]", plain)), len(re.findall(r"[A-Za-z]", plain))
            self.assertLess(cyr / max(1, cyr + lat), 0.2, name)

    def test_a_format_without_the_new_steps_gets_none_of_the_new_methods(self):
        text = self.render(["speech_spans", "cut_spans"])
        for head in list(METHODS.values())[:-1]:
            self.assertNotIn("## " + head, text, head)
        self.assertIn("## How to give remarks", text)
        self.assertNotIn("run.py\" covers", text)
        self.assertNotIn("run.py\" prep", text)

    def test_each_method_comes_with_its_own_step_only(self):
        for step, head in (("broll", "The person's library"), ("broll", "Inserts from their life"), ("voice_clean", "Voice, music and sounds"),
                           ("music", "Voice, music and sounds"), ("publish_pack", "The publishing pack"), ("timeline", "The timeline file"),
                           ("angles", "Several cameras")):
            text = self.render(["speech_spans", step])
            self.assertIn("## " + head, text, step)
            others = [h for h in list(METHODS.values())[:-2] if h != head and h != "The person's library" and h != "Inserts from their life"]
            self.assertEqual([h for h in others if "## " + h in text], [], step)
        self.assertIn("## Preparation before a shoot", self.render(["speech_spans"], {"prep": True}))

    def test_the_voice_and_music_parts_follow_their_steps(self):
        voice, music = self.render(["voice_clean"]), self.render(["music"])
        self.assertIn("cleaned by Auphonic", voice)
        self.assertNotIn("**Music** only", voice)
        self.assertIn("**Music** only", music)
        self.assertNotIn("cleaned by Auphonic", music)
        self.assertIn("Auphonic account", voice)

    def test_the_template_reads_the_rules_and_names_covers_and_prep(self):
        tmpl = read("templates", "format-skill", "SKILL.md.tmpl")
        for mark in ("правила.md", "чего-нельзя.md", "run.py\" covers", "run.py\" prep", "beats this format's setting"):
            self.assertIn(mark, tmpl)
        self.assertIn("run.py\" covers", self.render(["speech_spans", "publish_pack"]))
        self.assertIn("run.py\" prep", self.render(["speech_spans"], {"prep": True}))

    def test_the_no_questions_method_names_inserts_and_repeats(self):
        self.assertIn("`broll`: the proposals stand", self.render(["speech_spans", "broll"]))
        self.assertNotIn("`broll`: the proposals stand", self.render(["speech_spans"]))
        self.assertIn("`repeats`", self.render(["speech_spans"]))


class Kit(unittest.TestCase):
    def test_the_recipes_and_the_rules_are_in_the_kit(self):
        recipes = read("overlay-kit", "recipes.md")
        for mark in ("Three levels", "No two identical screens", "Events on the frame of the word", "Away past the edge", "about 15 s",
                     "lower right corner"):
            self.assertIn(mark, recipes, mark)
        brief = read("overlay-kit", "brief-template.md")
        for mark in ("recipes.md", "two identical screens", "about 15 s", "frame of the word"):
            self.assertIn(mark, brief, mark)
        self.assertIn("recipes.md", read("overlay-kit", "README.md"))
        self.assertIn("## Pace, captions and a short from a long video", read("overlay-kit", "vertical.md"))


class PrepCommand(TempDirCase):
    def setUp(self):
        super().setUp()
        folder = self.tmp / "work" / "монтаж-урок"
        folder.mkdir(parents=True)
        profile = {"format": "урок", "skill_name": "монтаж-урок", "language": "ru",
                   "asr": {"provider": "whispercpp", "language": "ru", "model": None, "base_url": None, "api_key_env": None, "command": None},
                   "steps": ["speech_spans", "cut_spans"], "params": {"prep": True}, "approval": "plan", "design": "design/",
                   "taste": [], "output_dir": str(self.tmp / "выпуски")}
        (folder / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        done = subprocess.run([sys.executable, str(AE), "build-skill", str(folder / "profile.json"), str(self.tmp / "out")],
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.skill = self.tmp / "out" / "монтаж-урок"
        (self.skill / "runtime" / "pipelines" / "__init__.py").write_text(
            "def run(src, profile, outdir, approve):\n    return {}\n", encoding="utf-8")

    def run_skill(self, *args):
        return subprocess.run([sys.executable, "-I", str(self.skill / "tools" / "run.py"), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8", cwd=str(self.tmp))

    def issue(self, topic="Тема"):
        return self.tmp / "выпуски" / "{}-{}".format(dt.date.today().isoformat(), topic.lower())

    def test_prep_writes_the_map_the_camera_and_the_checklist_once(self):
        first = self.run_skill("prep", "Тема", "--steps", "9")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        text = (self.issue() / "подготовка.md").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"(?m)^\d+\. \[шаг", text)), 9)
        for mark in ("## Куда поставить камеру", "свободное место", "## Чек-лист перед записью", "хлопок в ладоши"):
            self.assertIn(mark, text)
        (self.issue() / "подготовка.md").write_text("моё", encoding="utf-8")
        second = self.run_skill("prep", "Тема")
        self.assertIn("не перезаписываю", second.stdout)
        self.assertEqual((self.issue() / "подготовка.md").read_text(encoding="utf-8"), "моё")

    def test_a_map_of_six_or_thirteen_steps_is_refused(self):
        for n in ("6", "13"):
            done = self.run_skill("prep", "Тема", "--steps", n)
            self.assertEqual(done.returncode, 2, n)
            self.assertFalse((self.issue() / "подготовка.md").exists())

    def test_a_filled_map_beside_the_source_names_the_chapters(self):
        video = self.tmp / "запись.mp4"
        video.write_bytes(b"x")
        (self.tmp / "подготовка.md").write_text(
            "# П\n\n## Карта ролика\n\n1. Зачем это нужно\n   - а\n2. Как поставить\n   - б\n3. [шаг 3 — впиши название]\n\n## Куда\n\n9. не глава\n",
            encoding="utf-8")
        done = self.run_skill("edit", video, "--topic", "тест")
        self.assertIn("главы ролика по её шагам — Зачем это нужно; Как поставить", done.stdout)
        self.assertNotIn("не глава", done.stdout)
        self.assertNotIn("шаг 3", done.stdout)


if __name__ == "__main__":
    unittest.main()
