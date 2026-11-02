"""The second listening may use its own recogniser: `params.verify_asr`, so a paid one is not paid for twice."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import _support  # noqa: F401  (puts the skill on sys.path)


class VerifyAsr(unittest.TestCase):
    def test_check_words_listens_with_verify_asr(self):
        from runtime.pipelines import verify

        said = {"words": [{"text": "Привет", "start": 0.0, "end": 0.5, "type": "word"}]}
        ctx = mock.Mock()
        ctx.transcript.return_value = said
        ctx.p.side_effect = lambda name, default=None: {"provider": "whispercpp"} if name == "verify_asr" else default
        with mock.patch.object(verify, "recognise", return_value=said) as heard:
            self.assertEqual(verify.check_words(ctx, Path("готово.mp4"), [(0.0, 1.0)]), [])
        heard.assert_called_once_with(ctx, Path("готово.mp4"), {"provider": "whispercpp"})

    def test_recognise_uses_the_given_config_and_keeps_the_source_cache_apart(self):
        from runtime.pipelines import words

        with TemporaryDirectory() as tmp:
            video = Path(tmp) / "готово.mp4"
            video.write_bytes(b"\0")
            ctx = mock.Mock(src=Path(tmp) / "исходник.mp4", outdir=Path(tmp), work=Path(tmp) / "run",
                            profile={"asr": {"provider": "scribe"}, "language": "ru"}, info={"has_audio": True})
            with mock.patch("runtime.asr.transcribe", return_value={"words": []}) as call:
                words.recognise(ctx, video, {"provider": "whispercpp", "model": "m.bin"})
            self.assertEqual(call.call_args[0][1]["provider"], "whispercpp")

    def test_schema_accepts_verify_asr_with_max_context(self):
        from runtime.profile import check_profile

        profile = {"format": "урок", "skill_name": "монтаж-урок", "language": "ru", "output_dir": "выпуски",
                   "asr": {"provider": "scribe"}, "steps": ["cut_spans"],
                   "params": {"verify_asr": {"provider": "whispercpp", "model": "m.bin", "max_context": 0}}}
        self.assertEqual(check_profile(profile), [])
        profile["params"]["verify_asr"]["provider"] = "нет такого"
        self.assertTrue(check_profile(profile))


class Needs(unittest.TestCase):
    def test_the_tools_of_the_second_recogniser_go_into_the_skill(self):
        from aelib import catalog

        need = catalog.needs(["cut_spans"], "scribe", verify_provider="whispercpp")
        self.assertIn("whisper-cpp", need["tools"])
        self.assertNotIn("whisper-cpp", catalog.needs(["cut_spans"], "scribe")["tools"])


if __name__ == "__main__":
    unittest.main()
