"""Real, short media and subtitle cases for reusable finishing recipes."""
import argparse
import importlib.util
import subprocess
import sys
import unittest

from _support import SKILL, TempDirCase, ffmpeg, make_tone, needs_ffmpeg

sys.path.insert(0, str(SKILL / "tools"))
from recipe_lib import finishing  # noqa: E402
from recipe_lib.common import RecipeError  # noqa: E402
from runtime.media.probe import probe  # noqa: E402

HAVE_PYSUBS2 = importlib.util.find_spec("pysubs2") is not None


def has_filter(name):
    try:
        result = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True, timeout=10)
        return result.returncode == 0 and any(line.split()[1:2] == [name] for line in result.stdout.splitlines()
                                                 if len(line.split()) >= 2)
    except (OSError, subprocess.SubprocessError):
        return False


class FinishingRecipes(TempDirCase):
    def command(self, *args):
        parser = argparse.ArgumentParser()
        finishing.register(parser.add_subparsers(dest="cmd", required=True))
        return parser.parse_args(map(str, args))

    def rotated_source(self):
        upright = make_tone(self.tmp / "upright.mp4", duration=1, size="240x320")
        coded = self.tmp / "coded.mp4"
        rotated = self.tmp / "rotated.mp4"
        ffmpeg("-i", upright, "-vf", "transpose=1", "-c:v", "libx264", "-preset", "ultrafast",
               "-c:a", "copy", coded)
        ffmpeg("-display_rotation", "90", "-i", coded, "-c", "copy", rotated)
        self.assertIn(probe(rotated)["rotation"], (90, 270))
        return coded, rotated

    @unittest.skipUnless(HAVE_PYSUBS2, "pysubs2 is installed by AIEditing setup")
    def test_srt_to_vtt_shift_preserves_timing_and_source(self):
        import pysubs2

        source = self.tmp / "source.srt"
        source.write_text("1\n00:00:00,500 --> 00:00:01,200\nHello\n", encoding="utf-8")
        before = source.read_bytes()
        output = self.tmp / "retimed.vtt"
        result = self.command("subtitle-convert", source, output, "--shift-ms", "250").handler(
            self.command("subtitle-convert", source, output, "--shift-ms", "250"))
        event = pysubs2.load(output)[0]
        self.assertEqual((event.start, event.end), (750, 1450))
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(result["events"], 1)

    @unittest.skipUnless(HAVE_PYSUBS2, "pysubs2 is installed by AIEditing setup")
    def test_retime_rejects_negative_cue_before_writing(self):
        source = self.tmp / "source.srt"
        source.write_text("1\n00:00:00,100 --> 00:00:00,600\nHello\n", encoding="utf-8")
        output = self.tmp / "bad.srt"
        opt = self.command("subtitle-convert", source, output, "--shift-ms", "-200")
        with self.assertRaises(RecipeError):
            opt.handler(opt)
        self.assertFalse(output.exists())

    @unittest.skipUnless(HAVE_PYSUBS2, "pysubs2 required")
    def test_styled_vtt_cannot_silently_lose_css_and_position(self):
        source = self.tmp / "positioned.vtt"
        source.write_text("WEBVTT\n\nSTYLE\n::cue { color: lime; }\n\n"
                          "00:00:00.100 --> 00:00:00.700 position:10% align:start\nHello\n", encoding="utf-8")
        target = self.tmp / "shifted.vtt"
        opt = self.command("subtitle-convert", source, target, "--shift-ms", "250")
        with self.assertRaisesRegex(RecipeError, "WebVTT"):
            opt.handler(opt)
        self.assertFalse(target.exists())
        opt = self.command("subtitle-convert", source, target, "--shift-ms", "250", "--allow-style-loss")
        result = opt.handler(opt)
        self.assertTrue(result["style_loss"])
        self.assertIn("cue_settings", result["style_loss_features"])

    @needs_ffmpeg
    @unittest.skipUnless(HAVE_PYSUBS2, "pysubs2 required")
    def test_ass_different_bundled_font_does_not_claim_it_is_used(self):
        import pysubs2
        video = make_tone(self.tmp / "font-video.mp4", duration=1)
        subs = pysubs2.SSAFile()
        subs.styles["Default"].fontname = "Arial"
        subs.events.append(pysubs2.SSAEvent(start=100, end=700, text="Hello"))
        source = self.tmp / "arial.ass"; subs.save(source)
        target = self.tmp / "must-not-render.mp4"
        font = SKILL / "design" / "chrome-graphite" / "fonts" / "Onest.ttf"
        opt = self.command("subtitle-burn", video, source, target, "--font-file", font, "--font-family", "Onest")
        with self.assertRaisesRegex(RecipeError, "restyle"):
            opt.handler(opt)
        self.assertFalse(target.exists())

    @needs_ffmpeg
    @unittest.skipUnless(HAVE_PYSUBS2 and has_filter("ass"), "pysubs2 and FFmpeg ass filter required")
    def test_burn_subtitles_with_font_from_space_path_keeps_audio(self):
        video = make_tone(self.tmp / "source video.mp4", duration=2)
        subs = self.tmp / "русский caption.srt"
        subs.write_text("1\n00:00:00,400 --> 00:00:01,300\nHello world\n", encoding="utf-8")
        output = self.tmp / "burned output.mp4"
        font = SKILL / "design" / "chrome-graphite" / "fonts" / "Onest.ttf"
        opt = self.command("subtitle-burn", video, subs, output, "--font-file", font,
                           "--font-family", "Onest")
        result = opt.handler(opt)
        info = probe(output)
        self.assertTrue(info["has_video"] and info["has_audio"])
        self.assertAlmostEqual(info["duration"], 2, delta=0.15)
        self.assertEqual(result["output"], str(output.resolve()))

    @needs_ffmpeg
    @unittest.skipUnless(HAVE_PYSUBS2, "pysubs2 is installed by AIEditing setup")
    def test_ass_style_change_requires_explicit_restyle(self):
        import pysubs2

        video = make_tone(self.tmp / "source.mp4", duration=1)
        subs = pysubs2.SSAFile()
        subs.events.append(pysubs2.SSAEvent(start=100, end=700, text="Hello"))
        source = self.tmp / "styled.ass"
        subs.save(source)
        output = self.tmp / "styled.mp4"
        opt = self.command("subtitle-burn", video, source, output, "--font-size", "36")
        with self.assertRaises(RecipeError):
            opt.handler(opt)
        self.assertFalse(output.exists())

    @needs_ffmpeg
    @unittest.skipUnless(HAVE_PYSUBS2 and has_filter("ass"), "pysubs2 and FFmpeg ass filter required")
    def test_rotated_phone_uses_shown_canvas_for_generated_ass(self):
        import pysubs2
        from unittest import mock

        _, video = self.rotated_source()
        subs = self.tmp / "captions.srt"
        subs.write_text("1\n00:00:00,100 --> 00:00:00,700\nHello\n", encoding="utf-8")
        output = self.tmp / "phone-captioned.mp4"
        original = finishing.ffmpeg
        canvas = {}

        def capture(args, **kwargs):
            ass = pysubs2.load(kwargs["cwd"] / "sub.ass")
            canvas["size"] = (int(ass.info["PlayResX"]), int(ass.info["PlayResY"]))
            return original(args, **kwargs)

        opt = self.command("subtitle-burn", video, subs, output)
        with mock.patch.object(finishing, "ffmpeg", side_effect=capture):
            opt.handler(opt)
        self.assertEqual(canvas["size"], (240, 320))
        self.assertEqual((probe(output)["width"], probe(output)["height"]), (240, 320))

    @needs_ffmpeg
    @unittest.skipUnless(has_filter("vidstabdetect") and has_filter("vidstabtransform"), "full FFmpeg required")
    def test_stabilize_a_trimmed_clip_preserves_audio_and_source(self):
        video = make_tone(self.tmp / "camera source.mp4", duration=2)
        before = video.read_bytes()
        output = self.tmp / "stable clip.mp4"
        opt = self.command("stabilize", video, output, "--start", "0.2", "--duration", "1.2")
        result = opt.handler(opt)
        info = probe(output)
        self.assertTrue(info["has_audio"])
        self.assertAlmostEqual(info["duration"], 1.2, delta=0.15)
        self.assertEqual(video.read_bytes(), before)
        self.assertEqual(result["output"], str(output.resolve()))
        self.assertEqual(list(self.tmp.glob("*.trf")), [])

    @needs_ffmpeg
    @unittest.skipUnless(has_filter("libvmaf"), "FFmpeg libvmaf required")
    def test_identical_aligned_video_has_high_vmaf(self):
        video = make_tone(self.tmp / "same.mp4", duration=1)
        opt = self.command("quality", video, video, "--aligned-same-content")
        result = opt.handler(opt)
        self.assertGreaterEqual(result["vmaf"], 90.0)

    @needs_ffmpeg
    def test_quality_refuses_different_geometry_before_metric(self):
        first = make_tone(self.tmp / "a.mp4", duration=1, size="160x120")
        second = make_tone(self.tmp / "b.mp4", duration=1, size="320x240")
        opt = self.command("quality", first, second, "--aligned-same-content")
        with self.assertRaises(RecipeError):
            opt.handler(opt)

    @needs_ffmpeg
    def test_quality_refuses_same_stored_size_with_different_display_rotation(self):
        coded, rotated = self.rotated_source()
        self.assertEqual((probe(coded)["width"], probe(coded)["height"]),
                         (probe(rotated)["width"], probe(rotated)["height"]))
        opt = self.command("quality", coded, rotated, "--aligned-same-content")
        with self.assertRaisesRegex(RecipeError, "ориентац"):
            opt.handler(opt)


if __name__ == "__main__":
    unittest.main()
