"""install-skill / list-skills / backup-skill / restore-skill — only ever inside a temporary HOME."""
import json
import os
import subprocess
import sys
import unittest

from _support import SKILL, TempDirCase

AE = SKILL / "tools" / "ae.py"
STEPS = ["speech_spans", "cut_spans", "loudnorm", "write_srt"]


class InstallSkill(TempDirCase):
    def setUp(self):
        super().setUp()
        self.home = self.tmp / "дом"
        self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home), AIEDITING_NO_SERVE="1",
                        AIEDITING_WORK=str(self.tmp / "work"))

    def ae(self, *args, ok=True):
        proc = subprocess.run([sys.executable, str(AE), *map(str, args)], capture_output=True, text=True,
                              encoding="utf-8", env=self.env, cwd=str(self.tmp))
        if ok:
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc

    def built(self, note):
        folder = self.tmp / "src" / "монтаж-урок"
        folder.mkdir(parents=True, exist_ok=True)
        profile = {"format": "урок", "skill_name": "монтаж-урок", "language": "ru",
                   "asr": {"provider": "scribe", "language": "ru", "model": None, "base_url": None,
                           "api_key_env": "ELEVENLABS_API_KEY", "command": None},
                   "steps": STEPS, "params": {}, "approval": "plan", "design": "design/",
                   "taste": [{"date": "2026-10-29", "video": "", "note": note}], "output_dir": "выпуски"}
        (folder / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        out = self.tmp / ("build-" + note)
        self.ae("build-skill", folder / "profile.json", out)
        return out / "монтаж-урок"

    def installed_note(self):
        profile = self.home / ".agents" / "skills" / "монтаж-урок" / "profile.json"
        return json.loads(profile.read_text(encoding="utf-8"))["taste"][0]["note"]

    def test_install_writes_agents_copy_and_claude_pointer(self):
        out = self.ae("install-skill", self.built("первая")).stdout
        copy = self.home / ".agents" / "skills" / "монтаж-урок"
        pointer = self.home / ".claude" / "skills" / "монтаж-урок"
        self.assertTrue((copy / "SKILL.md").is_file())
        self.assertTrue((pointer / "SKILL.md").is_file())
        if os.name != "nt":
            self.assertTrue(pointer.is_symlink())
        self.assertIn("первая установка", out)

    def test_reinstall_keeps_previous_and_restore_brings_it_back(self):
        self.ae("install-skill", self.built("первая"))
        self.ae("install-skill", self.built("вторая"))
        self.assertEqual(self.installed_note(), "вторая")
        backups = self.home / ".agents" / "skills" / ".aiediting-backups"
        self.assertEqual(len([p for p in backups.iterdir() if p.name.startswith("монтаж-урок-")]), 1)
        self.ae("restore-skill", "монтаж-урок")
        self.assertEqual(self.installed_note(), "первая")
        self.assertTrue((self.home / ".claude" / "skills" / "монтаж-урок" / "SKILL.md").is_file())
        kept = list(backups.iterdir())  # the replaced «вторая» is kept in the reserve
        self.assertEqual(len(kept), 1)
        note = json.loads((kept[0] / "profile.json").read_text(encoding="utf-8"))["taste"][0]["note"]
        self.assertEqual(note, "вторая")

    def test_list_skills_finds_format_skills_only(self):
        (self.home / ".agents" / "skills" / "чужой").mkdir(parents=True)
        self.ae("install-skill", self.built("первая"))
        rows = json.loads(self.ae("list-skills", "--json").stdout)
        self.assertEqual([r["name"] for r in rows], ["монтаж-урок"])
        self.assertEqual(rows[0]["format"], "урок")
        self.assertEqual(rows[0]["steps"], STEPS)

    def test_foreign_folder_in_claude_skills_is_not_touched(self):
        foreign = self.home / ".claude" / "skills" / "монтаж-урок"
        foreign.mkdir(parents=True)
        (foreign / "мой.txt").write_text("моё", encoding="utf-8")
        proc = self.ae("install-skill", self.built("первая"), ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue((foreign / "мой.txt").is_file())
        self.assertFalse((self.home / ".agents" / "skills" / "монтаж-урок").exists())

    def test_backup_skill_copies_and_restore_without_backups_refuses(self):
        self.assertNotEqual(self.ae("restore-skill", "монтаж-урок", ok=False).returncode, 0)
        self.ae("install-skill", self.built("первая"))
        self.ae("backup-skill", "монтаж-урок")
        self.assertIn("монтаж-урок-", self.ae("restore-skill", "монтаж-урок", "--list").stdout)
        self.assertEqual(self.installed_note(), "первая")


if __name__ == "__main__":
    unittest.main()
