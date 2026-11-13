"""Two cameras and a separate recorder through the whole pipeline: lined up by sound, cut by the program of angles."""
import array
import json
import subprocess
import unittest

from _support import TempDirCase, needs_ffmpeg
from test_pipelines_helpers import Approver, asr_config, profile
from test_sync import RHYTHM, bursts_file, shifted

SPEECH = [(a + k * 16.0, b + k * 16.0) for k in range(4) for a, b in RHYTHM]  # 64 s, pauses of 0.2–0.8 s
SECONDS = 64.5


def words():
    return {"words": [{"text": "слово." if i % 3 == 2 else "слово", "start": a, "end": b} for i, (a, b) in enumerate(SPEECH)]}


def colour_at(video, t):
    """Mean U of the frame at t s: about 128 for black, far above for blue."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-ss", "{:.3f}".format(t), "-i", str(video), "-frames:v", "1",
                          "-vf", "signalstats,metadata=print:key=lavfi.signalstats.UAVG", "-f", "null", "-"],
                         stderr=subprocess.PIPE, encoding="utf-8", errors="replace").stderr
    return float(err.split("UAVG=")[1].split()[0])


def pitch(video, tmp):
    """The tone of the result: zero crossings in its loud 50 ms blocks, the median."""
    raw = tmp / "звук.raw"
    subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-i", str(video), "-ac", "1", "-ar",
                    "48000", "-f", "s16le", "-c:a", "pcm_s16le", str(raw)], check=True)
    x = array.array("h")
    x.frombytes(raw.read_bytes())
    found = []
    for i in range(0, len(x) - 2400, 2400):
        block = x[i:i + 2400]
        if max(map(abs, block)) > 3000:
            found.append(sum(1 for p, q in zip(block, block[1:]) if (p < 0) != (q < 0)) / 0.1)
    return sorted(found)[len(found) // 2]


@needs_ffmpeg
class TwoCamerasAndARecorder(TempDirCase):
    def setUp(self):
        super().setUp()
        self.main = bursts_file(self.tmp / "камера A.mp4", SPEECH, SECONDS, freq=440, video="black")
        self.side = bursts_file(self.tmp / "камера B.mp4", shifted(SPEECH, 1.0), SECONDS + 1, freq=600, video="blue")
        self.sound = bursts_file(self.tmp / "рекордер.wav", shifted(SPEECH, -0.5), SECONDS + 1, freq=1000)

    def run_it(self, **extra):
        from runtime import pipelines

        prof = profile(["speech_spans", "cut_spans", "angles"], asr_config(self.tmp, words()), gap=0.5, pad=0.12)
        return pipelines.run(self.main, prof, self.tmp / "выпуск", Approver(), **extra)

    def test_the_program_is_cut_from_both_cameras_with_the_recorders_sound(self):
        from runtime.media import probe

        report = self.run_it(cameras=[self.side], audio=self.sound)
        plan, offsets = report["angles"]["plan"], report["angles"]["offsets"]
        self.assertAlmostEqual(offsets[str(self.side.resolve())], 1.0, delta=0.04)
        self.assertAlmostEqual(offsets[str(self.sound.resolve())], -0.5, delta=0.04)
        self.assertAlmostEqual(probe(report["output"])["duration"], plan[-1]["end"], delta=0.08)
        self.assertAlmostEqual(plan[-1]["end"], report["kept_seconds"], places=2)
        side = [s for s in plan if s["camera"] == 1]
        wide = [s for s in plan if s["camera"] == 0 and s["crop"] is None]
        self.assertTrue(side and wide, json.dumps(plan))
        self.assertGreater(colour_at(report["output"], (side[0]["start"] + side[0]["end"]) / 2), 160)
        self.assertLess(abs(colour_at(report["output"], (wide[0]["start"] + wide[0]["end"]) / 2) - 128), 8)
        self.assertAlmostEqual(pitch(report["output"], self.tmp), 1000, delta=60, msg="the sound is the recorder's")

    def test_one_camera_keeps_its_own_sound(self):
        report = self.run_it()
        self.assertTrue(all(s["camera"] == 0 for s in report["angles"]["plan"]))
        self.assertAlmostEqual(pitch(report["output"], self.tmp), 440, delta=40)

    def test_without_the_step_the_cameras_are_named_unused(self):
        from runtime import pipelines

        prof = profile(["speech_spans", "cut_spans"], asr_config(self.tmp, words()), gap=0.5, pad=0.12)
        report = pipelines.run(self.main, prof, self.tmp / "выпуск", Approver(), cameras=[self.side])
        self.assertTrue(any("angles" in n for n in report["notes"]))
        self.assertNotIn("angles", report)


if __name__ == "__main__":
    unittest.main()
