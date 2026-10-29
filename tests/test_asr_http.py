"""Scribe and OpenAI-compatible providers against a local fake API; the key comes from the environment."""
import os
import unittest
from unittest import mock

from _fake_http import FakeApi, form_field
from _support import TempDirCase, make_tone, needs_ffmpeg

KEY_NAME = "AIEDITING_TEST_ASR_KEY"
KEY = "sk-test-ae-7f3c9d1b"  # a made-up value that must never show up in errors

OPENAI_REPLY = {"language": "russian", "text": "Привет мир", "words": [
    {"word": "Привет", "start": 0.1, "end": 0.42}, {"word": "мир", "start": 0.5, "end": 0.8}]}
SCRIBE_REPLY = {"language_code": "rus", "text": "Привет э-э мир", "words": [
    {"text": "Привет", "start": 0.1, "end": 0.42, "type": "word"},
    {"text": " ", "start": 0.42, "end": 0.5, "type": "spacing"},
    {"text": "(смех)", "start": 0.5, "end": 0.6, "type": "audio_event"},
    {"text": "э-э", "start": 0.6, "end": 0.9, "type": "word"},
    {"text": "мир", "start": 1.0, "end": 1.3, "type": "word"}]}


@needs_ffmpeg
class HttpProviders(TempDirCase):
    def setUp(self):
        super().setUp()
        self.media = make_tone(self.tmp / "урок.mp4", duration=1.5)
        patcher = mock.patch.dict(os.environ, {KEY_NAME: KEY})
        patcher.start()
        self.addCleanup(patcher.stop)

    def cfg(self, provider, url, **extra):
        cfg = {"provider": provider, "language": "ru", "model": None, "base_url": url,
               "api_key_env": KEY_NAME, "command": None}
        cfg.update(extra)
        return cfg

    def test_openai_compatible_words(self):
        from runtime.asr import transcribe

        with FakeApi(payload=OPENAI_REPLY) as api:
            result = transcribe(self.media, self.cfg("openai_compat", api.url + "/v1", model="whisper-x"))
        req = api.requests[0]
        self.assertEqual(req["path"], "/v1/audio/transcriptions")
        self.assertEqual(req["headers"]["Authorization"], "Bearer " + KEY)
        self.assertEqual(form_field(req["body"], "model"), "whisper-x")
        self.assertEqual(form_field(req["body"], "response_format"), "verbose_json")
        self.assertEqual(result, {"language": "ru", "provider": "openai_compat", "words": [
            {"text": "Привет", "start": 0.1, "end": 0.42, "type": "word"},
            {"text": "мир", "start": 0.5, "end": 0.8, "type": "word"}]})

    def test_openai_compatible_without_word_times_spreads_phrase(self):
        from runtime.asr import transcribe

        reply = {"text": "раз два", "segments": [{"start": 0.0, "end": 1.0, "text": " раз два"}]}
        with FakeApi(payload=reply) as api:
            result = transcribe(self.media, self.cfg("openai_compat", api.url))
        self.assertEqual([(w["text"], w["start"], w["end"]) for w in result["words"]],
                         [("раз", 0.0, 0.5), ("два", 0.5, 1.0)])

    def test_scribe_words_spacing_and_fillers(self):
        from runtime.asr import transcribe

        with FakeApi(payload=SCRIBE_REPLY) as api:
            result = transcribe(self.media, self.cfg("scribe", api.url))
        req = api.requests[0]
        self.assertEqual(req["path"], "/v1/speech-to-text")
        self.assertEqual(req["headers"]["xi-api-key"], KEY)
        self.assertEqual(form_field(req["body"], "timestamps_granularity"), "word")
        self.assertEqual([(w["text"], w["type"]) for w in result["words"]],
                         [("Привет", "word"), (" ", "spacing"), ("э-э", "filler"), ("мир", "word")])
        self.assertEqual(result["provider"], "scribe")

    def test_rejected_key_error_never_contains_the_key(self):
        from runtime.asr import AsrError, transcribe

        with FakeApi(status=401, payload={"detail": "invalid key " + KEY}) as api:
            for provider in ("openai_compat", "scribe"):
                with self.assertRaises(AsrError) as ctx:
                    transcribe(self.media, self.cfg(provider, api.url))
                self.assertIn("401", str(ctx.exception))
                self.assertNotIn(KEY, str(ctx.exception))

    def test_missing_key_names_the_variable_only(self):
        from runtime.asr import AsrError, transcribe

        with FakeApi(payload=OPENAI_REPLY) as api:
            with self.assertRaises(AsrError) as ctx:
                transcribe(self.media, self.cfg("scribe", api.url, api_key_env="AIEDITING_NO_SUCH_KEY"))
        self.assertIn("AIEDITING_NO_SUCH_KEY", str(ctx.exception))
        self.assertEqual(api.requests, [])

    def test_key_from_dotenv_file(self):
        from runtime.asr import transcribe

        (self.tmp / ".env").write_text("# keys\nAIEDITING_DOTENV_KEY='from-file-1'\n", encoding="utf-8")
        cwd = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, cwd)
        with FakeApi(payload=SCRIBE_REPLY) as api:
            transcribe(self.media, self.cfg("scribe", api.url, api_key_env="AIEDITING_DOTENV_KEY"))
        self.assertEqual(api.requests[0]["headers"]["xi-api-key"], "from-file-1")


if __name__ == "__main__":
    unittest.main()
