"""overlay-kit: nothing private inside, `prepare` unpacks a working folder safely, the design comes as data, sounds are real."""
import contextlib
import io
import json
import os
import re
import struct
import sys
import unittest
import wave
from pathlib import Path
from unittest import mock

from _support import SKILL, TempDirCase, ffmpeg, needs_ffmpeg

KIT = SKILL / "overlay-kit"
TEMPLATE = KIT / "template"
CHROME_GRAPHITE = SKILL / "design" / "chrome-graphite"
if str(KIT / "tools") not in sys.path:
    sys.path.insert(0, str(KIT / "tools"))

import overlay  # noqa: E402
from overlaylib import design, loudness, scaffold, scanning, sheets, sounds, words  # noqa: E402
from overlaylib.common import ToolError  # noqa: E402

PRIVATE = ["fisenkov", "фисенков", "мастерск", "masterskaya", "александр", "/users/", "ии-революция"]
TEXT_SUFFIXES = {".md", ".ts", ".tsx", ".json", ".py", ".mjs", ".js", ".txt", ".html", ".svg", ".css", ".yml", ".yaml", ".sh"}
SKIP_DIRS = {"__pycache__", "node_modules"}

REFERENCE_OVERLAY = {
    "color": {
        "white": "#FFFFFF", "muted": "#C7C9CC", "faint": "#8A8D92", "graphite": "#171717", "graphiteSoft": "#202123",
        "deep": "#0E0E10", "card": "#1B1C1F", "silver": "#C7C9CC", "silverLight": "#ECEDEF", "paper": "#F4F5F6",
        "ink": "#181A1C", "line": "rgba(255,255,255,.14)", "ok": "#1F8A5B",
    },
    "chrome": "linear-gradient(180deg,#FFFFFF 0%,#E0E2E5 40%,#A9ACB1 62%,#EEF0F2 100%)",
    "bg": "linear-gradient(165deg,#202123 0%,#0E0E10 100%)",
    "glass": "linear-gradient(165deg,rgba(32,33,35,.92),rgba(14,14,16,.94))",
    "hair": "linear-gradient(90deg,transparent,rgba(199,201,204,.55),transparent)",
    "rim": "0 0 0 1px rgba(199,201,204,.2), inset 0 1px 0 rgba(255,255,255,.08)",
    "shadow": "0 40px 90px rgba(0,0,0,.55)",
    "shine": "linear-gradient(100deg,#9A9DA2 0%,#E0E2E5 30%,#FFFFFF 42%,#E0E2E5 54%,#9A9DA2 100%)",
    "radius": {"block": 26, "card": 22, "inner": 15, "pill": 999},
}


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = overlay.main([str(a) for a in argv])
    return code, out.getvalue(), err.getvalue()


def make_video(path, size="1280x720", seconds=3):
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s={}:r=30:d={}".format(size, seconds),
           "-f", "lavfi", "-i", "sine=f=440:d={}".format(seconds),
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path))


def make_wav(path, seconds=0.1):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(struct.pack("<h", 0) * int(8000 * seconds))


def kit_files():
    for path in sorted(KIT.rglob("*")):
        if path.is_file() and not (set(path.relative_to(KIT).parts) & SKIP_DIRS):
            yield path


class NothingPrivate(unittest.TestCase):
    def test_no_private_strings_in_the_kit(self):
        found = []
        for path in kit_files():
            rel = str(path.relative_to(KIT))
            hits = [p for p in PRIVATE if p in rel.lower()]
            if path.suffix.lower() in TEXT_SUFFIXES:
                text = path.read_text(encoding="utf-8", errors="replace").lower()
                hits += [p for p in PRIVATE if p in text]
            if hits:
                found.append("{}: {}".format(rel, ", ".join(sorted(set(hits)))))
        self.assertEqual(found, [], "private strings in the kit")

    def test_no_logos_and_no_unverified_sounds_or_music_ship(self):
        self.assertEqual(json.loads((TEMPLATE / "src/data/brands.json").read_text(encoding="utf-8")), {})
        shipped = sorted(p.stem for p in (TEMPLATE / "public/sfx").iterdir())
        self.assertEqual(shipped, ["pop-soft", "riser-1s", "tick", "whoosh-soft"])
        self.assertFalse((TEMPLATE / "public/music").exists())
        self.assertFalse((TEMPLATE / "public/logos").exists())

    def test_every_shipped_font_has_its_licence_text_with_a_copyright_line(self):
        fonts = TEMPLATE / "public/fonts"
        for family in ("Unbounded", "Onest", "JetBrainsMono"):
            text = (fonts / "OFL-{}.txt".format(family)).read_text(encoding="utf-8")
            self.assertTrue(text.startswith("Copyright "), family)
            self.assertIn("SIL OPEN FONT LICENSE Version 1.1", text)
        self.assertIn("The Unbounded Project Authors", (fonts / "OFL-Unbounded.txt").read_text(encoding="utf-8"))


class TemplatePins(unittest.TestCase):
    def test_packages_are_pinned_and_locked(self):
        pkg = json.loads((TEMPLATE / "package.json").read_text(encoding="utf-8"))
        for group in ("dependencies", "devDependencies"):
            for name, version in pkg[group].items():
                self.assertRegex(version, r"^\d+\.\d+\.\d+$", name)
        lock = json.loads((TEMPLATE / "package-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["packages"]["node_modules/remotion"]["version"], pkg["dependencies"]["remotion"])
        self.assertEqual(lock["packages"]["node_modules/playwright"]["version"], pkg["dependencies"]["playwright"])

    def test_sound_names_in_python_and_in_the_kit_agree(self):
        source = (TEMPLATE / "src/kit/Sound.tsx").read_text(encoding="utf-8")
        vol = re.search(r"export const VOL = \{(.*?)\} as const;", source, re.S).group(1)
        names = re.findall(r'^\s*"?([a-z0-9-]+)"?:\s*[\d.]+,', vol, re.M)
        self.assertEqual(sorted(names), sorted(sounds.NAMES))


class Design(TempDirCase):
    def setUp(self):
        super().setUp()
        (self.tmp / "work/src/data").mkdir(parents=True)
        self.work = self.tmp / "work"
        self.tokens = json.loads((CHROME_GRAPHITE / "tokens.json").read_text(encoding="utf-8"))
        self.tokens.pop("overlay")  # these tests build their own block, or none

    def folder(self, tokens, files=None):
        folder = self.tmp / "design"
        folder.mkdir(exist_ok=True)
        (folder / "tokens.json").write_text(json.dumps(tokens), encoding="utf-8")
        for name, data in (files or {}).items():
            (folder / name).parent.mkdir(parents=True, exist_ok=True)
            (folder / name).write_bytes(data)
        return folder

    def built(self):
        return json.loads((self.work / "src/data/design.json").read_text(encoding="utf-8"))

    def test_design_without_an_overlay_block_is_derived_from_the_ordinary_tokens(self):
        note = design.build(self.folder(self.tokens), self.work, None)
        data = self.built()
        self.assertIn("выведен", note)
        shipped = json.loads((TEMPLATE / "src/data/design.json").read_text(encoding="utf-8"))
        for key in ("CHROME", "BG", "GLASS", "HAIR", "RIM", "SHADOW", "R", "FONT"):
            self.assertEqual(data[key], shipped[key], key)
        for key, value in shipped["C"].items():
            if key not in ("faint", "card"):  # the only two the ordinary tokens cannot reproduce exactly
                self.assertEqual(data["C"][key], value, key)
        self.assertEqual(data["C"]["muted"], self.tokens["color"]["silver"])

    def test_the_overlay_block_wins_and_with_the_reference_values_equals_the_shipped_default(self):
        self.tokens["overlay"] = REFERENCE_OVERLAY
        note = design.build(self.folder(self.tokens), self.work, None)
        self.assertIn("overlay", note)
        shipped = json.loads((TEMPLATE / "src/data/design.json").read_text(encoding="utf-8"))
        data = self.built()
        for key in ("C", "CHROME", "BG", "GLASS", "HAIR", "FONT", "R", "RIM", "SHADOW", "families", "fonts"):
            self.assertEqual(data[key], shipped[key], key)

    def test_overlay_values_replace_derived_ones(self):
        self.tokens["overlay"] = {"color": {"ok": "#123456", "ink": "#000001"}, "chrome": "linear-gradient(0deg,#111,#222)", "radius": {"card": 8}}
        design.build(self.folder(self.tokens), self.work, "logos/logo.svg")
        data = self.built()
        self.assertEqual(data["C"]["ok"], "#123456")
        self.assertEqual(data["C"]["white"], "#FFFFFF")
        self.assertEqual(data["CHROME"], "linear-gradient(0deg,#111,#222)")
        self.assertEqual((data["R"]["card"], data["R"]["pill"]), (8, 999))
        self.assertEqual(data["logo"], "logos/logo.svg")

    def test_a_missing_value_stops_with_its_name(self):
        del self.tokens["gradient"]
        with self.assertRaises(ToolError) as caught:
            design.build(self.folder(self.tokens), self.work, None)
        self.assertIn("chrome", str(caught.exception))

    def test_a_family_from_the_template_uses_its_woff2_and_another_uses_its_file(self):
        self.tokens["font"]["text"] = {"family": "Acme Sans", "file": "fonts/Acme.ttf"}
        design.build(self.folder(self.tokens, {"fonts/Acme.ttf": b"not really a font"}), self.work, None)
        data = self.built()
        self.assertEqual(data["families"], {"display": "Unbounded", "text": "Acme Sans", "mono": "JetBrains Mono"})
        acme = [f for f in data["fonts"] if f["family"] == "Acme Sans"]
        self.assertEqual([(f["format"], f["range"]) for f in acme], [("truetype", None)])
        self.assertTrue((self.work / acme[0]["src"].replace("fonts/", "public/fonts/")).is_file())
        self.assertTrue(any(f["src"].startswith("fonts/unbounded") for f in data["fonts"]))
        self.assertTrue(data["FONT"]["text"].startswith("'Acme Sans',"))


class Sounds(TempDirCase):
    def test_the_manifest_lists_only_files_that_exist(self):
        work = self.tmp / "work"
        (work / "public/sfx").mkdir(parents=True)
        (work / "src/data").mkdir(parents=True)
        for name in ("tick.wav", "pop-soft.wav", "whoosh-soft.wav", "other.wav"):
            make_wav(work / "public/sfx" / name)
        data = sounds.write_manifest(work)
        self.assertEqual(sorted(data["files"]), ["pop-soft", "tick", "whoosh-soft"])
        for rel in data["files"].values():
            self.assertTrue((work / "public" / rel).is_file())
        self.assertIsNone(data["music"])

    def test_own_sounds_replace_by_name_and_music_is_optional(self):
        work = self.tmp / "work"
        (work / "public/sfx").mkdir(parents=True)
        (work / "src/data").mkdir(parents=True)
        make_wav(work / "public/sfx/tick.wav")
        mine = self.tmp / "mine"
        mine.mkdir()
        make_wav(mine / "ding.wav")
        make_wav(mine / "tick.wav", seconds=0.5)
        make_wav(mine / "boom.wav")
        with contextlib.redirect_stdout(io.StringIO()):
            copied, ignored = sounds.add_sfx(work, mine)
        self.assertEqual((copied, ignored), (2, 1))
        make_wav(self.tmp / "pad.wav")
        sounds.add_music(work, self.tmp / "pad.wav")
        data = sounds.write_manifest(work)
        self.assertEqual(sorted(data["files"]), ["ding", "tick"])
        self.assertEqual(data["music"], "music/pad.wav")
        with self.assertRaises(ToolError):
            sounds.add_music(work, self.tmp / "missing.wav")


class Scenes(TempDirCase):
    def test_every_segment_file_is_listed_in_the_generated_indexes(self):
        work = self.tmp / "work"
        scaffold.deploy_template(work)
        (work / "src/scenes/seg-e.tsx").write_text((work / "src/scenes/seg-d.tsx").read_text(encoding="utf-8"), encoding="utf-8")
        (work / "src/data/layouts-e.ts").write_text(
            'import { LayoutKey } from "./layout-types";\nexport const LAYOUTS_E: readonly LayoutKey[] = [];\n', encoding="utf-8")
        self.assertEqual(scaffold.write_index(work), ["a", "b", "c", "d", "e"])
        self.assertIn('import * as s_e from "./seg-e";', (work / "src/scenes/index.ts").read_text(encoding="utf-8"))
        self.assertIn("...LAYOUTS_E", (work / "src/data/all-layouts.ts").read_text(encoding="utf-8"))
        (work / "src/scenes/seg-Bad.tsx").write_text("", encoding="utf-8")
        with self.assertRaises(ToolError):
            scaffold.write_index(work)

    def test_screen_texts_keep_words_and_drop_code(self):
        scenes = self.tmp / "scenes"
        scenes.mkdir()
        (scenes / "seg-a.tsx").write_text(
            'import React from "react";\n// A comment is not text\n'
            'const P = <path d="M5 12.5l4.5 4.5L19 7" />;\n'
            'const x = <div style={{ display: "flex", fontFamily: "Onest" }}><H2>Check what is done</H2>'
            '<Pill>one place</Pill><Pill>Привет, мир</Pill></div>;\n', encoding="utf-8")
        out = self.tmp / "texts.md"
        scanning.screen_texts(scenes, out)
        text = out.read_text(encoding="utf-8")
        for wanted in ("Check what is done", "one place", "Привет, мир"):
            self.assertIn(wanted, text)
        for unwanted in ("M5 12.5", "flex", "react", "A comment"):
            self.assertNotIn(unwanted, text)

    def test_loudness_chain_removes_the_measured_delay(self):
        measured = {"input_i": -22.0, "input_tp": -10.0, "input_lra": 1.5, "input_thresh": -32.0, "target_offset": 0.1}
        self.assertTrue(loudness.audio_filter(-14, measured, 0.0428).startswith("atrim=start=0.04280,asetpts=PTS-STARTPTS,loudnorm="))
        self.assertTrue(loudness.audio_filter(-14, measured, -0.02).startswith("adelay=20|20,loudnorm="))
        self.assertTrue(loudness.audio_filter(-14, measured, 0.0).startswith("loudnorm="))

    def test_crop_and_words_are_validated(self):
        self.assertEqual(sheets.parse_crop(None), (0.0, 0.0, 1.0, 1.0))
        self.assertEqual(sheets.parse_crop("0.1,0.2,0.5,0.5"), (0.1, 0.2, 0.5, 0.5))
        for bad in ("1,2,3", "0.5,0.5,0.9,0.9", "a,b,c,d"):
            with self.assertRaises(ToolError):
                sheets.parse_crop(bad)
        good = self.tmp / "w.txt"
        good.write_text("   0.50 hello\n  1.25 world\n\n", encoding="utf-8")
        self.assertEqual(words.read_words(good), [(0.5, "hello"), (1.25, "world")])
        good.write_text("hello 0.5\n", encoding="utf-8")
        with self.assertRaises(ToolError):
            words.read_words(good)


@needs_ffmpeg
class Prepare(TempDirCase):
    def setUp(self):
        super().setUp()
        self.video = self.tmp / "talk.mp4"
        make_video(self.video)
        self.words = self.tmp / "words.txt"
        self.words.write_text("".join("{:7.2f} word{}\n".format(0.3 * i, i) for i in range(1, 9)), encoding="utf-8")
        self.work = self.tmp / "work"
        self.env = mock.patch.dict(os.environ, {"OVERLAY_MIN_FREE_GB": "0", "AIEDITING_YUNET_MODEL": str(self.tmp / "no-model.onnx")})
        self.env.start()
        self.addCleanup(self.env.stop)

    def prepare(self, **extra):
        args = ["prepare", self.video, self.work, "--words", self.words, "--design", CHROME_GRAPHITE, "--no-install"]
        for key, value in extra.items():
            args += ["--" + key, value]
        return run_cli(*args)

    def test_unpacks_a_complete_working_folder(self):
        code, out, err = self.prepare()
        self.assertEqual(code, 0, err)
        for rel in ("public/clips/source.mp4", "public/clips/speech.wav", "raw/words.txt", "src/data/design.json", "src/data/face.json",
                    "src/data/sfx.json", "src/scenes/seg-a.tsx", "src/scenes/index.ts", "package-lock.json", "tools-local/capture-render.mjs",
                    "tools-local/add-logos.mjs", "public/fonts/unbounded-latin-wght-normal.woff2"):
            self.assertTrue((self.work / rel).is_file(), rel)
        self.assertEqual((self.work / "raw/words.txt").read_text(encoding="utf-8"), self.words.read_text(encoding="utf-8"))
        duration = float(re.search(r"DURATION = ([\d.]+)", (self.work / "src/data/layouts.ts").read_text(encoding="utf-8")).group(1))
        self.assertAlmostEqual(duration, 3.0, delta=0.1)
        self.assertEqual(json.loads((self.work / "src/data/face.json").read_text(encoding="utf-8"))[0][1:], [0.5, 0.45, 0.4])
        self.assertNotIn("node_modules", [p.name for p in self.work.iterdir()])
        self.assertIn("Лицо", out)

    def test_the_working_copy_is_1080p_30fps_h264_without_sound(self):
        self.assertEqual(self.prepare()[0], 0)
        from overlaylib.media import probe
        info = probe(self.work / "public/clips/source.mp4")
        self.assertEqual((info["width"], info["height"], round(info["fps"])), (1920, 1080, 30))
        self.assertFalse(info["audio"])
        from overlaylib.media import duration_of
        self.assertAlmostEqual(duration_of(self.work / "public/clips/speech.wav"), 3.0, delta=0.1)

    def test_sounds_listed_in_the_manifest_exist(self):
        self.assertEqual(self.prepare()[0], 0)
        data = json.loads((self.work / "src/data/sfx.json").read_text(encoding="utf-8"))
        self.assertTrue(data["files"])
        for rel in data["files"].values():
            self.assertTrue((self.work / "public" / rel).is_file(), rel)
        self.assertIsNone(data["music"])

    def test_a_repeat_keeps_scenes_and_layouts(self):
        self.assertEqual(self.prepare()[0], 0)
        scene = self.work / "src/scenes/seg-a.tsx"
        layouts = self.work / "src/data/layouts-a.ts"
        scene.write_text("// my scenes\n" + scene.read_text(encoding="utf-8"), encoding="utf-8")
        layouts.write_text("// my layouts\n" + layouts.read_text(encoding="utf-8"), encoding="utf-8")
        code, out, err = self.prepare()
        self.assertEqual(code, 0, err)
        self.assertTrue(scene.read_text(encoding="utf-8").startswith("// my scenes"))
        self.assertTrue(layouts.read_text(encoding="utf-8").startswith("// my layouts"))
        self.assertIn("не трогаю", out)

    def test_refuses_a_frame_that_is_not_16_by_9(self):
        square = self.tmp / "square.mp4"
        make_video(square, size="800x800")
        code, out, err = run_cli("prepare", square, self.work, "--words", self.words, "--design", CHROME_GRAPHITE, "--no-install")
        self.assertEqual(code, 2)
        self.assertIn("16:9", err)
        self.assertFalse((self.work / "src").exists())

    def test_refuses_a_relative_folder_and_words_of_another_recording(self):
        code, _, err = run_cli("prepare", self.video, "relative/dir", "--words", self.words, "--design", CHROME_GRAPHITE, "--no-install")
        self.assertEqual((code, "абсолютным" in err), (2, True))
        late = self.tmp / "late.txt"
        late.write_text("   400.00 far\n", encoding="utf-8")
        code, _, err = run_cli("prepare", self.video, self.work, "--words", late, "--design", CHROME_GRAPHITE, "--no-install")
        self.assertEqual(code, 2)
        self.assertIn("ЭТОГО видео", err)
        self.assertFalse(self.work.exists(), "a refused run writes nothing")
        broken = json.loads((CHROME_GRAPHITE / "tokens.json").read_text(encoding="utf-8"))
        broken.pop("overlay")
        del broken["gradient"]
        folder = self.tmp / "broken-design"
        folder.mkdir()
        (folder / "tokens.json").write_text(json.dumps(broken), encoding="utf-8")
        code, _, err = run_cli("prepare", self.video, self.work, "--words", self.words, "--design", folder, "--no-install")
        self.assertEqual(code, 2)
        self.assertIn("chrome", err)
        self.assertFalse(self.work.exists())

    def test_a_repeat_keeps_a_face_track_that_was_really_built(self):
        self.assertEqual(self.prepare()[0], 0)
        face = self.work / "src/data/face.json"
        face.write_text(json.dumps([[0.0, 0.4, 0.4, 0.3], [0.5, 0.41, 0.4, 0.3]]), encoding="utf-8")
        code, out, _ = self.prepare()
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(face.read_text(encoding="utf-8"))), 2)
        self.assertIn("уже построен", out)

    def test_another_video_under_the_same_folder_replaces_the_copies(self):
        work = self.tmp / "work"
        self.assertEqual(run_cli("prepare", self.video, work, "--words", self.words, "--design", CHROME_GRAPHITE, "--no-install")[0], 0)
        first = (work / "public/clips/source.mp4").stat().st_mtime_ns
        other = self.tmp / "другое.mp4"
        make_video(other)
        ffmpeg("-i", str(other), "-vf", "negate", "-c:a", "copy", str(self.tmp / "другое-2.mp4"))
        code, out, err = run_cli("prepare", self.tmp / "другое-2.mp4", work, "--words", self.words, "--design", CHROME_GRAPHITE, "--no-install")
        self.assertEqual(code, 0, err)
        self.assertIn("другое видео", out)
        self.assertNotEqual((work / "public/clips/source.mp4").stat().st_mtime_ns, first)

    def test_refuses_too_little_free_space(self):
        with mock.patch.dict(os.environ, {"OVERLAY_MIN_FREE_GB": "99999999"}):
            code, _, err = self.prepare()
        self.assertEqual(code, 2)
        self.assertIn("ГБ", err)

    @unittest.skipUnless(sys.platform == "darwin", "iCloud folders exist on macOS")
    def test_refuses_icloud_folders_on_macos(self):
        home = self.tmp / "home"
        with mock.patch.dict(os.environ, {"HOME": str(home)}):
            for sub in ("Documents", "Desktop"):
                code, _, err = run_cli("prepare", self.video, home / sub / "overlay", "--words", self.words, "--design", CHROME_GRAPHITE, "--no-install")
                self.assertEqual(code, 2, sub)
                self.assertIn("iCloud", err)

    def test_the_design_is_written_with_and_without_a_logo(self):
        self.assertEqual(self.prepare()[0], 0)
        self.assertIsNone(json.loads((self.work / "src/data/design.json").read_text(encoding="utf-8"))["logo"])
        logo = self.tmp / "mark.svg"
        logo.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><rect width="8" height="8"/></svg>', encoding="utf-8")
        self.assertEqual(self.prepare(logo=logo)[0], 0)
        self.assertEqual(json.loads((self.work / "src/data/design.json").read_text(encoding="utf-8"))["logo"], "logos/logo.svg")
        self.assertTrue((self.work / "public/logos/logo.svg").is_file())

    def test_unprepared_folders_and_unknown_commands_are_errors(self):
        code, _, err = run_cli("frame", self.tmp / "nothing", "5")
        self.assertEqual(code, 2)
        self.assertIn("prepare", err)
        self.assertEqual(run_cli("bogus")[0], 2)
        self.assertEqual(run_cli("--help")[0], 0)


@needs_ffmpeg
class LooksAtVideo(TempDirCase):
    def test_sheets_are_replaced_and_frames_remember_their_aspect(self):
        video = self.tmp / "v.mp4"
        make_video(video, seconds=9)
        code, out, err = run_cli("sheets", video, self.tmp / "sheets", "--step", "2")
        self.assertEqual(code, 0, err)
        self.assertTrue((self.tmp / "sheets/sheet-01.jpg").is_file())
        work = self.tmp / "work"
        scaffold.deploy_template(work)
        code, out, err = run_cli("frames", video, work, "--label", "demo clip", "--crop", "0,0,0.5,0.5", "3")
        self.assertEqual(code, 0, err)
        self.assertTrue((work / "public/frames/demo-clip-3.jpg").is_file())
        self.assertAlmostEqual(json.loads((work / "src/data/frames.json").read_text(encoding="utf-8"))["demo-clip-3"], 16 / 9, places=3)
        self.assertEqual(run_cli("frames", video, work, "99")[0], 2)

    def test_sync_measures_a_known_delay(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy is not installed")
        base, late = self.tmp / "base.mp4", self.tmp / "late.mp4"
        ffmpeg("-f", "lavfi", "-i", "color=c=black:s=320x180:r=30:d=14", "-f", "lavfi",
               "-i", "anoisesrc=d=14:c=pink:r=48000:a=0.5,volume='if(lt(mod(t,2.2),1.5),1,0.05)':eval=frame",
               "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(base))
        ffmpeg("-i", str(base), "-c:v", "copy", "-af", "adelay=40:all=1", "-c:a", "aac", str(late))
        code, out, _ = run_cli("sync", base, late)
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"сдвиг \+(39|40|41)\.\d мс")
        self.assertEqual(run_cli("sync", base, base)[0], 0)

    def test_the_length_is_held_to_the_picture_when_the_recordings_sound_is_shorter(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy is not installed")
        from overlaylib import verify

        video, speech = self.tmp / "picture.mp4", self.tmp / "speech.wav"
        ffmpeg("-f", "lavfi", "-i", "color=c=black:s=320x180:r=30:d=14", "-f", "lavfi",
               "-i", "anoisesrc=d=14:c=pink:r=48000:a=0.5,volume='if(lt(mod(t,2.2),1.5),1,0.05)':eval=frame",
               "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(video))
        ffmpeg("-i", str(video), "-t", "13.7", "-vn", str(speech))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(verify.sync_report(speech, video, length=14.0)[0])
            self.assertFalse(verify.sync_report(speech, video)[0])

    def test_the_report_stops_saying_the_graphics_are_to_come(self):
        from overlaylib import final

        (self.tmp / "отчёт.md").write_text("# Отчёт\n\n## Готовое\n\n- ролик.mp4\n\n- Графика ещё не наложена: это делается\n- другое\n",
                                           encoding="utf-8")
        final.mark_report(self.tmp, "ролик - монтаж.mp4")
        final.mark_report(self.tmp, "ролик - монтаж.mp4")
        text = (self.tmp / "отчёт.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("готовый ролик с графикой"), 1)
        self.assertLess(text.index("ролик - монтаж.mp4 — готовый"), text.index("- ролик.mp4"))
        self.assertIn("- Графика наложена: ролик - монтаж.mp4", text)
        self.assertNotIn("ещё не наложена", text)
        self.assertIn("- другое", text)


if __name__ == "__main__":
    unittest.main()
