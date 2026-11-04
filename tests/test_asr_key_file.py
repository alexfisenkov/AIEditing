"""`asr.key_file`: the key is read from a .env the person already has, at run time, and never copied."""
import copy
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

from _fake_http import FakeApi
from _support import SKILL, TempDirCase, make_tone, needs_ffmpeg
from test_asr_http import SCRIBE_REPLY
from test_profile_schema import VALID

KEY_NAME = "AIEDITING_F3_TEST_KEY"
KEY = "test-key-123"  # made up; must reach the provider and nothing else


class KeyFileInSchema(unittest.TestCase):
    def check(self, asr_update):
        from runtime.profile import check_profile

        profile = copy.deepcopy(VALID)
        profile["asr"].update(asr_update)
        return check_profile(profile)

    def test_key_file_is_a_path_string(self):
        self.assertEqual(self.check({"key_file": "~/монтаж-студия/инструменты/video-use/.env"}), [])
        self.assertEqual(self.check({"key_file": None}), [])
        errors = self.check({"key_file": 42})
        self.assertTrue(any("asr.key_file" in e for e in errors), errors)
        errors = self.check({"key_file": ""})
        self.assertTrue(any("asr.key_file" in e for e in errors), errors)

    def test_a_key_pasted_as_key_file_is_refused_without_showing_it(self):
        for value in ("sk_fakeprobe0000", "test-key-123"):
            errors = self.check({"key_file": value})
            self.assertTrue(any("asr.key_file" in e for e in errors), (value, errors))
            self.assertFalse(any(value in e for e in errors), errors)
        for path in ("~/x/.env", "/x/.env", "./.env", "../keys/.env", "keys/.env", "C:\\keys\\.env", ".env"):
            self.assertEqual(self.check({"key_file": path}), [], path)

    def test_still_no_field_for_the_key_itself(self):
        errors = self.check({"key_file": "/x/.env", "api_key": "whatever"})
        self.assertTrue(any("asr.api_key" in e for e in errors), errors)


@needs_ffmpeg
class KeyFileLookup(TempDirCase):
    def setUp(self):
        super().setUp()
        self.media = make_tone(self.tmp / "урок.mp4", duration=1.5)
        self.home = self.tmp / "дом"
        self.home.mkdir()
        self.work = self.tmp / "работа"
        self.work.mkdir()
        env = mock.patch.dict(os.environ, {"HOME": str(self.home), "USERPROFILE": str(self.home),
                                           "LOCALAPPDATA": str(self.home)})
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop(KEY_NAME, None)
        cwd = os.getcwd()
        os.chdir(self.work)
        self.addCleanup(os.chdir, cwd)

    def key_file(self, text, where=None):
        path = where or self.home / "монтаж-студия" / "инструменты" / "video-use" / ".env"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def sent_key(self, key_file):
        from runtime.asr import transcribe

        with FakeApi(payload=SCRIBE_REPLY) as api:
            transcribe(self.media, {"provider": "scribe", "language": "ru", "base_url": api.url,
                                    "api_key_env": KEY_NAME, "key_file": key_file})
        return api.requests[0]["headers"]["xi-api-key"]

    def test_key_comes_from_the_named_file_with_tilde(self):
        self.key_file("OTHER=1\nexport {}=\"{}\"\n".format(KEY_NAME, KEY))
        self.assertEqual(self.sent_key("~/монтаж-студия/инструменты/video-use/.env"), KEY)

    def test_process_environment_beats_the_file(self):
        path = self.key_file("{}=test-key-file\n".format(KEY_NAME))
        with mock.patch.dict(os.environ, {KEY_NAME: "test-key-env"}):
            self.assertEqual(self.sent_key(str(path)), "test-key-env")

    def test_file_beats_dotenv_of_the_current_folder(self):
        path = self.key_file("{}=test-key-file\n".format(KEY_NAME))
        (self.work / ".env").write_text("{}=test-key-cwd\n".format(KEY_NAME), encoding="utf-8")
        self.assertEqual(self.sent_key(str(path)), "test-key-file")

    def assert_refused(self, key_file, shown_path):
        from runtime.asr import AsrError, transcribe

        with FakeApi(payload=SCRIBE_REPLY) as api:
            with self.assertRaises(AsrError) as ctx:
                transcribe(self.media, {"provider": "scribe", "language": "ru", "base_url": api.url,
                                        "api_key_env": KEY_NAME, "key_file": key_file})
        message = str(ctx.exception)
        self.assertIn(KEY_NAME, message)
        self.assertIn(str(shown_path), message)
        self.assertEqual(api.requests, [])
        return message

    def test_missing_file_names_the_path_and_the_variable(self):
        missing = self.home / "нет такой папки" / ".env"
        self.assert_refused("~/нет такой папки/.env", missing)

    def test_a_key_pasted_as_key_file_is_refused_without_showing_it(self):
        from runtime.asr import AsrError, transcribe

        with FakeApi(payload=SCRIBE_REPLY) as api:
            with self.assertRaises(AsrError) as ctx:
                transcribe(self.media, {"provider": "scribe", "language": "ru", "base_url": api.url,
                                        "api_key_env": KEY_NAME, "key_file": "sk_fakeprobe0000"})
        self.assertNotIn("sk_fakeprobe0000", str(ctx.exception))
        self.assertIn("asr.key_file", str(ctx.exception))
        self.assertEqual(api.requests, [])

    def test_missing_file_does_not_fall_back_to_the_folder_dotenv(self):
        (self.work / ".env").write_text("{}=test-key-cwd\n".format(KEY_NAME), encoding="utf-8")
        missing = self.home / "нет такой папки" / ".env"
        message = self.assert_refused(str(missing), missing)
        self.assertNotIn("test-key-cwd", message)

    def test_file_without_the_variable_does_not_fall_back_either(self):
        (self.work / ".env").write_text("{}=test-key-cwd\n".format(KEY_NAME), encoding="utf-8")
        path = self.key_file("OTHER=test-key-other\n")
        self.assert_refused(str(path), path)

    def test_file_without_the_variable_names_both_and_shows_no_value(self):
        path = self.key_file("ELEVENLABS_API_KEY=test-key-other\n")
        message = self.assert_refused(str(path), path)
        self.assertNotIn("test-key-other", message)


class KeyFileInTexts(unittest.TestCase):
    def test_interview_and_readmes_offer_the_key_file(self):
        from _support import ROOT

        rows = (SKILL / "phases" / "interview.md").read_text(encoding="utf-8").splitlines()
        row = next(r for r in rows if r.startswith("| Speech recognition"))
        self.assertIn("`asr.key_file`", row)
        for name in ("README.md", "README.ru.md"):
            self.assertIn("key_file", (ROOT / name).read_text(encoding="utf-8"), name)

    def test_vertical_offer_limits_only_clips_cut_from_long_recordings(self):
        lines = (SKILL / "phases" / "formats.md").read_text(encoding="utf-8").splitlines()
        line = next(l for l in lines if l.startswith("4. Вертикаль"))
        self.assertNotIn("9:16 до 60 с", line)
        self.assertIn("60 с", line)
        self.assertIn("нарезк", line)


ANSWERS = {"srt": True, "layout": True, "secrets": True, "retakes": True}


@needs_ffmpeg
class KeyFileThroughBuiltSkill(TempDirCase):
    """Built skill → «edit» with Scribe on a fake API: the key travels only in the request header."""

    def test_key_reaches_the_provider_and_nowhere_else(self):
        key_file = self.tmp / "инструменты" / "video-use" / ".env"
        key_file.parent.mkdir(parents=True)
        key_file.write_text("{}={}\n".format(KEY_NAME, KEY), encoding="utf-8")
        video = make_tone(self.tmp / "запись.mp4", duration=1.5)
        answers = self.tmp / "ответы-заранее.json"
        answers.write_text(json.dumps(ANSWERS), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != KEY_NAME}
        with FakeApi(payload=SCRIBE_REPLY) as api:
            folder = self.tmp / "work" / "монтаж-урок"
            folder.mkdir(parents=True)
            profile = {"format": "урок", "skill_name": "монтаж-урок", "language": "ru",
                       "asr": {"provider": "scribe", "language": "ru", "model": None, "base_url": api.url,
                               "api_key_env": KEY_NAME, "key_file": str(key_file), "command": None},
                       "steps": ["write_srt"], "params": {}, "approval": "plan", "design": "design/",
                       "taste": [], "output_dir": str(self.tmp / "выпуски")}
            (folder / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
            built = subprocess.run([sys.executable, str(SKILL / "tools" / "ae.py"), "build-skill",
                                    str(folder / "profile.json"), str(self.tmp / "out")],
                                   capture_output=True, text=True, encoding="utf-8", env=env)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            skill = self.tmp / "out" / "монтаж-урок"
            issue = self.tmp / "выпуски" / "выпуск"
            run = subprocess.run([sys.executable, "-I", str(skill / "tools" / "run.py"), "edit", str(video),
                                  "--out", str(issue), "--answers", str(answers)],
                                 capture_output=True, text=True, encoding="utf-8", cwd=str(self.tmp), env=env)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(api.requests[0]["headers"]["xi-api-key"], KEY)
        self.assertNotIn(KEY, built.stdout + built.stderr + run.stdout + run.stderr)
        built_profile = json.loads((skill / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(built_profile["asr"]["key_file"], str(key_file))
        self.assertTrue((issue / "отчёт.md").is_file())
        for root in (skill, issue, folder):
            for path in root.rglob("*"):
                if path.is_file():
                    self.assertNotIn(KEY.encode(), path.read_bytes(), str(path))


if __name__ == "__main__":
    unittest.main()
