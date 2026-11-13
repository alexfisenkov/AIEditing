"""`ae.py trial --camera F --audio F` hands the other cameras and the separate sound to `pipelines.run`, cut to the same
piece as the main camera, so the first trial of a format with `angles` lines them up as the real edit will."""
import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from _support import SKILL, TempDirCase, ffmpeg, make_av, needs_ffmpeg
from test_pipelines_helpers import asr_config

sys.path.insert(0, str(SKILL / "tools"))


def angles_profile(tmp):
    return {"format": "урок", "skill_name": "монтаж-урок", "language": "ru", "asr": asr_config(tmp, {"words": []}),
            "steps": ["speech_spans", "cut_spans", "angles"], "params": {}, "approval": "plan", "design": "design/",
            "taste": [], "output_dir": str(tmp / "выпуски")}


@needs_ffmpeg
class TrialCameras(TempDirCase):
    def setUp(self):
        super().setUp()
        self.main = make_av(self.tmp / "камера A.mp4", [(0.5, 2.5)], 4.0, size="320x180")
        self.side = make_av(self.tmp / "камера B.mp4", [(0.5, 2.5)], 4.0, size="320x180")
        self.sound = self.tmp / "рекордер.wav"  # a recorder has no picture
        ffmpeg("-i", str(make_av(self.tmp / "рекордер.mp4", [(0.5, 2.5)], 4.0)), "-vn", "-c:a", "pcm_s16le", str(self.sound))
        self.work = self.tmp / "мастерская"
        env = mock.patch.dict(os.environ, {"AIEDITING_WORK": str(self.work), "AIEDITING_NO_SERVE": "1"})
        env.start()
        self.addCleanup(env.stop)
        self.assertEqual(self.ae("init", "--title", "Проба")[0], 0)
        self.assertEqual(self.ae("formats", "урок")[0], 0)
        (self.work / "монтаж-урок" / "profile.json").write_text(
            json.dumps(angles_profile(self.tmp), ensure_ascii=False), encoding="utf-8")
        self.calls = []

    def ae(self, *args):
        from aelib.cli import main

        with redirect_stdout(io.StringIO()) as buf:
            code = main([str(a) for a in args])
        return code, buf.getvalue()

    def fake_run(self, src, profile, outdir, approve, **extra):
        self.calls.append(dict(extra, src=Path(src)))
        Path(outdir).mkdir(parents=True, exist_ok=True)
        out = Path(outdir) / "готово.mp4"
        out.write_bytes(Path(src).read_bytes())
        return {"output": str(out)}

    def test_whole_files_go_to_the_pipeline_as_they_are(self):
        with mock.patch("runtime.pipelines.run", self.fake_run):
            code, out = self.ae("trial", "монтаж-урок", self.main, "--camera", self.side, "--camera", self.sound,
                                "--audio", self.sound)
        self.assertEqual(code, 0, out)
        call = self.calls[0]
        self.assertEqual([Path(c) for c in call["cameras"]], [self.side.resolve(), self.sound.resolve()])
        self.assertEqual(Path(call["audio"]), self.sound.resolve())

    def test_a_piece_cuts_every_camera_and_the_sound_to_the_same_seconds(self):
        from runtime.media import probe

        with mock.patch("runtime.pipelines.run", self.fake_run):
            code, out = self.ae("trial", "монтаж-урок", self.main, "--camera", self.side, "--audio", self.sound,
                                "--start", "1", "--duration", "2")
        self.assertEqual(code, 0, out)
        call = self.calls[0]
        folder = self.work / "монтаж-урок" / "trials" / "01"
        for path in [call["src"]] + list(call["cameras"]) + [call["audio"]]:
            self.assertEqual(Path(path).resolve().parent, folder.resolve())
            self.assertAlmostEqual(probe(Path(path))["duration"], 2.0, delta=0.1)

    def test_a_missing_camera_is_named_and_nothing_runs(self):
        with mock.patch("runtime.pipelines.run", self.fake_run):
            code, out = self.ae("trial", "монтаж-урок", self.main, "--camera", self.tmp / "нет.mp4")
        self.assertEqual(code, 1, out)
        self.assertIn("нет.mp4", out)
        self.assertEqual(self.calls, [])
