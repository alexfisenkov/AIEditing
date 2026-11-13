"""`overlay.py timeline`: the video with graphics as one muted picture, the sound in stems (speech, sfx, music), chapters."""
import contextlib
import io
import os
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from unittest import mock
from urllib.parse import unquote, urlparse

from _support import SKILL, TempDirCase, ffmpeg, make_av, needs_ffmpeg

KIT = SKILL / "overlay-kit"
if str(KIT / "tools") not in sys.path:
    sys.path.insert(0, str(KIT / "tools"))

import overlay  # noqa: E402
from overlaylib import timeline  # noqa: E402


def cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = overlay.main([str(a) for a in argv])
    return code, out.getvalue() + err.getvalue()


def secs(value):
    return Fraction(str(value).rstrip("s"))


@needs_ffmpeg
class KitTimeline(TempDirCase):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, {"OVERLAY_MIN_FREE_GB": "0", "AIEDITING_YUNET_MODEL": str(self.tmp / "нет.onnx")})
        env.start()
        self.addCleanup(env.stop)
        self.video = make_av(self.tmp / "база.mp4", [(0.5, 2.5)], 6.0, size="320x180", rate=30)
        words = self.tmp / "слова.txt"
        words.write_text(" 0.60 раз\n 1.20 два\n", encoding="utf-8")
        self.work = self.tmp / "работа"
        self.music = self.tmp / "подложка.wav"
        ffmpeg("-f", "lavfi", "-i", "sine=f=220:d=6", str(self.music))
        self.prepare_args = ["prepare", self.video, self.work, "--words", words, "--design",
                             SKILL / "design" / "chrome-graphite", "--no-install"]
        self.release = self.tmp / "выпуск"
        self.release.mkdir()
        make_av(self.release / "база-графика.mp4", [(0.5, 2.5)], 6.0, size="320x180", rate=30)
        (self.release / "отчёт.md").write_text("# Отчёт монтажа\n\n## Готовое\n\n- Графика наложена: база-графика.mp4\n\n"
                                               "## Главы\n\n- 0:00:00.0 Начало\n- 0:00:03.5 Суть\n\n## Синхрон\n\n- в норме\n",
                                               encoding="utf-8")
        self.asked = []

    def fake_stem(self, work, stem, out):
        """Remotion stands in: a WAV the length of the composition, one tone per stem."""
        self.asked.append(stem)
        out.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg("-f", "lavfi", "-i", "sine=f={}:d=6".format({"speech": 440, "sfx": 880, "music": 220}[stem]), str(out))

    def timeline(self, *extra):
        code, out = cli(*self.prepare_args, *extra)
        self.assertEqual(code, 0, out)
        (self.work / "node_modules" / "remotion").mkdir(parents=True)
        with mock.patch.object(timeline, "render_stem", self.fake_stem):
            return cli("timeline", self.work, self.release)

    def test_picture_and_stems_and_chapters_are_on_the_timeline(self):
        code, out = self.timeline("--music", self.music)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.asked, ["speech", "sfx", "music"])
        path = self.release / "база-графика.fcpxml"
        root = ET.parse(str(path)).getroot()
        self.assertEqual(root.get("version"), "1.10")
        files = {a.get("id"): Path(unquote(urlparse(a.find("media-rep").get("src")).path)) for a in root.iter("asset")}
        picture, = [c for c in root.find("library/event/project/sequence/spine") if c.tag == "asset-clip"]
        self.assertEqual(files[picture.get("ref")], (self.release / "база-графика.mp4").resolve())
        self.assertEqual(picture.get("srcEnable"), "video")  # the sound is in the stems, not twice
        stems = {c.get("name").split(" · ")[0]: c for c in picture.findall("asset-clip")}
        self.assertEqual(sorted(stems), ["Голос", "Звуки", "Музыка"])
        self.assertEqual(sorted(files[c.get("ref")].name for c in stems.values()), ["голос.wav", "звуки.wav", "музыка.wav"])
        self.assertTrue(all(int(c.get("lane")) < 0 for c in stems.values()))
        marks = {m.get("value"): secs(m.get("start")) for m in picture.findall("marker")}
        self.assertEqual(marks, {"Начало": 0, "Суть": Fraction(7, 2)})
        note = (self.release / "таймлиния.md").read_text(encoding="utf-8")
        self.assertIn("Файл → Импорт → Таймлиния", note)
        self.assertNotIn("Final Cut", note + path.read_text(encoding="utf-8"))

    def test_without_a_pad_there_is_no_music_stem_and_without_a_video_a_reason(self):
        code, out = self.timeline()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.asked, ["speech", "sfx"])
        (self.release / "база-графика.mp4").unlink()
        with mock.patch.object(timeline, "render_stem", self.fake_stem):
            code, out = cli("timeline", self.work, self.release)
        self.assertEqual(code, 2)
        self.assertIn("overlay.py final", out)

