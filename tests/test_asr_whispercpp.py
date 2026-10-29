"""Local whisper.cpp provider driven through a fake whisper-cli; the real one is not needed."""
import sys
import unittest

from _support import FIXTURES, TempDirCase, make_tone, needs_ffmpeg


@needs_ffmpeg
class WhisperCpp(TempDirCase):
    def setUp(self):
        super().setUp()
        self.media = make_tone(self.tmp / "эфир 04.09.mp4", duration=1.5)
        self.model = self.tmp / "ggml-test.bin"
        self.model.write_bytes(b"\0")

    def cfg(self, model):
        return {"provider": "whispercpp", "language": "ru", "model": str(model), "base_url": None,
                "api_key_env": None, "command": [sys.executable, str(FIXTURES / "fake_whisper_cli.py")]}

    def test_word_segments_become_transcript(self):
        from runtime.asr import transcribe

        result = transcribe(self.media, self.cfg(self.model))
        self.assertEqual(result, {"language": "ru", "provider": "whispercpp", "words": [
            {"text": "Привет", "start": 0.12, "end": 0.48, "type": "word"},
            {"text": "э-э", "start": 0.5, "end": 0.9, "type": "filler"},
            {"text": "мир.", "start": 1.0, "end": 1.3, "type": "word"}]})

    def test_missing_model_is_explained(self):
        from runtime.asr import AsrError, transcribe

        with self.assertRaises(AsrError) as ctx:
            transcribe(self.media, self.cfg(self.tmp / "нет модели.bin"))
        self.assertIn("нет модели.bin", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
