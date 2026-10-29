"""Vertical plan: a recording shot vertically is cut whole (no clip pick, no 60 s limit); a long horizontal one
is still cut into scored clips. `params.vertical_source` (auto · native · clips) overrides the guess."""
import unittest

from _support import TempDirCase, ffmpeg, make_av, needs_ffmpeg
from test_pipelines_helpers import Approver, asr_config, profile
from test_pipelines_vertical import long_words

SPEECH = [(1, 15), (19, 33), (37, 51), (55, 69), (73, 87)]  # 70 s of speech in a 90 s recording
WORDS = {"words": [{"text": "слово{}.".format(i), "start": a + 0.1, "end": a + 1.0} for i, (a, _) in enumerate(SPEECH)]}


class Stop(Exception):
    pass


def stretch_of(case, src, words, **params):
    """Asks the plan only: the payload of «vertical» (the pieces) and the keys asked before it."""
    from runtime import pipelines
    from runtime.pipelines.errors import PipelineError

    seen = {}
    approve = Approver(answers={"vertical": False}, edits={"vertical": lambda p: seen.update(p)})
    prof = profile(["speech_spans", "vertical"], asr_config(case.tmp, words), layout="face_full",
                   face={"x": 60, "y": 40, "w": 40, "h": 60}, **params)
    with case.assertRaises(PipelineError):
        pipelines.run(src, prof, case.tmp / "выпуск", approve)
    return seen.get("pieces"), approve.asked


def horizontal(path, seconds):
    ffmpeg("-f", "lavfi", "-i", "color=c=gray:s=320x180:r=25:d={}".format(seconds),
           "-f", "lavfi", "-i", "sine=f=440:d={}".format(seconds), "-c:v", "libx264", "-preset", "ultrafast",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path))
    return path


@needs_ffmpeg
class VerticalSource(TempDirCase):
    def portrait(self):
        return make_av(self.tmp / "вертикаль.mp4", SPEECH, 90, size="180x320", rate=25)

    def test_portrait_recording_is_cut_whole_to_the_length_of_the_speech(self):
        from runtime import pipelines
        from runtime.media import probe

        prof = profile(["speech_spans", "vertical"], asr_config(self.tmp, WORDS))
        approve = Approver()
        report = pipelines.run(self.portrait(), prof, self.tmp / "выпуск", approve)
        self.assertNotIn("clips", approve.asked)
        self.assertEqual(len(report["outputs"]), 1)
        length = probe(report["output"])["duration"]
        self.assertGreater(length, 68.0, "the 60 s limit must not cut the speech")
        self.assertLess(length, 74.0, "pauses are cut out")

    def test_horizontal_90_s_still_goes_through_clip_pick_with_the_limit(self):
        src = horizontal(self.tmp / "горизонталь.mp4", 90)
        pieces, asked = stretch_of(self, src, long_words(90), max_seconds=60, clips=[5, 10])
        self.assertIn("clips", asked)
        self.assertTrue(pieces and all(p["end"] - p["start"] <= 60 for p in pieces), pieces)

    def test_native_overrides_the_guess_for_a_horizontal_source(self):
        src = horizontal(self.tmp / "горизонталь.mp4", 90)
        pieces, asked = stretch_of(self, src, long_words(90), vertical_source="native")
        self.assertNotIn("clips", asked)
        self.assertEqual(len(pieces), 1)
        self.assertGreater(pieces[0]["end"] - pieces[0]["start"], 80)

    def test_clips_overrides_the_guess_for_a_portrait_source(self):
        pieces, asked = stretch_of(self, self.portrait(), long_words(90), vertical_source="clips")
        self.assertIn("clips", asked)

    def test_auto_is_the_same_as_no_param(self):
        pieces, asked = stretch_of(self, self.portrait(), WORDS, vertical_source="auto")
        self.assertNotIn("clips", asked)
        self.assertGreater(pieces[0]["end"] - pieces[0]["start"], 80)


class Documented(unittest.TestCase):
    def test_template_and_interview_table_name_the_mode(self):
        import json

        from _support import SKILL

        template = json.loads((SKILL / "templates" / "profiles" / "vertical.json").read_text(encoding="utf-8"))
        self.assertEqual(template["params"]["vertical_source"], "auto")
        rows = (SKILL / "phases" / "interview.md").read_text(encoding="utf-8").splitlines()
        row = next(r for r in rows if r.startswith("| Vertical"))
        self.assertIn("`params.vertical_source`", row)
        for word in ("`native`", "`clips`", "`auto`"):
            self.assertIn(word, row)


if __name__ == "__main__":
    unittest.main()
