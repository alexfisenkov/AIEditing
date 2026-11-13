"""A service that cannot do its part stops `run.py edit` with one line and exit code 1, no Python traceback, no key."""
import json
import os
import subprocess
import sys

from _support import SKILL, TempDirCase, make_av, needs_ffmpeg

MISSING = "AIEDITING_TEST_KEY_THAT_IS_NOT_SET"


@needs_ffmpeg
class ServiceErrorOnEdit(TempDirCase):
    def test_voice_clean_without_a_key_is_one_clear_line(self):
        profile = {"format": "ютуб", "skill_name": "монтаж-ютуб", "language": "ru",
                   "asr": {"provider": "command", "language": "ru", "model": None, "base_url": None,
                           "api_key_env": None, "command": ["нет"]},
                   "steps": ["voice_clean", "speech_spans", "cut_spans"],
                   "params": {"voice": {"service": "auphonic", "preset": "средне", "key_env": MISSING}},
                   "approval": "plan", "design": "design/", "taste": [], "output_dir": "выпуски"}
        folder = self.tmp / "work" / "монтаж-ютуб"
        folder.mkdir(parents=True)
        (folder / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        built = subprocess.run([sys.executable, str(SKILL / "tools" / "ae.py"), "build-skill", str(folder / "profile.json"),
                                str(self.tmp / "out")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        video = make_av(self.tmp / "запись.mp4", [(0.0, 2.0)], 2.0)
        home = self.tmp / "дом"  # no ~/.aiediting/.env of the machine: the key is surely absent
        home.mkdir()
        env = {k: v for k, v in os.environ.items() if k not in (MISSING, "AIEDITING_LIBRARY")}
        env.update(AIEDITING_IN_VENV="1", HOME=str(home), USERPROFILE=str(home), LOCALAPPDATA=str(home))
        done = subprocess.run([sys.executable, str(self.tmp / "out" / "монтаж-ютуб" / "tools" / "run.py"), "edit", str(video),
                               "--out", str(self.tmp / "выпуск")], capture_output=True, text=True, encoding="utf-8",
                              env=env, cwd=str(home))
        said = (done.stdout + done.stderr).strip()
        self.assertEqual(done.returncode, 1, said)
        self.assertNotIn("Traceback", said)
        self.assertNotIn("ServiceError", said)
        self.assertEqual(len(said.splitlines()), 1, said)
        self.assertIn(MISSING, said)  # the variable is named so the person knows what to fill in
        self.assertIn("Auphonic", said)
