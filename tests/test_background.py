"""Human matting keeps frame order, transparency, audio and source files."""
import importlib.util
import subprocess
import unittest

from _support import TempDirCase, ffmpeg, needs_ffmpeg

HAVE_NUMPY = importlib.util.find_spec("numpy") is not None


class CenterPerson:
    """A deterministic ONNX session: the centre is the subject, the edge is background."""

    def __init__(self):
        self.frames = 0

    def run(self, names, feeds):
        import numpy as np

        self.frames += 1
        assert names == ["fgr", "pha", "r1o", "r2o", "r3o", "r4o"]
        assert feeds["src"].shape[0:2] == (1, 3)
        assert feeds["src"].dtype == np.float32
        assert feeds["downsample_ratio"].dtype == np.float32
        assert feeds["r1i"].mean() == self.frames - 1
        h, w = feeds["src"].shape[-2:]
        alpha = np.zeros((1, 1, h, w), np.float32)
        alpha[:, :, h // 4:3 * h // 4, w // 4:3 * w // 4] = 1
        states = [np.full((1, 1, 1, 1), self.frames, np.float32) for _ in range(4)]
        return [feeds["src"], alpha] + states


class BackgroundPlan(unittest.TestCase):
    def test_chromakey_needs_no_rvm_model(self):
        from runtime.pipelines.background import plan_background, settings

        class Ctx:
            steps = ["background"]
            def p(self, key):
                return {"mode": "chromakey", "key_color": "#00ff00", "similarity": 0.12, "blend": 0.08}

        self.assertEqual(settings(Ctx())["mode"], "chromakey")
        self.assertIsNone(plan_background(Ctx()))

    def test_model_location_matches_windows_catalog(self):
        from runtime.media.background import default_model_path

        self.assertEqual(str(default_model_path("nt", "C:/Users/Test/AppData/Local")).replace("\\", "/"),
                         "C:/Users/Test/AppData/Local/AIEditing/models/rvm_mobilenetv3_fp32.onnx")

    def test_invalid_choice_fails_before_render(self):
        from runtime.pipelines.background import settings
        from runtime.pipelines.errors import PipelineError

        class Ctx:
            def __init__(self, value):
                self.value = value

            def p(self, key):
                return self.value

        for value in ({"mode": "video", "value": "missing.mp4"},
                      {"mode": "solid", "value": "green"},
                      {"mode": "solid", "value": "#zzzzzz"},
                      {"mode": "chromakey", "key_color": "#zzzzzz"},
                      {"mode": "unknown"},
                      {"mode": "blur", "downsample_ratio": 0}):
            with self.subTest(value=value), self.assertRaises(PipelineError):
                settings(Ctx(value))


@needs_ffmpeg
@unittest.skipUnless(HAVE_NUMPY, "numpy not installed")
class BackgroundVideo(TempDirCase):
    def source(self):
        path = self.tmp / "source.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=red:s=64x64:r=8:d=1",
               "-f", "lavfi", "-i", "sine=f=440:d=1", "-c:v", "libx264",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", path)
        return path

    def pixel(self, path, x, y):
        data = subprocess.check_output(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
                                        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"])
        i = (y * 64 + x) * 3
        return tuple(data[i:i + 3])

    def test_replaces_background_and_keeps_audio(self):
        from runtime.media.background import edit_background
        from runtime.media.probe import probe

        src = self.source()
        source_bytes = src.read_bytes()
        session = CenterPerson()
        out = self.tmp / "green.mp4"
        self.assertEqual(edit_background(src, out, mode="solid", background="#00FF00", session=session), out.resolve())
        self.assertEqual(session.frames, 8)
        self.assertTrue(probe(out)["has_audio"])
        self.assertAlmostEqual(probe(out)["duration"], 1, delta=0.15)
        self.assertEqual(src.read_bytes(), source_bytes)
        self.assertGreater(self.pixel(out, 32, 32)[0], 170)
        self.assertGreater(self.pixel(out, 2, 2)[1], 170)

    def test_remove_outputs_alpha_and_rejects_mp4(self):
        from runtime.media.background import edit_background
        from runtime.media.ffmpeg import MediaError
        from runtime.media.probe import probe

        src = self.source()
        with self.assertRaises(MediaError):
            edit_background(src, self.tmp / "wrong.mp4", mode="remove", session=CenterPerson())
        out = self.tmp / "cutout.mov"
        edit_background(src, out, mode="remove", session=CenterPerson())
        self.assertTrue(probe(out)["has_audio"])
        alpha = subprocess.check_output(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(out),
                                         "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgba", "pipe:1"])
        self.assertLess(alpha[(2 * 64 + 2) * 4 + 3], 25)
        self.assertGreater(alpha[(32 * 64 + 32) * 4 + 3], 230)

    def test_foreground_places_subject_over_existing_video(self):
        from runtime.media.background import edit_background
        from runtime.media.probe import probe

        src = self.source()
        graphics = self.tmp / "graphics.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=64x64:r=8:d=1",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", graphics)
        out = self.tmp / "behind-head.mp4"
        edit_background(src, out, mode="foreground", background=graphics, session=CenterPerson())
        self.assertTrue(probe(out)["has_audio"])
        self.assertGreater(self.pixel(out, 32, 32)[0], 170)
        self.assertGreater(self.pixel(out, 2, 2)[2], 170)

    def test_image_and_blur_modes_make_video_with_audio(self):
        from runtime.media.background import edit_background
        from runtime.media.probe import probe

        src = self.source()
        picture = self.tmp / "background.png"
        ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=64x64", "-frames:v", "1", picture)
        for mode, background in (("image", picture), ("blur", None)):
            with self.subTest(mode=mode):
                out = self.tmp / (mode + ".mp4")
                edit_background(src, out, mode=mode, background=background, session=CenterPerson())
                self.assertTrue(probe(out)["has_audio"])
                self.assertAlmostEqual(probe(out)["duration"], 1, delta=0.15)

    def test_failure_does_not_replace_existing_result(self):
        from runtime.media.background import edit_background
        from runtime.media.ffmpeg import MediaError

        src = self.source()
        out = self.tmp / "existing.mp4"
        out.write_bytes(b"keep me")

        class BrokenSession:
            def run(self, names, feeds):
                raise RuntimeError("inference failed")

        with self.assertRaises(MediaError):
            edit_background(src, out, mode="solid", background="#00FF00", session=BrokenSession())
        self.assertEqual(out.read_bytes(), b"keep me")
        self.assertFalse(list(self.tmp.glob(".aiediting-background-*")))

    def test_nonfinite_matte_is_rejected(self):
        import numpy as np

        from runtime.media.background import edit_background
        from runtime.media.ffmpeg import MediaError

        class NanSession(CenterPerson):
            def run(self, names, feeds):
                result = super().run(names, feeds)
                result[1][:] = np.nan
                return result

        out = self.tmp / "nan.mov"
        with self.assertRaisesRegex(MediaError, "NaN"):
            edit_background(self.source(), out, session=NanSession())
        self.assertFalse(out.exists())

    def test_missing_model_does_not_create_output(self):
        from runtime.media.background import edit_background
        from runtime.media.ffmpeg import MediaError

        src = self.source()
        out = self.tmp / "absent.mp4"
        with self.assertRaises(MediaError):
            edit_background(src, out, mode="solid", background="#00FF00",
                            model_path=self.tmp / "absent.onnx")
        self.assertFalse(out.exists())

    def test_missing_background_value_fails_cleanly(self):
        from runtime.media.background import edit_background
        from runtime.media.ffmpeg import MediaError

        with self.assertRaisesRegex(MediaError, "Нужен файл фона"):
            edit_background(self.source(), self.tmp / "image.mp4", mode="image", session=CenterPerson())


if __name__ == "__main__":
    unittest.main()
