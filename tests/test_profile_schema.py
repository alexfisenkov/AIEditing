"""Format profile schema and the dependency-free profile check."""
import copy
import json
import unittest

from _support import SKILL

VALID = {
    "format": "урок",
    "skill_name": "монтаж-урок",
    "language": "ru",
    "asr": {"provider": "openai_compat", "language": "ru", "model": "whisper-1",
            "base_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY", "command": None},
    "steps": ["speech_spans", "cut_spans", "loudnorm", "write_srt"],
    "params": {"gap": 0.5, "pad": 0.12, "lufs": -16, "glossary": {"клод код": "Claude Code"}},
    "approval": "plan",
    "design": "design/",
    "taste": [{"date": "2026-10-29", "video": "урок-14-10.mp4", "note": "паузы короче"}],
    "output_dir": "~/Видео/выпуски",
}


class ProfileSchema(unittest.TestCase):
    def check(self, profile):
        from runtime.profile import check_profile

        return check_profile(profile)

    def test_schema_file_is_json(self):
        schema = json.loads((SKILL / "schema" / "profile.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["type"], "object")

    def test_valid_profile_has_no_errors(self):
        self.assertEqual(self.check(VALID), [])

    def test_whisper_profile_with_nulls_is_valid(self):
        profile = copy.deepcopy(VALID)
        profile["asr"] = {"provider": "whispercpp", "language": "ru", "model": "~/models/ggml-large-v3.bin",
                          "base_url": None, "api_key_env": None, "command": None}
        self.assertEqual(self.check(profile), [])

    def broken(self, mutate):
        profile = copy.deepcopy(VALID)
        mutate(profile)
        return self.check(profile)

    def test_invalid_profiles_are_reported_with_paths(self):
        cases = {
            "skill_name": lambda p: p.pop("skill_name"),
            "asr.provider": lambda p: p["asr"].update(provider="magic"),
            "steps[1]": lambda p: p["steps"].__setitem__(1, 42),
            "taste[0].note": lambda p: p["taste"][0].pop("note"),
            "approval": lambda p: p.update(approval="sometimes"),
        }
        for where, mutate in cases.items():
            errors = self.broken(mutate)
            self.assertTrue(errors, where)
            self.assertTrue(any(where in e for e in errors), (where, errors))

    def test_skill_name_cannot_escape_or_hide_the_skill_folder(self):
        for name in (".", "..", ".скрытый", "../монтаж", "a/b", "a\\b"):
            errors = self.broken(lambda p: p.update(skill_name=name))
            self.assertTrue(any("skill_name" in e for e in errors), (name, errors))
        for name in ("монтаж-урок", "montage.v2", "монтаж_эфир"):
            self.assertEqual(self.broken(lambda p: p.update(skill_name=name)), [], name)

    def test_a_key_value_cannot_hide_in_the_profile(self):
        errors = self.broken(lambda p: p["asr"].update(api_key_env="sk-or-v1-abc"))
        self.assertTrue(any("asr.api_key_env" in e for e in errors), errors)
        errors = self.broken(lambda p: p["asr"].update(api_key="whatever"))
        self.assertTrue(any("asr.api_key" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
