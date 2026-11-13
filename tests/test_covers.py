"""Covers: six 3840×2160 JPG in the format's design, the lower right corner free, a sheet and 320 px previews; --more adds."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import unittest

from _support import SKILL, TempDirCase, ffmpeg, needs_ffmpeg

HAVE_PIL = importlib.util.find_spec("PIL") is not None
needs_pil = unittest.skipUnless(HAVE_PIL, "Pillow не установлен: обложки рисуются только с ним")
GREY = (90, 110, 130)


def frames(folder, n=4):
    from PIL import Image

    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for k in range(n):
        size = (640, 480) if k == 1 else (1280, 720)  # a 4:3 frame is cropped to 16:9, not squeezed
        path = folder / "кадр-{:02d}.jpg".format(k + 1)
        Image.new("RGB", size, GREY).save(str(path), quality=95)
        out.append(path)
    return out


def close(a, b, tol=12):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


@needs_pil
class Render(TempDirCase):
    def design(self, **colors):
        from runtime.render import default_design, load_design

        d = dict(load_design(default_design()))
        d["color"] = dict(d["color"], **colors)
        return d

    def test_six_covers_of_the_right_size_with_previews_and_a_sheet(self):
        from PIL import Image
        from runtime.media import covers

        out = self.tmp / "выпуск" / "обложки"
        made = covers.render(frames(self.tmp / "кадры"), "Три простых слова", self.design(), out)
        self.assertEqual([p.name for p in made], ["обложка-{:02d}.jpg".format(k) for k in range(1, 7)])
        for p in made:
            with Image.open(str(p)) as im:
                self.assertEqual((im.format, im.size), ("JPEG", (3840, 2160)))
            self.assertLess(p.stat().st_size, 50 * 1024 * 1024)
            with Image.open(str(out / "превью" / p.name)) as small:
                self.assertEqual(small.size, (320, 180))
        sheet = covers.sheet(made, out / "лист.jpg")
        with Image.open(str(sheet)) as im:
            self.assertGreaterEqual(im.size[0], 3 * 320)

    def test_the_lower_right_corner_stays_the_frame_and_the_words_are_in_the_design_colour(self):
        from PIL import Image
        from runtime.media import covers

        made = covers.render(frames(self.tmp / "кадры"), "Три простых слова", self.design(white="#FFEE00"),
                             self.tmp / "обложки")
        for p in made:
            with Image.open(str(p)) as im:
                im = im.convert("RGB")
                corner = im.crop((int(3840 * 0.7), int(2160 * 0.75), 3840, 2160)).resize((40, 20))
                self.assertTrue(all(close(px, GREY) for px in corner.getdata()), p.name)
                yellow = [px for px in im.resize((384, 216)).getdata() if px[0] > 200 and px[1] > 190 and px[2] < 90]
                self.assertGreater(len(yellow), 30, "{}: the words are drawn in the design's text colour".format(p.name))

    def test_more_adds_six_and_overwrites_nothing(self):
        from runtime.media import covers

        out, shots = self.tmp / "обложки", frames(self.tmp / "кадры", n=12)
        first = covers.render(shots, "Слово", self.design(), out)
        before = {p.name: p.read_bytes() for p in first}
        self.assertEqual(covers.next_number(out), 7)
        more = covers.render(shots, "Другое слово", self.design(), out, first=covers.next_number(out))
        self.assertEqual([p.name for p in more], ["обложка-{:02d}.jpg".format(k) for k in range(7, 13)])
        self.assertEqual({p.name: p.read_bytes() for p in first}, before)

    def test_no_frames_is_a_reason_not_a_crash(self):
        from runtime.media import covers

        with self.assertRaises(ValueError):
            covers.render([], "Слово", self.design(), self.tmp / "обложки")
        with self.assertRaises(ValueError):
            covers.render(frames(self.tmp / "кадры"), "   ", self.design(), self.tmp / "обложки")


@needs_pil
class Command(TempDirCase):
    def test_run_py_covers_makes_six_then_six_more(self):
        profile = {"format": "ютуб", "skill_name": "монтаж-ютуб", "language": "ru",
                   "asr": {"provider": "command", "language": "ru", "model": None, "base_url": None,
                           "api_key_env": None, "command": ["нет"]},
                   "steps": ["speech_spans", "cut_spans", "publish_pack"], "params": {}, "approval": "plan",
                   "design": "design/", "taste": [], "output_dir": "выпуски"}
        folder = self.tmp / "work" / "монтаж-ютуб"
        folder.mkdir(parents=True)
        (folder / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        example = SKILL / "design" / "chrome-graphite"  # the design stage leaves the format a design of its own
        shutil.copytree(str(example), str(folder / "design"), ignore=shutil.ignore_patterns("animations"))
        built = subprocess.run([sys.executable, str(SKILL / "tools" / "ae.py"), "build-skill", str(folder / "profile.json"),
                                str(self.tmp / "out")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        run_py = self.tmp / "out" / "монтаж-ютуб" / "tools" / "run.py"
        issue = self.tmp / "выпуски" / "2026-11-13-проба"
        frames(issue / "обложки" / "кадры")
        env = dict(os.environ, AIEDITING_IN_VENV="1")

        def covers(*extra):
            return subprocess.run([sys.executable, str(run_py), "covers", str(issue), "--text", "Как это работает", *extra],
                                  capture_output=True, text=True, encoding="utf-8", env=env)

        done = covers()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(list((issue / "обложки").glob("обложка-*.jpg"))), 6)
        self.assertTrue((issue / "обложки" / "лист.jpg").is_file())
        self.assertIn("--more", done.stdout)  # «сделать ещё?»
        done = covers("--more")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(list((issue / "обложки").glob("обложка-*.jpg"))), 12)
        empty = subprocess.run([sys.executable, str(run_py), "covers", str(self.tmp / "нет"), "--text", "Слово"],
                               capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(empty.returncode, 2, empty.stdout + empty.stderr)

    @needs_ffmpeg
    def test_a_video_without_pauses_still_gets_six_covers_and_a_sheet(self):
        from runtime.pipelines import publish
        from test_publish import Ctx

        profile = {"format": "ютуб", "skill_name": "монтаж-ютуб", "language": "ru",
                   "asr": {"provider": "command", "language": "ru", "model": None, "base_url": None,
                           "api_key_env": None, "command": ["нет"]},
                   "steps": ["speech_spans", "cut_spans", "publish_pack"], "params": {}, "approval": "plan",
                   "design": "design/", "taste": [], "output_dir": "выпуски"}
        folder = self.tmp / "work" / "монтаж-ютуб"
        folder.mkdir(parents=True)
        (folder / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        built = subprocess.run([sys.executable, str(SKILL / "tools" / "ae.py"), "build-skill", str(folder / "profile.json"),
                                str(self.tmp / "out")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        run_py = self.tmp / "out" / "монтаж-ютуб" / "tools" / "run.py"
        words = [{"text": "слово", "start": round(k * 0.32, 2), "end": round(k * 0.32 + 0.3, 2)} for k in range(93)]
        for name, pack in (("с пакетом", True), ("только ролик", False)):
            issue = self.tmp / "выпуски" / name
            issue.mkdir(parents=True)
            video = issue / "ролик.mp4"
            ffmpeg("-f", "lavfi", "-i", "testsrc=s=320x180:r=25:d=30", "-c:v", "libx264", "-preset", "ultrafast",
                   "-pix_fmt", "yuv420p", str(video))
            if pack:  # speech from the first second to the last: the cut left no pause for a frame
                publish.write_pack(Ctx(issue, words, [], [(0.0, 30.0)]), video)
            done = subprocess.run([sys.executable, str(run_py), "covers", str(issue), "--text", "Как это работает"],
                                  capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, AIEDITING_IN_VENV="1"))
            self.assertEqual(done.returncode, 0, name + ": " + done.stdout + done.stderr)
            self.assertEqual(len(list((issue / "обложки").glob("обложка-*.jpg"))), 6, name)
            self.assertTrue((issue / "обложки" / "лист.jpg").is_file(), name)

    def test_a_format_without_a_design_of_its_own_still_makes_six_covers(self):
        profile = {"format": "влог", "skill_name": "монтаж-влог", "language": "ru",
                   "asr": {"provider": "command", "language": "ru", "model": None, "base_url": None,
                           "api_key_env": None, "command": ["нет"]},
                   "steps": ["speech_spans", "cut_spans", "publish_pack"], "params": {}, "approval": "plan",
                   "design": "design/", "taste": [], "output_dir": "выпуски"}
        folder = self.tmp / "work" / "монтаж-влог"
        folder.mkdir(parents=True)  # no design/ at all: the design stage was never asked for
        (folder / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        built = subprocess.run([sys.executable, str(SKILL / "tools" / "ae.py"), "build-skill", str(folder / "profile.json"),
                                str(self.tmp / "out")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        issue = self.tmp / "выпуски" / "2026-11-13-влог"
        frames(issue / "обложки" / "кадры")
        done = subprocess.run([sys.executable, str(self.tmp / "out" / "монтаж-влог" / "tools" / "run.py"), "covers", str(issue),
                               "--text", "Как это работает"], capture_output=True, text=True, encoding="utf-8",
                              env=dict(os.environ, AIEDITING_IN_VENV="1"))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(list((issue / "обложки").glob("обложка-*.jpg"))), 6)
        self.assertTrue((issue / "обложки" / "лист.jpg").is_file())
