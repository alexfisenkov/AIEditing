"""The 'what is better where' table shown when a person picks a recogniser."""
import re
import unittest


class ProvidersHelp(unittest.TestCase):
    def test_every_provider_is_explained_in_russian(self):
        from runtime.asr import PROVIDERS, providers_help

        rows = providers_help()
        self.assertEqual([r["provider"] for r in rows], list(PROVIDERS))
        for row in rows:
            for field in ("cost", "privacy", "word_timing", "needs", "best_for"):
                self.assertRegex(row[field], r"[а-яё]", (row["provider"], field))

    def test_cost_and_privacy_tell_local_from_cloud(self):
        from runtime.asr import providers_help

        rows = {r["provider"]: r for r in providers_help()}
        self.assertIn("бесплатно", rows["whispercpp"]["cost"])
        self.assertIn("не покидает", rows["whispercpp"]["privacy"])
        self.assertIn("платно", rows["scribe"]["cost"])
        self.assertIn("облако", rows["scribe"]["privacy"])
        self.assertIn("OpenRouter", rows["openai_compat"]["title"])

    def test_keys_are_named_never_requested_in_chat(self):
        from runtime.asr import providers_help

        for row in providers_help():
            text = " ".join(row.values())
            self.assertNotRegex(text, r"(?i)пришлите ключ|вставьте ключ в чат")
            for name in re.findall(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b", text):
                self.assertTrue(name.endswith("_API_KEY"), name)


if __name__ == "__main__":
    unittest.main()
