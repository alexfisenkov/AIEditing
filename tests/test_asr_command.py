"""Speech recognition through the user's own command: no network, a fake recogniser script."""
import sys
import unittest

from _support import FIXTURES, TempDirCase

EXPECTED = [
    {"text": "Привет", "start": 0.10, "end": 0.42, "type": "word"},
    {"text": " ", "start": 0.42, "end": 0.50, "type": "spacing"},
    {"text": "э-э", "start": 0.50, "end": 0.90, "type": "filler"},
    {"text": "мир", "start": 1.00, "end": 1.30, "type": "word"},
]


class CommandProvider(TempDirCase):
    def setUp(self):
        super().setUp()
        self.media = self.tmp / "запись урока.mp4"
        self.media.write_bytes(b"not really a video")

    def cfg(self, *extra):
        cmd = [sys.executable, str(FIXTURES / "fake_asr.py"), "{input}", "{language}", *extra]
        return {"provider": "command", "language": "ru", "model": None,
                "base_url": None, "api_key_env": None, "command": cmd}

    def test_stdout_json_becomes_transcript(self):
        from runtime.asr import transcribe

        result = transcribe(self.media, self.cfg())
        self.assertEqual(result, {"words": EXPECTED, "language": "ru", "provider": "command"})

    def test_output_file_placeholder(self):
        from runtime.asr import transcribe

        result = transcribe(self.media, self.cfg("{output}"))
        self.assertEqual(result["words"], EXPECTED)

    def test_failing_command_is_an_asr_error(self):
        from runtime.asr import AsrError, transcribe

        cfg = self.cfg()
        cfg["command"][2] = str(self.tmp / "нет файла.mp4")
        with self.assertRaises(AsrError):
            transcribe(self.media, cfg)

    def test_unknown_provider_lists_known_ones(self):
        from runtime.asr import AsrError, transcribe

        with self.assertRaises(AsrError) as ctx:
            transcribe(self.media, {"provider": "magic", "language": "ru"})
        for name in ("whispercpp", "scribe", "openai_compat", "command"):
            self.assertIn(name, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
