"""Clips of a finished video: the picture whole in the centre, a headline and a call to action on the fields."""
import unittest

from _support import TempDirCase, ffmpeg, needs_ffmpeg
from test_pipelines_helpers import Approver, asr_config, profile
from test_vertical_source import horizontal


def said(start, count, step=2.0):
    return [{"text": "слово{}{}".format(i, "." if i % 5 == 4 else ""), "start": start + i * step,
             "end": start + i * step + step - 0.1} for i in range(count)]


class Wrapping(unittest.TestCase):
    def test_a_dash_keeps_to_the_word_before_and_a_short_word_to_the_word_after(self):
        from runtime.render.lines import tokens

        self.assertEqual(tokens("В МОЁМ СТИЛЕ — ПОКАЗЫВАЮ ПО ШАГАМ"),
                         ["В МОЁМ", "СТИЛЕ —", "ПОКАЗЫВАЮ", "ПО ШАГАМ"])

    def test_a_clip_pointing_outside_itself_loses_points(self):
        from runtime.pipelines.clips import _score

        def phrase(text):
            return [{"text": text, "start": 0.0, "end": 20.0,
                     "words": [{"text": w, "start": 0.0, "end": 0.5} for w in text.split()]}]

        plain = _score(phrase("Самое важное это начать сегодня."))
        outside = _score(phrase("Самое важное лежит под этим видео."))
        self.assertEqual(plain["total"] - outside["total"], 3)
        self.assertEqual(outside["outside"], -3)


class Picture(TempDirCase):
    def test_both_fields_are_drawn_and_the_picture_stays_clear(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("нет Pillow")
        from runtime.render.band import band

        out = band("НАУЧИЛ ДЕЛАТЬ ДИЗАЙН В МОЁМ СТИЛЕ — ПОКАЗЫВАЮ ПО ШАГАМ", "Хотите урок? Напишите «УРОК» — пришлю ссылку.",
                   None, picture_height=608, out=self.tmp / "поля.png")
        alpha = Image.open(out).getchannel("A")
        self.assertEqual(alpha.size, (1080, 1920))
        self.assertIsNotNone(alpha.crop((0, 0, 1080, 656)).getbbox(), "заголовок")
        self.assertIsNotNone(alpha.crop((0, 1264, 1080, 1920)).getbbox(), "призыв")
        self.assertIsNone(alpha.crop((0, 656, 1080, 1264)).getbbox(), "картинка свободна")

    def test_a_long_headline_shrinks_to_fit_its_field(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("нет Pillow")
        from runtime.render.band import band

        out = band("ОЧЕНЬ ДЛИННЫЙ ЗАГОЛОВОК " * 6, "", None, picture_height=608, out=self.tmp / "поля.png")
        box = Image.open(out).getchannel("A").getbbox()
        self.assertGreaterEqual(box[1], 0)
        self.assertLess(box[3], 656)


@needs_ffmpeg
class Clips(TempDirCase):
    def clips_answer(self, payload):
        payload["items"] = [{"id": "c01", "name": "1 — проба", "start": 5.0, "end": 45.0, "drop": [[15.0, 25.0]],
                             "headline": "ЗАГОЛОВОК ОТРЫВКА", "said": "проба"}]
        payload["chosen"] = ["c01"]

    def run_clip(self, **params):
        from runtime import pipelines

        src = horizontal(self.tmp / "готовый.mp4", 90)
        words = {"words": said(0.0, 44)}
        prof = profile(["speech_spans", "vertical", "bands"], asr_config(self.tmp, words), vertical_source="clips",
                       layout={"kind": "native", "background": "#000000"}, clips=[1, 1], max_seconds=60, **params)
        approve = Approver(edits={"clips": self.clips_answer})
        return pipelines.run(src, prof, self.tmp / "выпуск", approve)

    def test_the_clip_has_its_name_its_length_without_the_drop_and_a_black_field(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("нет Pillow")
        from runtime.media import probe

        report = self.run_clip(cta="Напишите «УРОК»", speed=1.25)
        video = report["output"]
        self.assertEqual(video.name, "1 — проба.mp4")
        info = probe(video)
        self.assertEqual((info["width"], info["height"]), (1080, 1920))
        self.assertAlmostEqual(info["duration"], 30.0 / 1.25, delta=1.0)
        frame = self.tmp / "кадр.png"
        ffmpeg("-i", str(video), "-frames:v", "1", str(frame))
        pixels = Image.open(frame).convert("RGB")
        self.assertLess(max(pixels.getpixel((5, 5))), 12, "поле чёрное")
        self.assertGreater(min(pixels.getpixel((540, 960))), 80, "картинка по центру")

    def test_the_limit_counts_the_finished_clip_not_the_source(self):
        from unittest import mock

        from runtime.pipelines.context import Context
        from runtime.pipelines.vertical_source import stretches

        src = horizontal(self.tmp / "готовый.mp4", 200)
        prof = profile(["speech_spans", "vertical"], asr_config(self.tmp, {"words": said(0.0, 95)}),
                       vertical_source="clips", clips=[1, 3], max_seconds=60, speed=1.5)
        with mock.patch("runtime.pipelines.clips.candidates", return_value=[]) as found:
            stretches(Context(src, prof, self.tmp / "выпуск", Approver()))
        self.assertEqual(found.call_args.kwargs["max_s"], 90.0, "до 90 с исходника при скорости 1,5")


class Refused(TempDirCase):
    """What cannot work is refused before the questions and the rendering."""

    def refused(self, source_size=None, **params):
        from runtime import pipelines
        from runtime.pipelines.errors import PipelineError

        src = horizontal(self.tmp / "готовый.mp4", 5)
        base = dict(layout={"kind": "native"}, cta="Напишите «УРОК»")
        base.update(params)
        approve = Approver()
        with self.assertRaises(PipelineError) as caught:
            pipelines.run(src, profile(["bands", "vertical"], asr_config(self.tmp, {"words": []}), **base),
                          self.tmp / "выпуск", approve)
        self.assertEqual(approve.asked, [], "ни одного вопроса до отказа")
        return str(caught.exception)

    @needs_ffmpeg
    def test_a_crop_has_no_fields(self):
        self.assertIn("native", self.refused(layout="auto"))

    @needs_ffmpeg
    def test_a_colour_ffmpeg_would_refuse(self):
        self.assertIn("#000000", self.refused(layout={"kind": "native", "background": "#000"}))

    @needs_ffmpeg
    def test_a_call_to_action_too_long_to_read(self):
        self.assertIn("Призыв", self.refused(cta="Напиши слово " * 10))

    @needs_ffmpeg
    def test_a_design_without_the_element(self):
        import json

        (self.tmp / "свой").mkdir()
        (self.tmp / "свой" / "tokens.json").write_text(json.dumps({"color": {}, "video": {}}), encoding="utf-8")
        from runtime import pipelines
        from runtime.pipelines.errors import PipelineError

        src = horizontal(self.tmp / "готовый.mp4", 5)
        prof = dict(profile(["bands"], asr_config(self.tmp, {"words": []}), layout={"kind": "native"}),
                    design=str(self.tmp / "свой"))
        with self.assertRaises(PipelineError) as caught:
            pipelines.run(src, prof, self.tmp / "выпуск", Approver())
        self.assertIn("video.band", str(caught.exception))


class Names(unittest.TestCase):
    def test_a_name_has_no_folders_and_nothing_a_disk_refuses(self):
        from runtime.pipelines.bands import clean_name

        self.assertEqual(clean_name("../почему/дизайн?"), "почему дизайн")
        self.assertEqual(clean_name("скидка 50%"), "скидка 50")
        self.assertEqual(clean_name("..."), "")


class Documented(unittest.TestCase):
    def test_the_format_is_offered_and_its_steps_exist(self):
        import json

        from _support import SKILL

        catalog = json.loads((SKILL / "catalog" / "formats.json").read_text(encoding="utf-8"))
        entry = next(f for f in catalog["formats"] if f["word"] == "нарезка")
        preset = json.loads((SKILL / "templates" / "profiles" / (entry["preset"] + ".json")).read_text(encoding="utf-8"))
        steps = json.loads((SKILL / "catalog" / "steps.json").read_text(encoding="utf-8"))["steps"]
        for step in preset["steps"]:
            self.assertIn(step, steps)
        tokens = json.loads((SKILL / "design" / "chrome-graphite" / "tokens.json").read_text(encoding="utf-8"))
        self.assertIn("band", tokens["video"])
        self.assertIn("teaser", tokens["video"])

    def test_the_built_skill_carries_the_method_only_when_it_has_the_step(self):
        import sys

        from _support import SKILL

        sys.path.insert(0, str(SKILL / "tools"))
        from aelib.skillmd import _method

        self.assertIn("## Clips from a finished video", _method({"steps": ["vertical", "bands"]}))
        self.assertNotIn("## Clips from a finished video", _method({"steps": ["vertical"]}))


if __name__ == "__main__":
    unittest.main()
