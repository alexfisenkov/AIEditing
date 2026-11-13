"""`ae.py build-skill profile.json <dest>` → a self-contained `монтаж-<слово>/` with only what was chosen."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from _support import SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))

AE = SKILL / "tools" / "ae.py"
LESSON_STEPS = ["speech_spans", "cut_spans", "loudnorm", "write_srt"]


def profile_for(word, steps, provider="scribe"):
    return {"format": word, "skill_name": "монтаж-" + word, "language": "ru",
            "asr": {"provider": provider, "language": "ru", "model": "scribe_v2", "base_url": None,
                    "api_key_env": "ELEVENLABS_API_KEY", "command": None},
            "steps": steps, "params": {"gap": 0.5, "pad": 0.12}, "approval": "plan",
            "design": "design/", "taste": [{"date": "2026-10-29", "video": "a.mp4", "note": "паузы короче"}],
            "output_dir": "выпуски"}


class BuildSkill(TempDirCase):
    def write_profile(self, profile):
        folder = self.tmp / "work" / profile["skill_name"]
        (folder / "design").mkdir(parents=True)
        (folder / "design" / "tokens.json").write_text('{"font": "Onest"}', encoding="utf-8")
        path = folder / "profile.json"
        path.write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        return path

    def build(self, profile):
        return subprocess.run([sys.executable, str(AE), "build-skill", str(self.write_profile(profile)),
                               str(self.tmp / "out")], capture_output=True, text=True, encoding="utf-8")

    def test_structure_of_a_built_format_skill(self):
        proc = self.build(profile_for("урок", LESSON_STEPS))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        skill = self.tmp / "out" / "монтаж-урок"
        for rel in ("SKILL.md", "profile.json", "pins.json", "design/tokens.json", "runtime/__init__.py",
                    "runtime/media/__init__.py", "runtime/asr/__init__.py", "runtime/pipelines/__init__.py",
                    "schema/profile.schema.json", "tools/run.py"):
            self.assertTrue((skill / rel).is_file(), rel)
        from runtime.profile import check_profile

        self.assertEqual(check_profile(json.loads((skill / "profile.json").read_text(encoding="utf-8"))), [])
        head = (skill / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
        self.assertRegex(head, r"(?m)^name: монтаж-урок$")
        self.assertEqual(list((skill).rglob("__pycache__")), [])

    def test_only_chosen_steps_and_tools(self):
        self.build(profile_for("урок", LESSON_STEPS))
        skill = self.tmp / "out" / "монтаж-урок"
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("вырезает паузы", text)
        for absent in ("выгружает версии под Reels", "раскладку кадра", "«за головой»", "HyperFrames"):
            self.assertNotIn(absent, text)
        pins = json.loads((skill / "pins.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(pins["tools"]), ["ffmpeg"])
        self.assertEqual(pins["steps"], LESSON_STEPS)
        self.assertFalse((skill / "runtime" / "look").exists())

    def test_layout_step_brings_its_runtime_and_tools(self):
        self.build(profile_for("вертикаль", ["detect_layout", "vertical"], provider="whispercpp"))
        skill = self.tmp / "out" / "монтаж-вертикаль"
        pins = json.loads((skill / "pins.json").read_text(encoding="utf-8"))
        self.assertTrue({"opencv-python", "numpy", "whisper-cpp", "ffmpeg"} <= set(pins["tools"]))
        self.assertTrue((skill / "runtime" / "look" / "__init__.py").is_file())

    def test_invalid_profile_builds_nothing(self):
        bad = profile_for("урок", LESSON_STEPS)
        del bad["steps"]
        proc = self.build(bad)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("steps", proc.stdout + proc.stderr)
        self.assertFalse((self.tmp / "out" / "монтаж-урок").exists())

    def test_unknown_step_is_refused(self):
        proc = self.build(profile_for("урок", ["cut_spans", "teleport"]))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("teleport", proc.stdout + proc.stderr)

    def test_the_sound_method_names_the_formats_own_loudness(self):
        prof = profile_for("подкаст", LESSON_STEPS + ["music"])
        prof["params"].update(lufs=-18, music={"dir": "музыка"})
        self.build(prof)
        text = (self.tmp / "out" / "монтаж-подкаст" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("params.lufs", text)
        self.assertNotIn("−14 LUFS", text)
        self.assertNotIn("-14 LUFS", text)

    def test_music_with_sound_roles_and_no_graphics_brings_the_kits_sounds(self):
        prof = profile_for("подкаст", LESSON_STEPS + ["music"])
        prof["params"]["sfx"] = {"roles": True}
        proc = self.build(prof)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        skill = self.tmp / "out" / "монтаж-подкаст"
        probe = ("import json, sys\nfrom pathlib import Path\nsys.path.insert(0, sys.argv[1])\n"
                 "from runtime.pipelines import music\n"
                 "class Ctx:\n"
                 "    music, chapters, keep, notes, outdir = {}, [{'start': 2.0, 'title': 'Глава'}], [(0.0, 10.0)], [], '.'\n"
                 "    def p(self, name, default=None):\n"
                 "        return {'sfx': {'roles': True}}.get(name, default)\n"
                 "    def note(self, text):\n"
                 "        self.notes.append(text)\n"
                 "ctx = Ctx()\nmusic.plan_music(ctx)\n"
                 "roles = ctx.music.get('accent_roles') or {}\n"
                 "print(json.dumps({k: [str(v['file']), v['peak_ms']] for k, v in roles.items()}))\n")
        done = subprocess.run([sys.executable, "-I", "-c", probe, str(skill)], capture_output=True, text=True,
                              encoding="utf-8", cwd=str(self.tmp))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        roles = json.loads(done.stdout)
        self.assertEqual(sorted(roles), ["card", "chapter"])
        for file, peak in roles.values():
            self.assertTrue(file.startswith(str(skill.resolve())), file)
            self.assertTrue(Path(file).is_file(), file)
            self.assertGreaterEqual(peak, 0)
        self.assertFalse((skill / "design" / "overlay-kit" / "tools").exists(), "the sounds only, not the whole kit")

    def test_built_skill_works_from_its_own_copy(self):
        self.build(profile_for("подкаст", LESSON_STEPS))
        run = self.tmp / "out" / "монтаж-подкаст" / "tools" / "run.py"
        proc = subprocess.run([sys.executable, "-I", str(run), "check"], capture_output=True, text=True,
                              encoding="utf-8", cwd=str(self.tmp))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("монтаж-подкаст", proc.stdout)


if __name__ == "__main__":
    unittest.main()
