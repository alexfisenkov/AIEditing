"""The `timeline` step: next to the video a FCPXML timeline of its layers and a note how to open it in DaVinci Resolve."""
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from urllib.parse import unquote, urlparse

from _support import TempDirCase, ffmpeg, make_av, needs_ffmpeg
from test_pipelines_helpers import LESSON, LESSON_SECONDS, Approver, asr_config, bursts, profile


def secs(value) -> Fraction:
    return Fraction(str(value).rstrip("s"))


def lanes(path):
    """{lane name: [(timeline second, own start, length, element)]} and {marker text: timeline second}."""
    root = ET.parse(str(path)).getroot()
    files = {a.get("id"): Path(unquote(urlparse(a.find("media-rep").get("src")).path)) for a in root.iter("asset")}
    out, marks = {}, {}
    for host in root.find("library/event/project/sequence/spine"):
        base = secs(host.get("offset")) - secs(host.get("start", "0s"))
        rows = [host] + [c for c in host if c.tag in ("asset-clip", "video")]
        for c in rows:
            if c.tag == "gap":
                continue
            at = secs(c.get("offset")) if c is host else base + secs(c.get("offset"))
            out.setdefault(c.get("name").split(" · ")[0], []).append((at, secs(c.get("start")), secs(c.get("duration")),
                                                                     c, files[c.get("ref")]))
        for m in host.findall("marker"):
            marks[m.get("value")] = base + secs(m.get("start"))
    return out, marks


class Ctx:
    """The part of a run the timeline reads."""

    def __init__(self, outdir, src, keep, **extra):
        self.outdir, self.src, self.keep = outdir, src, keep
        self.params = dict(extra.pop("params", {}))
        self.steps = extra.pop("steps", ["timeline"])
        self.broll, self.chapters, self.music, self.notes = [], [], {}, []
        self.report = {"cuts": []}
        self.info = {"duration": 20.0}
        for k, v in extra.items():
            setattr(self, k, v)

    def p(self, name, default=None):
        value = self.params.get(name)
        return default if value is None else value

    def has(self, step):
        return step in self.steps

    def note(self, text):
        self.notes.append(text)


@needs_ffmpeg
class Layers(TempDirCase):
    def setUp(self):
        super().setUp()
        self.out = self.tmp / "выпуск"
        self.out.mkdir()
        self.src = make_av(self.tmp / "запись.mp4", [(1.0, 3.0)], 20.0, size="320x180", rate=25)
        self.final = make_av(self.out / "запись-монтаж.mp4", [(1.0, 3.0)], 14.0, size="320x180", rate=25)
        self.photo = self.tmp / "библиотека" / "море.jpg"
        self.photo.parent.mkdir()
        ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=320x180:d=1", "-frames:v", "1", str(self.photo))
        self.plate = self.tmp / ".aiediting-run" / "плашки" / "chapter-000.png"
        self.plate.parent.mkdir(parents=True)
        ffmpeg("-f", "lavfi", "-i", "color=c=black@0.0:s=320x180:d=1", "-frames:v", "1", str(self.plate))

    def ctx(self, **extra):
        ctx = Ctx(self.out, self.src, [(0.0, 4.0), (6.0, 16.0)], **extra)
        ctx.broll = [{"start": 8.0, "end": 12.0, "file": str(self.photo), "from": 0.0, "phrase": "у моря", "kind": "photo",
                      "who": [], "shown": "море.jpg"}]
        ctx.chapters = [{"start": 0.0, "title": "Начало"}, {"start": 7.0, "title": "Море"}]
        ctx.report = {"cuts": [{"start": 4.0, "end": 6.0, "why": "дубль: «я был»"}, {"start": 16.0, "end": 20.0, "why": "пауза"}]}
        return ctx

    def test_the_layers_of_the_cut_lie_on_their_lanes_with_markers(self):
        from runtime.pipelines.timeline_export import NOTE, write_timeline

        pictures = [{"png": self.plate, "start": 0.6, "end": 3.6}]
        path = write_timeline(self.ctx(), self.final, pictures)
        self.assertEqual(path, self.out / "запись-монтаж.fcpxml")
        got, marks = lanes(path)
        cam = got["Камера"]
        self.assertEqual([(a, s, d) for a, s, d, _, _ in cam], [(0, 0, 4), (4, 6, 10)])
        self.assertEqual({f for *_, f in cam}, {self.src.resolve()})
        (at, _s, length, el, f), = got["Вставки"]
        self.assertEqual((at, length, f), (6, 4, self.photo.resolve()))  # 8 s of the source is 6 s of the cut
        (at, _s, length, el, f), = got["Плашки"]
        self.assertEqual((at, length), (Fraction(3, 5), 3))
        self.assertTrue(f.is_file() and self.out.resolve() in f.parents, "the plate is kept next to the video: the run folder goes")
        self.assertEqual(marks, {"Начало": 0, "Море": 5, "вставка: у моря": 6, "правка: дубль: «я был»": 4})
        note = (self.out / NOTE).read_text(encoding="utf-8")
        self.assertIn("Файл → Импорт → Таймлиния", note)
        self.assertIn("запись-монтаж.fcpxml", note)
        for lane in ("Камера", "Вставки", "Плашки"):
            self.assertIn(lane, note)
        self.assertIn("не перенёсся", note)  # what to do when a layer did not come through
        for text in (note, path.read_text(encoding="utf-8")):
            self.assertNotIn("Final Cut", text)

    def test_music_variants_lie_on_their_own_lanes_switched_off(self):
        from runtime.pipelines.timeline_export import write_timeline

        beds = self.out / "музыка-варианты"
        beds.mkdir()
        for k in (1, 2, 3):
            ffmpeg("-f", "lavfi", "-i", "sine=f=300:d=14", str(beds / "вариант-{}.m4a".format(k)))
        ctx = self.ctx(steps=["timeline", "music"])
        ctx.music = {"track": beds / "вариант-1.m4a", "tracks": [beds / "вариант-1.m4a"], "variants": 3, "db": -20.0, "outdir": self.out}
        got, _ = lanes(write_timeline(ctx, self.final))
        names = sorted(n for n in got if n.startswith("Музыка"))
        self.assertEqual(names, ["Музыка", "Музыка, вариант 2", "Музыка, вариант 3"])
        self.assertEqual([got[n][0][3].get("enabled", "1") for n in names], ["1", "0", "0"])
        self.assertTrue(all(int(got[n][0][3].get("lane")) < 0 for n in names))

    def test_two_cameras_and_a_recorder_lie_as_the_program_of_angles(self):
        from runtime.pipelines.timeline_export import NOTE, write_timeline

        side = make_av(self.tmp / "камера B.mp4", [(2.0, 4.0)], 21.0, size="320x180", rate=25)
        sound = self.tmp / "рекордер.wav"
        ffmpeg("-f", "lavfi", "-i", "sine=f=1000:sample_rate=48000:d=21", str(sound))
        push, crop = {"zoom": 1.0, "to": 1.04, "y": 0.3}, {"zoom": 1.2, "y": 0.3}
        ctx = self.ctx(steps=["timeline", "angles"], cameras=[side], audio_src=sound,
                       offsets={str(side): 1.0, str(sound): -0.6},  # B started 1 s after the main camera, the recorder 0.6 s before
                       angles=[{"start": 0.0, "end": 3.0, "camera": 0, "crop": push},
                               {"start": 3.0, "end": 9.0, "camera": 1, "crop": None},
                               {"start": 9.0, "end": 14.0, "camera": 0, "crop": crop}])
        path = write_timeline(ctx, self.final)
        got, marks = lanes(path)
        cam = got["Камера"]
        # kept 0–4 and 6–16 of the main camera: 0–3 main, 3–4 and 4–9 camera B (1 s earlier in its file), 9–14 main
        self.assertEqual([(a, s, d, f) for a, s, d, _, f in cam],
                         [(0, 0, 3, self.src.resolve()), (3, 2, 1, side.resolve()), (4, 5, 5, side.resolve()),
                          (9, 11, 5, self.src.resolve())])
        self.assertTrue(all(el.get("srcEnable") == "video" for *_, el, _f in cam), "the cameras' own sound is off")
        looks = [el.find("adjust-transform") for *_, el, _f in cam]
        self.assertEqual([t is not None for t in looks], [True, False, False, True])
        self.assertEqual(looks[3].get("scale"), "1.2 1.2")
        self.assertEqual(len(list(looks[0].iter("keyframe"))), 4)  # the push-in: scale and position, start and end
        voice = got["Голос"]
        self.assertEqual([(a, s, d, f) for a, s, d, _, f in voice], [(0, Fraction(3, 5), 4, sound.resolve()),
                                                                      (4, Fraction(33, 5), 10, sound.resolve())])
        self.assertTrue(all(int(el.get("lane")) < 0 for *_, el, _f in voice))
        self.assertEqual(marks["Море"], 5)
        note = (self.out / NOTE).read_text(encoding="utf-8")
        self.assertIn("«Голос»", note)
        self.assertIn("рекордер.wav", note)
        self.assertNotIn("Голос — это звук клипов «Камера»", note)
        self.assertIn("камера B.mp4", note)

    def test_the_method_names_the_timeline_where_the_code_puts_it(self):
        from _support import SKILL

        method = (SKILL / "templates" / "format-skill" / "method" / "timeline.md").read_text(encoding="utf-8")
        self.assertNotIn("таймлиния/<name>.fcpxml", method)
        self.assertIn("<name>.fcpxml", method)  # next to the video, as write_timeline and overlay.py timeline write it

    def test_picture_mode_is_the_finished_video_in_one_clip(self):
        from runtime.pipelines.timeline_export import write_timeline

        got, marks = lanes(write_timeline(self.ctx(params={"timeline": {"layers": "picture"}}), self.final))
        self.assertEqual(list(got), ["Готовый ролик"])
        (at, s, length, _el, f), = got["Готовый ролик"]
        self.assertEqual((at, s, length, f), (0, 0, 14, self.final.resolve()))
        self.assertEqual(marks["Море"], 5)


@needs_ffmpeg
class InTheRun(TempDirCase):
    def run_with(self, steps, name):
        from runtime import pipelines

        src = self.tmp / "урок.mp4"
        if not src.is_file():
            make_av(src, [(a, b) for a, b, _ in LESSON], LESSON_SECONDS, size="320x180")
        out = self.tmp / "выпуски" / name
        prof = profile(steps, asr_config(self.tmp, bursts(LESSON)), gap=0.5, pad=0.12, lufs=-16)
        return pipelines.run(src, prof, out, Approver()), out

    def test_with_the_steps_the_folder_gets_the_timeline_and_the_pack_and_without_them_nothing(self):
        base = ["speech_spans", "cut_spans", "drift_ms"]
        report, out = self.run_with(base + ["timeline", "publish_pack"], "с шагами")
        names = {p.name for p in out.iterdir()}
        self.assertTrue({"урок.fcpxml", "таймлиния.md", "публикация.md", "обложки"} <= names, names)
        text = report["report"].read_text(encoding="utf-8")
        self.assertIn("урок.fcpxml", text)
        self.assertIn("публикация.md", text)
        self.assertNotIn("pictures", report["outputs"][0])
        _report, plain = self.run_with(base, "без шагов")
        self.assertFalse({"урок.fcpxml", "таймлиния.md", "публикация.md", "обложки"} & {p.name for p in plain.iterdir()})
