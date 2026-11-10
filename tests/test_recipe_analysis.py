"""Scene and audio reports are measurements; sync never edits the media."""
import argparse
import importlib.util
import json
import subprocess
import sys
import unittest

from _support import SKILL, TempDirCase, ffmpeg, needs_ffmpeg

sys.path.insert(0, str(SKILL / "tools"))
HAVE_AUDIO = all(importlib.util.find_spec(name) for name in ("numpy", "soundfile", "scipy", "librosa"))
HAVE_SCENES = importlib.util.find_spec("scenedetect") is not None


def invoke(*args):
    from recipe_lib.analysis import register

    parser = argparse.ArgumentParser()
    register(parser.add_subparsers(dest="command", required=True))
    options = parser.parse_args(args)
    return options.handler(options)


@needs_ffmpeg
@unittest.skipUnless(HAVE_SCENES, "PySceneDetect unavailable")
class SceneRecipes(TempDirCase):
    def test_two_synthetic_shots_have_source_time_boundary(self):
        video = self.tmp / "two-shots.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=red:s=128x128:r=10:d=1",
               "-f", "lavfi", "-i", "color=blue:s=128x128:r=10:d=1",
               "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", video)
        result = invoke("scenes", str(video), "--detector", "content", "--threshold", "1",
                        "--min-scene", "0.1")
        self.assertEqual(result["kind"], "scenes")
        self.assertEqual(len(result["scenes"]), 2)
        self.assertAlmostEqual(result["scenes"][0]["end_seconds"], 1.0, delta=0.11)
        self.assertAlmostEqual(result["scenes"][1]["start_seconds"], 1.0, delta=0.11)
        self.assertEqual(result["cuts_seconds"], [1.0])
        saved = invoke("scenes", str(video), "--threshold", "1", "--min-scene", "0.1",
                       "--output", str(self.tmp / "scenes.json"))
        self.assertEqual(json.loads((self.tmp / "scenes.json").read_text())["cuts_seconds"], [1.0])
        self.assertTrue(saved["report_file"].endswith("scenes.json"))


@needs_ffmpeg
@unittest.skipUnless(HAVE_AUDIO, "audio analysis packages unavailable")
class AudioRecipes(TempDirCase):
    def wav(self, name, samples, rate=8000):
        import soundfile as sf

        path = self.tmp / name
        sf.write(path, samples, rate)
        return path

    def pair(self, delay=0.4, late_extra_delay=0.0):
        import numpy as np

        rate = 8000
        rng = np.random.default_rng(612)
        base = rng.normal(0, 0.15, 12 * rate).astype(np.float32)
        # A broadband clap/chirp-like track is uniquely matchable; a steady tone is not.
        base *= np.sin(np.linspace(0, 80 * np.pi, len(base))).astype(np.float32)
        reference = self.wav("reference.wav", base)
        timeline = np.arange(len(base), dtype=np.float64)
        positions = timeline - delay * rate - late_extra_delay * rate * (timeline >= 6 * rate)
        target = np.interp(positions, np.arange(len(base)), base, left=0, right=0).astype(np.float32)
        other = self.wav("target.wav", target)
        return reference, other

    def test_report_has_bounded_audio_measurements(self):
        import numpy as np
        from recipe_lib.common import RecipeError

        rate = 8000
        sound = np.concatenate((np.zeros(rate), 0.3 * np.sin(2 * np.pi * 440 * np.arange(rate) / rate)))
        src = self.wav("sound.wav", sound)
        result = invoke("audio-report", str(src), "--at", "0", "--window", "2")
        self.assertEqual(result["kind"], "audio-report")
        self.assertGreater(result["peak_dbfs"], -12)
        self.assertLess(result["peak_dbfs"], -9)
        self.assertGreater(result["quiet_fraction"], 0.35)
        self.assertLessEqual(result["analyzed_seconds"], 2)
        before = src.read_bytes()
        with self.assertRaisesRegex(RecipeError, ".json"):
            invoke("audio-report", str(src), "--at", "0", "--window", "2",
                   "--output", str(src), "--replace")
        self.assertEqual(src.read_bytes(), before)

    def test_positive_lag_means_target_event_is_later(self):
        reference, target = self.pair(delay=0.4)
        result = invoke("audio-sync", str(reference), str(target), "--at", "2",
                        "--window", "2", "--max-lag", "1")
        self.assertEqual(result["kind"], "audio-sync")
        self.assertAlmostEqual(result["lag_seconds"], 0.4, delta=0.01)
        self.assertAlmostEqual(result["target_shift_seconds"], -0.4, delta=0.01)
        self.assertEqual(result["status"], "confident")

    def test_rejects_silence_and_clock_drift(self):
        import numpy as np
        from recipe_lib.common import RecipeError

        silent = self.wav("silent.wav", np.zeros(12 * 8000, dtype=np.float32))
        other_silent = self.wav("other-silent.wav", np.zeros(12 * 8000, dtype=np.float32))
        with self.assertRaisesRegex(RecipeError, "silence|quiet|тишин"):
            invoke("audio-sync", str(silent), str(other_silent), "--at", "2", "--window", "2")
        reference, target = self.pair(delay=0.2, late_extra_delay=0.2)
        with self.assertRaisesRegex(RecipeError, "drift|расхожд|clock"):
            invoke("audio-sync", str(reference), str(target), "--at", "2", "--window", "2", "--max-lag", "1")

    def test_repeated_tone_is_ambiguous(self):
        import numpy as np
        from recipe_lib.common import RecipeError

        rate = 8000
        tone = 0.3 * np.sin(2 * np.pi * 440 * np.arange(rate * 12) / rate)
        reference = self.wav("tone-reference.wav", tone)
        target = self.wav("tone-target.wav", np.concatenate((np.zeros(rate // 2), tone[:-rate // 2])))
        with self.assertRaisesRegex(RecipeError, "Неоднознач|совпаден"):
            invoke("audio-sync", str(reference), str(target), "--at", "2", "--window", "2", "--max-lag", "1")


if __name__ == "__main__":
    unittest.main()
