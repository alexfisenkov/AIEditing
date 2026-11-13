"""FCPXML 1.10 writer: a timeline DaVinci Resolve imports (Файл → Импорт → Таймлиния), read back with xml.etree."""
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from urllib.parse import unquote, urlparse

from _support import SKILL, TempDirCase
from runtime.media import fcpxml

sys.path.insert(0, str(SKILL / "tools"))
import fcpx_timeline  # noqa: E402  (the reader the workshop already has: an independent check of the writer)


def secs(value) -> Fraction:
    return Fraction(str(value).rstrip("s"))


def path_of(asset) -> Path:
    src = asset.find("media-rep").get("src")
    return Path(unquote(urlparse(src).path))


class Write(TempDirCase):
    def spec(self, **over):
        cam, broll, music = self.tmp / "камера 1.mp4", self.tmp / "вставки" / "море.mov", self.tmp / "трек.m4a"
        spec = {"name": "Урок про море", "fps": 25, "width": 1920, "height": 1080, "duration": 12.0,
                "video": [{"name": "Камера", "clips": [{"file": str(cam), "start": 0.0, "in": 2.0, "dur": 5.0},
                                                       {"file": str(cam), "start": 5.0, "in": 9.0, "dur": 7.0}]},
                          {"name": "Вставки", "clips": [{"file": str(broll), "start": 6.0, "in": 1.6, "dur": 4.0,
                                                         "muted": True}]}],
                "audio": [{"name": "Музыка", "role": "music",
                           "clips": [{"file": str(music), "start": 0.0, "in": 0.0, "dur": 12.0, "db": -20}]},
                          {"name": "Музыка, вариант 2", "role": "music",
                           "clips": [{"file": str(music), "start": 0.0, "in": 30.0, "dur": 12.0, "off": True}]}],
                "markers": [{"t": 0.0, "text": "Начало", "kind": "chapter"},
                            {"t": 6.0, "text": "вставка: море", "kind": "broll"}]}
        spec.update(over)
        return spec

    def written(self, spec):
        out = fcpxml.write(spec, self.tmp / "выпуск" / "урок.fcpxml")
        self.assertEqual(out, self.tmp / "выпуск" / "урок.fcpxml")
        return ET.parse(str(out)).getroot(), out

    def test_a_version_1_10_file_with_absolute_paths_of_every_file_once(self):
        root, out = self.written(self.spec())
        self.assertEqual(root.tag, "fcpxml")
        self.assertEqual(root.get("version"), "1.10")
        self.assertTrue(out.read_text(encoding="utf-8").startswith('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>'))
        assets = root.findall("resources/asset")
        self.assertEqual(sorted(path_of(a) for a in assets),
                         sorted(p.resolve() for p in [self.tmp / "камера 1.mp4", self.tmp / "вставки" / "море.mov",
                                                      self.tmp / "трек.m4a"]))
        for a in assets:
            self.assertTrue(a.find("media-rep").get("src").startswith("file:///"))
            self.assertTrue(path_of(a).is_absolute())
        audio = next(a for a in assets if path_of(a).suffix == ".m4a")
        self.assertEqual((audio.get("hasAudio"), audio.get("hasVideo", "0")), ("1", "0"))

    def test_clips_keep_their_place_in_and_length_on_named_lanes(self):
        root, _ = self.written(self.spec())
        seq = root.find("library/event/project/sequence")
        self.assertEqual(root.find("library/event/project").get("name"), "Урок про море")
        self.assertEqual(secs(seq.get("duration")), 12)
        main = [c for c in seq.find("spine") if c.tag == "asset-clip"]
        self.assertEqual([(secs(c.get("offset")), secs(c.get("start")), secs(c.get("duration"))) for c in main],
                         [(0, 2, 5), (5, 9, 7)])
        self.assertTrue(all(c.get("name").startswith("Камера") for c in main))
        connected = seq.findall("spine/asset-clip/asset-clip")
        lanes = {c.get("name").split(" · ")[0]: c for c in connected}
        self.assertEqual(set(lanes), {"Вставки", "Музыка", "Музыка, вариант 2"})
        broll = lanes["Вставки"]
        self.assertEqual(broll.get("lane"), "1")
        self.assertEqual(broll.get("srcEnable"), "video")  # an insert is shown without its sound
        # attached to the second camera clip, whose own time starts at 9 s and stands at 5 s of the timeline
        parent = next(c for c in main if broll in list(c))
        self.assertEqual((secs(parent.get("offset")), secs(parent.get("start"))), (5, 9))
        self.assertEqual(secs(broll.get("offset")), 9 + (6 - 5))  # in the parent's own time
        self.assertEqual((secs(broll.get("start")), secs(broll.get("duration"))), (Fraction(8, 5), 4))
        music, second = lanes["Музыка"], lanes["Музыка, вариант 2"]
        self.assertEqual((music.get("lane"), second.get("lane")), ("-1", "-2"))
        self.assertEqual((music.get("audioRole"), music.get("enabled", "1")), ("music", "1"))
        self.assertEqual(second.get("enabled"), "0")  # a variant is there, switched off
        self.assertEqual(music.find("adjust-volume").get("amount"), "-20dB")

    def test_markers_carry_their_text_at_their_second(self):
        root, _ = self.written(self.spec())
        found = {}
        for clip in root.iter():
            for m in clip.findall("marker"):
                at = secs(clip.get("offset", "0s")) + secs(m.get("start")) - secs(clip.get("start", "0s"))
                found[m.get("value")] = at
                self.assertEqual(secs(m.get("duration")), Fraction(1, 25))
        self.assertEqual(found, {"Начало": 0, "вставка: море": 6})

    def test_the_reader_of_the_workshop_reads_the_kept_spans_back(self):
        root, out = self.written(self.spec(video=self.spec()["video"][:1], audio=[], markers=[]))
        self.assertEqual(fcpx_timeline.read(out)["kept"], [(2.0, 7.0), (9.0, 16.0)])

    def test_a_long_run_at_29_97_lands_on_frames_with_no_drift(self):
        cam = str(self.tmp / "камера.mp4")
        clips = [{"file": cam, "start": k / 3.0, "in": 100 + k / 3.0, "dur": 1 / 3.0} for k in range(900)]
        root, _ = self.written(self.spec(fps=29.97, duration=300.0, video=[{"name": "Камера", "clips": clips}],
                                         audio=[], markers=[]))
        frame = Fraction(1001, 30000)
        self.assertEqual(root.find("resources/format").get("frameDuration"), "1001/30000s")
        main = [c for c in root.find("library/event/project/sequence/spine") if c.tag == "asset-clip"]
        self.assertEqual(len(main), 900)
        for k, c in enumerate(main):
            for name in ("offset", "start", "duration"):
                self.assertEqual(secs(c.get(name)) % frame, 0, (k, name))  # every time on a frame of the sequence
            self.assertEqual(secs(c.get("offset")), round(Fraction(k, 3) / frame) * frame)
        end = secs(main[-1].get("offset")) + secs(main[-1].get("duration"))
        self.assertEqual(end, round(Fraction(300) / frame) * frame)  # 8991 frames, not 900 roundings off
        self.assertTrue(all(secs(a.get("offset")) + secs(a.get("duration")) == secs(b.get("offset"))
                            for a, b in zip(main, main[1:])), "clips touch: no gap and no overlap")

    def test_a_picture_is_a_still_and_a_hole_in_the_main_lane_is_a_gap(self):
        png = str(self.tmp / "плашки" / "глава.png")
        spec = self.spec(video=[{"name": "Камера", "clips": [{"file": str(self.tmp / "к.mp4"), "start": 2.0, "in": 0.0, "dur": 10.0}]},
                                {"name": "Плашки", "clips": [{"file": png, "start": 3.0, "in": 0.0, "dur": 3.0}]}],
                         audio=[])
        root, _ = self.written(spec)
        spine = list(root.find("library/event/project/sequence/spine"))
        self.assertEqual([c.tag for c in spine], ["gap", "asset-clip"])
        self.assertEqual((secs(spine[0].get("offset")), secs(spine[0].get("duration"))), (0, 2))
        still = root.find(".//video")
        self.assertEqual(path_of(next(a for a in root.findall("resources/asset") if a.get("id") == still.get("ref"))),
                         Path(png).resolve())
        self.assertEqual((still.get("lane"), secs(still.get("duration"))), ("1", 3))

    def test_a_spec_without_clips_or_with_a_wrong_rate_is_refused(self):
        with self.assertRaises(ValueError):
            fcpxml.write(self.spec(fps=0), self.tmp / "x.fcpxml")
        with self.assertRaises(ValueError):
            fcpxml.write(self.spec(video=[], audio=[]), self.tmp / "x.fcpxml")
        self.assertFalse((self.tmp / "x.fcpxml").exists())
