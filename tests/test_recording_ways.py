"""The whole path of one video: recording → clean speech → `run.py edit`. A parameter applied twice shows only here."""
import json
import sys
import unittest
from pathlib import Path

from _support import SKILL, TempDirCase, ffmpeg, needs_ffmpeg
from test_pipelines_helpers import Approver, asr_config, profile

KIT = SKILL / "overlay-kit"
for path in (KIT / "tools", SKILL / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import recut  # noqa: E402
import takes  # noqa: E402
import takes_whole  # noqa: E402

try:
    import numpy  # noqa: F401
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
# The job «pins» of ci.yml installs numpy and runs this file on macOS and Windows
needs_numpy = unittest.skipUnless(HAS_NUMPY, "numpy is not installed")

RATE = 1.07
SECONDS = 12.0
SPEECH = (2.0, 10.0)  # the edges of the speech in the recording


def recording(path, rate=30, seconds=SECONDS, speech=SPEECH):
    """A recording with a tone in `speech`, silence around it, and its sound as the mono 48 kHz file the kit reads."""
    on = "between(t,{},{})".format(*speech)
    ffmpeg("-f", "lavfi", "-i", "testsrc=s=320x180:r={}:d={}".format(rate, seconds),
           "-f", "lavfi", "-i", "aevalsrc='if({},0.5*sin(2*PI*440*t),0)':s=48000:d={}".format(on, seconds),
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path))
    audio = Path(path).with_suffix(".wav")
    ffmpeg("-i", str(path), "-vn", "-ac", "1", "-ar", "48000", str(audio))
    return Path(path), audio


@needs_ffmpeg
@needs_numpy
class WholeRecording(TempDirCase):
    def cfg(self, video, audio, speed=RATE, **more):
        out = self.tmp / "clean"
        out.mkdir(exist_ok=True)
        (out / "words.json").write_text(json.dumps(
            [{"c": "A", "a": 2.1, "b": 3.0, "t": "первое"}, {"c": "A", "a": 9.0, "b": 9.8, "t": "последнее"},
             {"c": "A", "a": 11.0, "b": 11.5, "t": "титры"}]), encoding="utf-8")
        return dict({"out": str(out), "speed": speed, "recordings": {"A": {"video": str(video), "audio": str(audio)}}}, **more), out

    def test_trim_keeps_everything_between_the_first_and_last_word_with_sound(self):
        video, audio = recording(self.tmp / "запись.mp4")
        cfg, out = self.cfg(video, audio)
        takes_whole.trim(cfg, out)
        pieces = json.loads((out / "pieces.json").read_text(encoding="utf-8"))
        self.assertEqual(len(pieces), 1)
        self.assertAlmostEqual(pieces[0]["a"], SPEECH[0] - takes_whole.HEAD, delta=0.1)
        self.assertAlmostEqual(pieces[0]["b"], SPEECH[1] + takes_whole.TAIL, delta=0.1, msg="a credit on silence is not speech")
        self.assertAlmostEqual(pieces[0]["to"], (pieces[0]["b"] - pieces[0]["a"]) / RATE, delta=0.001)

    def test_trim_by_hand_wins(self):
        video, audio = recording(self.tmp / "запись.mp4")
        cfg, out = self.cfg(video, audio, trim={"A": [1.0, 11.0]})
        takes_whole.trim(cfg, out)
        pieces = json.loads((out / "pieces.json").read_text(encoding="utf-8"))
        self.assertEqual((pieces[0]["a"], pieces[0]["b"]), (1.0, 11.0))

    def test_the_finished_video_is_the_clean_speech_over_the_speed_once(self):
        from runtime import pipelines
        from runtime.media import probe

        video, audio = recording(self.tmp / "запись.mp4")
        cfg, out = self.cfg(video, audio)
        takes_whole.trim(cfg, out)
        recut.build(cfg, out)
        clean = probe(out / "clean-speech.mov")
        piece = json.loads((out / "pieces.json").read_text(encoding="utf-8"))[0]
        self.assertAlmostEqual(clean["duration"], piece["b"] - piece["a"], delta=0.1, msg="clean speech stays at the recording's speed")
        issue = self.tmp / "выпуск"
        report = pipelines.run(out / "clean-speech.mov", profile(["write_srt"], asr_config(self.tmp, {"bursts": [[8.0, "речь"]]}), speed=RATE),
                               issue, Approver())
        self.assertAlmostEqual(probe(report["output"])["duration"], clean["duration"] / RATE, delta=0.1)
        self.assertIn("применена на этом шаге", report["report"].read_text(encoding="utf-8"))

    def test_a_source_that_is_not_30_fps_keeps_its_length(self):
        from runtime.media import probe

        video, audio = recording(self.tmp / "запись60.mp4", rate=60)
        cfg, out = self.cfg(video, audio, speed=1.0)
        takes_whole.trim(cfg, out)
        recut.build(cfg, out)
        made = probe(out / "clean-speech.mov")
        piece = json.loads((out / "pieces.json").read_text(encoding="utf-8"))[0]
        self.assertAlmostEqual(made["duration"], piece["b"] - piece["a"], delta=0.1)
        self.assertAlmostEqual(made["fps"], 30.0, delta=0.1)

    def test_init_cuts_a_long_recording_for_the_recogniser_in_its_quiet_places(self):
        import numpy as np

        vad = np.ones(50 * 400, dtype=bool)
        vad[50 * 170:50 * 172] = False
        rows = takes_whole._segments(vad)
        self.assertEqual(rows[0], [0.0, 171.0])
        self.assertEqual(rows[-1][1], 400.0)
        self.assertTrue(all(b - a <= takes_whole.LONGEST for a, b in rows[:-1]))


@needs_ffmpeg
class TheMix(TempDirCase):
    def test_a_levelled_sound_lasts_as_long_as_the_picture(self):
        from runtime.media import probe

        video, _ = recording(self.tmp / "рендер.mp4", seconds=6.0, speech=(0.5, 5.5))
        out = self.tmp / "итог.mp4"
        lufs = "loudnorm=I=-14:TP=-1:LRA=11:measured_I=-20:measured_TP=-5:measured_LRA=1:measured_thresh=-30:offset=0:linear=true"
        sys.path.insert(0, str(KIT / "tools"))
        from overlaylib import final

        final.mix(video, out, lufs, 6.0)
        self.assertAlmostEqual(probe(out)["duration"], 6.0, delta=0.05)


@needs_ffmpeg
class TheColour(TempDirCase):
    def make(self, name, *args):
        path = self.tmp / name
        ffmpeg("-f", "lavfi", "-i", "testsrc=s=320x180:r=30:d=1", "-c:v", "libx264", "-preset", "ultrafast", *args, str(path))
        return path

    def test_a_full_range_file_without_tags_is_named_and_a_bt709_one_passes(self):
        from overlaylib import verify

        bad = verify.color_problems(self.make("плохо.mp4", "-pix_fmt", "yuvj420p"))
        self.assertTrue(any("pix_fmt" in p for p in bad) and any("color_space" in p for p in bad))
        good = self.make("хорошо.mp4", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-color_range", "tv",
                         "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709:range=tv")
        self.assertEqual(verify.color_problems(good), [])

    def test_both_renders_ask_for_it(self):
        from unittest import mock
        from overlaylib import remotion, vfinal

        with mock.patch("overlaylib.remotion.run") as run, mock.patch("overlaylib.remotion.os.replace"), mock.patch("overlaylib.remotion.say"):
            remotion.render(self.tmp, self.tmp / "а.mp4", draft=False)
        self.assertIn("--color-space=bt709", run.call_args[0][0])
        with mock.patch("overlaylib.vfinal.run") as run, mock.patch("overlaylib.vfinal.os.replace"):
            vfinal.render_silent(self.tmp, "c1")
        self.assertIn("--color-space=bt709", run.call_args[0][0])


@needs_ffmpeg
@needs_numpy
class CleanSpeechOverALink(TempDirCase):
    def test_a_build_does_not_write_through_a_finished_video_linked_to_it(self):
        import os

        video, audio = recording(self.tmp / "запись.mp4")
        out = self.tmp / "речь"
        out.mkdir()
        (out / "words.json").write_text(json.dumps([{"c": "A", "a": 2.1, "b": 9.8, "t": "речь"}]), encoding="utf-8")
        cfg = {"out": str(out), "speed": 1.0, "recordings": {"A": {"video": str(video), "audio": str(audio)}}}
        takes_whole.trim(cfg, out)
        recut.build(cfg, out)
        linked = self.tmp / "готовое.mp4"
        os.link(str(out / "clean-speech.mov"), str(linked))
        before = linked.read_bytes()
        cfg["trim"] = {"A": [3.0, 8.0]}
        takes_whole.trim(cfg, out)
        recut.build(cfg, out)
        self.assertEqual(linked.read_bytes(), before)


@needs_numpy
class Init(TempDirCase):
    @needs_ffmpeg
    def test_the_config_has_a_real_model_path_and_a_flat_folder(self):
        video, _ = recording(self.tmp / "запись.mp4")
        takes_whole.init(video, self.tmp / "конфиг.json", self.tmp / "речь", 1.07, "~/модели/ggml.bin", "ru", "")
        cfg = json.loads((self.tmp / "конфиг.json").read_text(encoding="utf-8"))
        self.assertNotIn("~", cfg["whisper_model"])
        self.assertEqual(Path(cfg["out"]), (self.tmp / "речь").resolve())
        self.assertEqual(cfg["speed"], 1.07)

    @needs_ffmpeg
    def test_the_config_of_a_recording_is_not_wiped_by_accident(self):
        video, _ = recording(self.tmp / "запись.mp4")
        takes_whole.init(video, self.tmp / "конфиг.json", self.tmp / "речь", 1.0, "м", "ru", "")
        with self.assertRaises(SystemExit):
            takes_whole.init(video, self.tmp / "конфиг.json", self.tmp / "речь", 1.0, "м", "ru", "")
        takes_whole.init(video, self.tmp / "конфиг.json", self.tmp / "речь", 1.0, "м", "ru", "", force=True)

    @needs_ffmpeg
    def test_edges_by_hand_outside_the_recording_are_refused(self):
        video, audio = recording(self.tmp / "запись.mp4")
        out = self.tmp / "речь"
        out.mkdir()
        (out / "words.json").write_text("[]", encoding="utf-8")
        for bad in ([5, 3], [1.0], [0, 99]):
            with self.assertRaises(SystemExit):
                takes_whole.trim({"recordings": {"A": {"video": str(video), "audio": str(audio)}}, "trim": {"A": bad}}, out)

    @needs_ffmpeg
    def test_a_frame_that_is_not_wide_is_refused(self):
        video = self.tmp / "вертикаль.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=black:s=180x320:r=30:d=1", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "1",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(video))
        with self.assertRaises(SystemExit):
            takes_whole.init(video, self.tmp / "к.json", self.tmp / "р", 1.0, "м", "ru", "")


class Takes(unittest.TestCase):
    def test_a_retake_from_earlier_in_the_recording_starts_another_pass(self):
        part = [{"a": 200.0, "b": 210.0}, {"a": 100.0, "b": 110.0}, {"a": 120.0, "b": 130.0}]
        self.assertEqual([len(b) for b in recut.batches(part)], [1, 2])


@needs_ffmpeg
@needs_numpy
class TakesOnARealFile(TempDirCase):
    def test_a_later_take_placed_first_loses_nothing_and_the_picture_follows_the_sound(self):
        from runtime.media import probe

        video, audio = recording(self.tmp / "запись.mp4", speech=(0.5, 11.5))
        out = self.tmp / "речь"
        out.mkdir()
        (out / "words.json").write_text(json.dumps(
            [{"c": "A", "a": 1.0, "b": 2.0, "t": "раз"}, {"c": "A", "a": 2.1, "b": 3.0, "t": "два"},
             {"c": "A", "a": 8.0, "b": 9.0, "t": "три"}, {"c": "A", "a": 9.1, "b": 10.0, "t": "четыре"}]), encoding="utf-8")
        cfg = {"out": str(out), "speed": 1.0, "recordings": {"A": {"video": str(video), "audio": str(audio)}},
               "takes": [["A", 8, "три", "четыре"], ["A", 1, "раз", "два"]]}
        takes.plan(cfg, out)
        pieces = json.loads((out / "pieces.json").read_text(encoding="utf-8"))
        self.assertGreater(pieces[0]["a"], pieces[-1]["a"])
        self.assertEqual({p["clip"] for p in pieces}, {0, 1})
        recut.build(cfg, out)
        made = probe(out / "clean-speech.mov")
        self.assertAlmostEqual(made["duration"], sum(p["b"] - p["a"] for p in pieces), delta=0.15)

    def test_a_mute_at_the_very_start_does_not_stop_the_build(self):
        video, audio = recording(self.tmp / "запись.mp4", speech=(0.5, 11.5))
        out = self.tmp / "речь"
        out.mkdir()
        (out / "pieces.json").write_text(json.dumps([{"c": "A", "a": 0.0, "b": 5.0, "from": 0.0, "to": 5.0, "clip": 0}]), encoding="utf-8")
        (out / "time-map.json").write_text(json.dumps({"mute": [[0.0, 0.5], [4.9999, 5.0]]}), encoding="utf-8")
        recut.build({"out": str(out), "speed": 1.0, "recordings": {"A": {"video": str(video), "audio": str(audio)}}}, out)
        self.assertTrue((out / "clean-speech.mov").is_file())


class Markers(unittest.TestCase):
    def test_a_second_of_the_latest_file_goes_back_to_the_accepted_video(self):
        rows = [[0.0, 4.0, 0.0, 4.0, 0.0], [4.0, 8.0, 6.0, 10.0, 0.0]]
        self.assertEqual(recut.to_old(2.0, rows), 2.0)
        self.assertEqual(recut.to_old(5.0, rows), 7.0)
        self.assertEqual(recut.to_old(5.0, []), 5.0)

    def test_pieces_of_another_rate_move_to_the_seconds_of_the_finished_video(self):
        old = [{"from": 0.0, "to": 10.7, "c": "A", "a": 100.0, "b": 110.7, "clip": 0}]  # written at speed 1.0
        new, moved = recut.at_speed(old, RATE)
        self.assertTrue(moved)
        self.assertAlmostEqual(new[0]["to"], 10.0, delta=0.001)
        again, moved = recut.at_speed(new, RATE)
        self.assertFalse(moved)
        self.assertEqual(again, new)

    def test_a_cut_at_a_second_of_the_finished_video_lands_in_the_recording(self):
        pieces = [{"from": 0.0, "to": 10.0, "c": "A", "a": 100.0, "b": 110.7, "clip": 0}]
        new, meta = recut.edit_pieces(pieces, [[4.0, 6.0]], [], [], [], RATE)
        self.assertAlmostEqual(new[0]["b"], 100.0 + 4.0 * RATE, delta=0.001)
        self.assertAlmostEqual(new[1]["a"], 100.0 + 6.0 * RATE, delta=0.001)
        self.assertAlmostEqual(meta["duration"], 8.0, delta=0.001)


class Coherence(unittest.TestCase):
    def problems(self, steps, **params):
        from aelib.coherence import problems

        return problems({"steps": steps, "params": params})

    def test_clean_speech_goes_only_with_graphics_because_of_its_kit(self):
        self.assertTrue(any("graphics" in p for p in self.problems(["write_srt"], clean_speech=True, recording="trim")))

    def test_clean_speech_on_a_paid_recogniser_names_the_local_model_it_still_needs(self):
        from aelib.coherence import problems

        profile_ = {"steps": ["write_srt", "graphics"], "params": {"clean_speech": True, "recording": "trim"}, "asr": {"provider": "scribe"}}
        self.assertTrue(any("verify_asr.model" in p for p in problems(profile_)))

    def test_clean_speech_needs_the_answer_about_the_recording(self):
        self.assertTrue(any("params.recording" in p for p in self.problems(["write_srt", "graphics"], clean_speech=True)))
        self.assertEqual(self.problems(["write_srt", "graphics"], clean_speech=True, recording="trim"), [])
        self.assertEqual(self.problems(["write_srt", "graphics"], clean_speech=True, recording="takes"), [])

    def test_answers_that_do_not_fit_are_named(self):
        self.assertTrue(self.problems(["cut_spans"], recording="whole"))
        self.assertTrue(self.problems(["cut_spans"], clean_speech=True, recording="takes"))
        self.assertTrue(self.problems(["write_srt"], recording="trim"))
        self.assertTrue(self.problems(["write_srt"], recording="целиком"))
        self.assertTrue(self.problems(["loudnorm", "graphics"]))

    def test_a_format_that_never_asked_is_left_alone(self):
        self.assertEqual(self.problems(["speech_spans", "cut_spans", "loudnorm", "write_srt"], speed=1.07), [])

    def test_every_preset_is_either_coherent_or_waits_only_for_that_question(self):
        from aelib.coherence import problems
        from aelib.paths import PRESETS_DIR

        for path in PRESETS_DIR.glob("*.json"):
            preset = json.loads(path.read_text(encoding="utf-8"))
            found = problems(preset)
            self.assertTrue(all("params.recording" in p for p in found), "{}: {}".format(path.name, found))

    def test_a_format_on_clean_speech_needs_local_whisper_whatever_writes_the_srt(self):
        import os
        import subprocess

        draft = Path(self.tmp_dir.name) / "монтаж-проба"
        draft.mkdir()
        profile_ = {"format": "проба", "skill_name": "монтаж-проба", "language": "ru", "output_dir": "выпуски", "approval": "auto", "design": "design/",
                    "asr": {"provider": "scribe", "language": "ru", "model": None, "base_url": None, "api_key_env": "K", "command": None},
                    "steps": ["write_srt", "graphics"], "taste": [],
                    "params": {"clean_speech": True, "recording": "trim", "speed": 1.07,
                               "verify_asr": {"provider": "whispercpp", "language": "ru", "model": "/модели/ggml.bin"}}}
        (draft / "profile.json").write_text(json.dumps(profile_), encoding="utf-8")
        done = subprocess.run([sys.executable, str(SKILL / "tools" / "ae.py"), "build-skill", str(draft / "profile.json"), str(draft.parent / "out")],
                              capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, AIEDITING_WORK=str(draft.parent)))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        pins = json.loads((draft.parent / "out" / "монтаж-проба" / "pins.json").read_text(encoding="utf-8"))
        self.assertIn("whisper-cpp", pins["tools"])
        text = (draft.parent / "out" / "монтаж-проба" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("First make the clean speech", text)
        self.assertNotIn("{{", text)

    def setUp(self):
        import tempfile

        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)


class TheSample(unittest.TestCase):
    def test_the_sample_shows_what_the_brief_asks_for_on_a_stage(self):
        text = (KIT / "examples" / "seg-a.tsx").read_text(encoding="utf-8")
        stage = text[text.index("// ───────── Scene 2"):text.index("// ───────── Scene 4")]  # the corner cards of a full frame have their own sizes
        import re

        for name, least in (("H2", 60), ("Lead", 32), ("Pill", 32), ("Txt", 32)):
            for size in re.findall(r"<{} [^>]*size=\{{(\d+)\}}".format(name), stage):
                self.assertGreaterEqual(int(size), least, name)
        scene2 = stage[:stage.index("// ───────── Scene 3")]
        self.assertTrue(all(float(a) < 13.7 + 0.85 for a in re.findall(r"<Appear at=\{([\d.]+)\}", scene2)[:2]), "the stage is full when the change ends")


class TheMethodAndThePipelineAgree(unittest.TestCase):
    def read(self, *parts):
        return (SKILL.joinpath(*parts)).read_text(encoding="utf-8")

    def test_only_the_pipeline_applies_the_speed(self):
        self.assertNotIn("atempo", self.read("overlay-kit", "tools", "recut.py"))
        self.assertNotIn("setpts=PTS/", self.read("overlay-kit", "tools", "recut.py"))
        self.assertIn("speed_up", self.read("runtime", "pipelines", "render.py"))
        self.assertEqual(json.loads(self.read("catalog", "params.json"))["params"]["speed"]["owner"].split(",")[0],
                         "runtime/pipelines/render.py")

    def test_the_interview_asks_about_the_recording_first_and_in_order(self):
        text = self.read("phases", "interview.md")
        self.assertLess(text.index("## The first round: the recording"), text.index("## Themes"))
        self.assertLess(text.index("**Do we cut the recording"), text.index("**Do we speed it up"))
        self.assertLess(text.index("**Do we speed it up"), text.index("**Where does the text of the speech"))

    def test_the_built_method_names_the_way_of_this_format(self):
        from aelib import skillmd

        steps = {"steps": {"write_srt": {"what": "x"}, "graphics": {"what": "y"}}}
        for way, word in (("trim", "«trim»"), ("takes", "«takes»")):
            profile_ = {"format": "ф", "skill_name": "монтаж-ф", "language": "ru", "asr": {"provider": "whispercpp"},
                        "steps": ["write_srt", "graphics"], "params": {"clean_speech": True, "recording": way}, "taste": []}
            text = skillmd.render(profile_, {"tools": []}, steps, {}, "0")
            self.assertIn(word, text)
            self.assertNotIn("{{", text)
            self.assertIn("takes.py trim", text)
            self.assertIn("run.py edit` applies the speed", text)


if __name__ == "__main__":
    unittest.main()
