"""Step voice_clean: the cleaned voice replaces the sound before any cut, the original stays in `.звук/исходный.wav`,
and the paid service is called only when the profile names the step — once per source and preset."""
import re
import subprocess
from pathlib import Path
from unittest import mock

from _support import TempDirCase, ffmpeg, make_av, needs_ffmpeg
from test_pipelines_helpers import Approver, asr_config, profile
from runtime import pipelines
from runtime.pipelines import voice
from runtime.services import auphonic


def band(path, freq):
    done = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path), "-af",
                           "bandpass=f={}:width_type=h:w=60,volumedetect".format(freq), "-f", "null", "-"],
                          capture_output=True, text=True)
    return float(re.search(r"mean_volume: (-?[\d.]+) dB", done.stderr).group(1))


class FakeAuphonic:
    """Stands for the service: «cleans» any audio into a 1000 Hz tone of the same length."""

    def __init__(self):
        self.calls = []

    def __call__(self, audio, preset, out, key_env=auphonic.KEY_ENV):
        self.calls.append({"audio": audio.name, "preset": preset, "key_env": key_env})
        ffmpeg("-i", str(audio), "-f", "lavfi", "-i", "sine=f=1000:sample_rate=48000", "-filter_complex",
               "[1:a][0:a]amix=inputs=2:duration=shortest:weights=1 0[a]", "-map", "[a]", "-c:a", "pcm_s16le", str(out))
        return out


@needs_ffmpeg
class VoiceClean(TempDirCase):
    def setUp(self):
        super().setUp()
        self.src = make_av(self.tmp / "запись.mp4", [(0.0, 4.0)], 4.0)  # a 440 Hz voice
        self.asr = asr_config(self.tmp, {})
        self.fake = FakeAuphonic()
        patch = mock.patch.object(auphonic, "process", self.fake)
        patch.start()
        self.addCleanup(patch.stop)

    def run_edit(self, steps, **params):
        return pipelines.run(self.src, profile(steps, self.asr, **params), self.tmp / "выпуск", Approver())

    def test_the_clean_voice_replaces_the_sound_and_the_original_stays_beside(self):
        report = self.run_edit(["voice_clean"], voice={"service": "auphonic", "preset": "средне"})
        final = self.tmp / "выпуск" / "запись.mp4"
        self.assertEqual(Path(report["output"]).resolve(), final.resolve())
        self.assertGreater(band(final, 1000), band(final, 440) + 10)
        original = self.tmp / "выпуск" / ".звук" / "исходный.wav"
        self.assertGreater(band(original, 440), band(original, 1000) + 10)
        self.assertEqual(len(self.fake.calls), 1)
        self.assertEqual(self.fake.calls[0]["preset"], voice.PRESETS["средне"])

    def test_a_second_run_pays_nothing_again(self):
        params = {"voice": {"service": "auphonic", "preset": "мягко"}}
        self.run_edit(["voice_clean"], **params)
        self.run_edit(["voice_clean"], **params)
        self.assertEqual(len(self.fake.calls), 1)
        self.run_edit(["voice_clean"], voice={"service": "auphonic", "preset": "сильно"})
        self.assertEqual(len(self.fake.calls), 2)  # another preset is another result

    def test_no_step_no_request_and_a_step_without_params_only_says_so(self):
        self.run_edit(["loudnorm"], voice={"service": "auphonic", "preset": "мягко"})
        self.assertEqual(self.fake.calls, [])
        report = self.run_edit(["voice_clean"])
        self.assertEqual(self.fake.calls, [])
        self.assertFalse((self.tmp / "выпуск" / ".звук").exists())
        self.assertTrue(any("params.voice" in n for n in report.get("notes", [])), report.get("notes"))

    def test_an_own_auphonic_preset_and_the_key_variable_go_through(self):
        self.run_edit(["voice_clean"], voice={"service": "auphonic", "preset": "uuid-of-my-preset", "key_env": "MY_AUPHONIC"})
        self.assertEqual(self.fake.calls[0]["preset"], "uuid-of-my-preset")
        self.assertEqual(self.fake.calls[0]["key_env"], "MY_AUPHONIC")
