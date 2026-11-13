"""`ae.py voice-try`: a minute of the recording through the three presets, side by side on the dashboard, and a
trial request that says whether the key works. No network: the service is played by a stand-in."""
import io
import json
import os
import sys
from contextlib import redirect_stdout
from unittest import mock

from _support import SKILL, TempDirCase, make_av, needs_ffmpeg
from test_voice_clean import FakeAuphonic

sys.path.insert(0, str(SKILL / "tools"))

from runtime.pipelines import voice  # noqa: E402
from runtime.services import auphonic  # noqa: E402


class Base(TempDirCase):
    def setUp(self):
        super().setUp()
        self.work = self.tmp / "work"
        patcher = mock.patch.dict(os.environ, {"AIEDITING_WORK": str(self.work), "AIEDITING_NO_SERVE": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.ae("init", "--title", "Проба")

    def ae(self, *args, code=0):
        from aelib.cli import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            got = main([str(a) for a in args])
        self.assertEqual(got, code, buf.getvalue())
        return buf.getvalue()


def with_steps(work, steps):
    folder = work / "монтаж-урок"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "profile.json").write_text(json.dumps({"skill_name": "монтаж-урок", "steps": steps}), encoding="utf-8")


@needs_ffmpeg
class VoiceTry(Base):
    def test_without_voice_clean_in_the_steps_nothing_is_paid(self):
        src = make_av(self.tmp / "запись.mp4", [(0.0, 9.0)], 9.0)
        fake = FakeAuphonic()
        for steps in (None, ["cut_spans"]):
            if steps is not None:
                with_steps(self.work, steps)
            with mock.patch.object(auphonic, "process", fake):
                out = self.ae("voice-try", "монтаж-урок", src, "--duration", "5", code=1)
            self.assertIn("voice_clean", out)
            self.assertEqual(fake.calls, [])

    def test_a_repeat_of_the_same_piece_takes_the_ready_files(self):
        src = make_av(self.tmp / "запись.mp4", [(0.0, 9.0)], 9.0)
        with_steps(self.work, ["cut_spans", "voice_clean"])
        fake = FakeAuphonic()
        with mock.patch.object(auphonic, "process", fake):
            self.ae("voice-try", "монтаж-урок", src, "--start", "2", "--duration", "5")
            again = self.ae("voice-try", "монтаж-урок", src, "--start", "2", "--duration", "5")
            self.assertEqual(len(fake.calls), len(voice.PRESETS))
            self.assertIn("0 мин", again)
            self.ae("voice-try", "монтаж-урок", src, "--start", "3", "--duration", "5")
        self.assertEqual(len(fake.calls), 2 * len(voice.PRESETS))  # another piece is another request

    def test_three_presets_and_the_original_stand_side_by_side(self):
        src = make_av(self.tmp / "запись.mp4", [(0.0, 9.0)], 9.0)
        with_steps(self.work, ["voice_clean"])
        fake = FakeAuphonic()
        with mock.patch.object(auphonic, "process", fake):
            text = self.ae("voice-try", "монтаж-урок", src, "--start", "2", "--duration", "5")
        self.assertEqual([c["preset"] for c in fake.calls], list(voice.PRESETS.values()))
        from state import read

        rows = [t for t in read(self.work)["trials"] if t.get("probe")]
        self.assertEqual([t["variant"] for t in rows], ["голос-как-записано"] + ["голос-" + n for n in voice.PRESETS])
        for t in rows:
            self.assertTrue((self.work / t["video"]).is_file(), t["video"])
        for name in voice.PRESETS:
            self.assertIn(name, text)
        self.assertIn("params.voice", text)
        self.assertIn("3 мин", text)


class CheckKey(Base):
    def test_the_check_only_asks_the_account(self):
        with mock.patch.object(auphonic, "check_key", return_value="Ключ Auphonic принят: аккаунт отвечает."):
            self.assertIn("принят", self.ae("voice-try", "монтаж-урок", "--check"))

    def test_a_missing_key_is_one_line_with_what_to_do(self):
        def no_key(*a, **k):
            raise auphonic.ServiceError("Нет ключа Auphonic: переменная AUPHONIC_API_KEY не задана")

        with mock.patch.object(auphonic, "check_key", no_key):
            out = self.ae("voice-try", "монтаж-урок", "--check", code=1)
        self.assertIn("AUPHONIC_API_KEY", out)

    def test_without_a_recording_it_says_what_is_missing(self):
        self.assertIn("видео", self.ae("voice-try", "монтаж-урок", code=1))
