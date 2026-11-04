"""overlay-kit, the vertical cut: what can be checked without a render."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import unicodedata
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parent.parent / "skills" / "aiediting" / "overlay-kit"
sys.path.insert(0, str(KIT / "tools"))

import overlay  # noqa: E402
from overlaylib import design, vcheck, vaudio, vfinal, vinit, vmap, vmeasure, vsheets, vsound, vspans  # noqa: E402
from overlaylib.common import ToolError  # noqa: E402

VERTICAL = KIT / "template" / "src" / "vertical"
NEW_FILES = [*sorted(VERTICAL.glob("*")), KIT / "examples" / "vertical" / "c1.tsx", KIT / "tools" / "vertical-frames.mjs", KIT / "vertical.md",
             *sorted((KIT / "tools" / "overlaylib").glob("v*.py"))]
HAS_NUMPY = True
try:
    import numpy as np
except ImportError:  # pragma: no cover
    HAS_NUMPY = False


def sample() -> dict:
    return json.loads((VERTICAL / "spans.json").read_text(encoding="utf-8"))


class SpansTest(unittest.TestCase):
    def test_sample_is_valid_and_has_the_contract(self):
        data = vspans.load(VERTICAL / "spans.json")
        for key in ("rate", "cta_lead", "cta_tail", "cta", "safe", "spans", "names"):
            self.assertIn(key, data)
        self.assertEqual(set(data["cta"]), {"lead", "before", "word", "after"})

    def test_lengths(self):
        data = sample()
        self.assertAlmostEqual(vspans.speech_seconds(data, "c1"), 10.0)
        self.assertEqual(vspans.clip_frames(data, "c1"), 300 + 120)
        self.assertAlmostEqual(vspans.clip_seconds(data, "c1"), 14.0)
        self.assertAlmostEqual(vspans.cta_start(data, "c1"), 8.0)
        self.assertAlmostEqual(vspans.cta_needed(data), 6.0 - vspans.APPEAR)

    def test_two_spans_and_rounding(self):
        data = sample()
        data["spans"]["c1"] = [[0, 1.0], [5.0, 6.5]]
        self.assertAlmostEqual(vspans.speech_seconds(data, "c1"), 2.5 / 1.2)
        self.assertEqual(vspans.js_round(2.5), 3)
        self.assertEqual(vspans.js_round(62.5), 63)

    def test_cta_start_never_negative(self):
        data = sample()
        data["spans"]["c1"] = [[0, 1.0]]
        self.assertEqual(vspans.cta_start(data, "c1"), 0.0)

    def test_bad_data_is_refused_with_a_reason(self):
        cases = [("rate", 9), ("cta_tail", 0.1), ("safe", "nowhere"), ("cta", {"lead": "", "before": "", "word": "", "after": ""}),
                 ("spans", {"x1": [[0, 1]]}), ("spans", {"c1": [[2, 1]]}), ("spans", {"c1": []}), ("names", {"c1": "a/b"}), ("names", {"c2": "x"})]
        for key, value in cases:
            data = sample()
            data[key] = value
            with self.assertRaises(ToolError, msg=key):
                vspans.check(data)

    def test_span_past_the_source_is_refused(self):
        with self.assertRaises(ToolError):
            vspans.check_against_source(sample(), 5.0)
        vspans.check_against_source(sample(), 12.0)

    def test_safe_zone_matches_the_typescript(self):
        text = (VERTICAL / "safe.ts").read_text(encoding="utf-8")
        found = re.search(r"reels: \{ x0: (\d+), x1: (\d+), y0: (\d+), y1: (\d+) \}", text)
        x0, x1, y0, y1 = map(int, found.groups())
        self.assertEqual(vspans.SAFE_ZONES["reels"], (x0, y0, x1, y1))
        self.assertEqual((x0, x1, y0, y1), (70, 940, 270, 1240))


class SheetLabelTest(unittest.TestCase):
    def test_second_comes_from_the_frame_number(self):
        self.assertEqual(vsheets.frame_of("f-00150.jpeg"), 150)
        with self.assertRaises(ToolError):
            vsheets.frame_of("element-3.jpeg")

    def test_every_half_second_with_the_real_second(self):
        frames = list(range(0, 90, 5))  # a step of 1/6 s
        picked = vsheets.pick(frames, 30, 0.5)
        self.assertEqual([vsheets.label(t) for t, _ in picked], ["0.0 s", "0.5 s", "1.0 s", "1.5 s", "2.0 s", "2.5 s"])
        self.assertEqual([f for _, f in picked], [0, 15, 30, 45, 60, 75])

    def test_files_that_start_late_are_not_counted_from_zero(self):
        picked = vsheets.pick(list(range(300, 330, 5)), 30, 0.5)
        self.assertEqual(vsheets.label(picked[0][0]), "10.0 s")

    def test_order_of_the_list_does_not_matter(self):
        frames = [45, 0, 15, 30]
        self.assertEqual([f for _, f in vsheets.pick(frames, 30, 0.5)], [0, 15, 30, 45])


@unittest.skipUnless(shutil.which("node"), "node is missing")
class GeometryTest(unittest.TestCase):
    def run_js(self, expr: str) -> str:
        code = "import('{}').then(m => console.log(JSON.stringify({})))".format((VERTICAL / "geometry.ts").as_uri(), expr)
        done = subprocess.run(["node", "--no-warnings", "-e", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if done.returncode != 0:
            self.skipTest("this node cannot run TypeScript: " + done.stderr[-120:])
        return done.stdout.strip()

    def test_gap_under_twelve_pixels_is_touching(self):
        a = "{left:0,right:100,top:0,bottom:100}"
        self.assertEqual(self.run_js("m.isTight({},{{left:111,right:200,top:0,bottom:100}})".format(a)), "true")
        self.assertEqual(self.run_js("m.isTight({},{{left:113,right:200,top:0,bottom:100}})".format(a)), "false")
        self.assertEqual(self.run_js("m.distance({},{{left:50,right:200,top:50,bottom:200}})".format(a)), "0")

    def test_crossing_area(self):
        a = "{left:0,right:100,top:0,bottom:100}"
        self.assertEqual(self.run_js("m.crossing({},{{left:50,right:150,top:50,bottom:150}})".format(a)), "2500")
        self.assertEqual(self.run_js("m.crossing({},{{left:100,right:150,top:0,bottom:100}})".format(a)), "0")


def work_folder(root: Path) -> Path:
    work = root / "work"
    for sub in ("src/kit", "src/data", "src/scenes", "public/clips"):
        (work / sub).mkdir(parents=True)
    (work / "src" / "Root.tsx").write_text("//", encoding="utf-8")
    (work / "public" / "clips" / "source.mp4").write_bytes(b"x")
    (work / "src" / "data" / "face.json").write_text("[[0,0.5,0.45,0.4]]", encoding="utf-8")
    (work / "src" / "kit" / "time.ts").write_text(
        "export const toOld = (n: number) => n;\nexport const useT = () => toOld(useCurrentFrame() / FPS);\n", encoding="utf-8")
    (work / "src" / "kit" / "tokens.ts").write_text('import design from "../data/design.json";\nexport const C = design.C;\n', encoding="utf-8")
    return work


class InitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vtest-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.work = work_folder(self.tmp)
        self.vertical = self.work / "src" / "vertical"

    def init(self, **kw):
        ns = argparse.Namespace(work=str(self.work), spans=None, renew=False)
        for k, v in kw.items():
            setattr(ns, k, v)
        return vinit.run_init(ns)

    def test_first_run_puts_the_set_and_patches_an_old_kit(self):
        self.assertEqual(self.init(), 0)
        for name in [*vinit.SET_FILES, "spans.json", "c1.tsx", "index-clips.ts"]:
            self.assertTrue((self.vertical / name).is_file(), name)
        self.assertIn("setFrameMap", (self.work / "src" / "kit" / "time.ts").read_text(encoding="utf-8"))
        self.assertIn("export const MARK", (self.work / "src" / "kit" / "tokens.ts").read_text(encoding="utf-8"))
        self.assertIn('import { c1 } from "./c1";', (self.vertical / "index-clips.ts").read_text(encoding="utf-8"))
        self.assertTrue((self.work / "tools-local" / "vertical-frames.mjs").is_file())

    def test_without_renew_nothing_is_overwritten(self):
        self.init()
        mine = json.dumps({**sample(), "rate": 1.5})
        for name in ("VKit.tsx", "spans.json", "c1.tsx"):
            (self.vertical / name).write_text(mine if name == "spans.json" else "MINE " + name, encoding="utf-8")
        self.init()
        for name in ("VKit.tsx", "spans.json", "c1.tsx"):
            self.assertEqual((self.vertical / name).read_text(encoding="utf-8"), mine if name == "spans.json" else "MINE " + name)

    def test_renew_touches_only_the_set_never_scenes_or_data(self):
        self.init()
        mine = json.dumps({**sample(), "rate": 1.5})
        for name in ("VKit.tsx", "spans.json", "c1.tsx", "c2.tsx"):
            (self.vertical / name).write_text(mine if name == "spans.json" else "MINE " + name, encoding="utf-8")
        self.init(renew=True)
        self.assertNotEqual((self.vertical / "VKit.tsx").read_text(encoding="utf-8"), "MINE VKit.tsx")
        for name in ("spans.json", "c1.tsx", "c2.tsx"):
            self.assertEqual((self.vertical / name).read_text(encoding="utf-8"), mine if name == "spans.json" else "MINE " + name)

    def test_own_spans_need_renew_when_there_are_some(self):
        self.init()
        own = self.tmp / "own.json"
        data = sample()
        data["rate"] = 1.1
        own.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ToolError):
            self.init(spans=str(own))
        self.init(spans=str(own), renew=True)
        self.assertEqual(json.loads((self.vertical / "spans.json").read_text(encoding="utf-8"))["rate"], 1.1)

    def test_a_broken_own_spans_stops_before_any_write(self):
        own = self.tmp / "bad.json"
        own.write_text("{}", encoding="utf-8")
        with self.assertRaises(ToolError):
            self.init(spans=str(own))
        self.assertFalse(self.vertical.exists())

    def test_folder_without_prepare_is_refused(self):
        (self.work / "public" / "clips" / "source.mp4").unlink()
        with self.assertRaises(ToolError):
            self.init()

    def test_clip_index_lists_scenes_in_number_order(self):
        self.vertical.mkdir(parents=True)
        for n in ("c10", "c2", "c1"):
            (self.vertical / (n + ".tsx")).write_text("", encoding="utf-8")
        self.assertEqual(vinit.write_clips_index(self.work), ["c1", "c2", "c10"])


@unittest.skipUnless(HAS_NUMPY, "numpy is missing")
class HumTest(unittest.TestCase):
    SR = vaudio.SR

    def speech(self, seconds=14.0, floor=0.0005, hum=0.0):
        t = np.arange(int(seconds * self.SR)) / self.SR
        gate = (np.sin(2 * np.pi * 0.8 * t) > -0.35).astype(float)  # words with pauses between them
        voice = 0.25 * gate * np.sin(2 * np.pi * 180 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 3.1 * t))
        rng = np.random.default_rng(1)
        x = voice + rng.normal(0, floor, len(t))
        for hz in (110, 160, 170):
            x = x + hum * np.sin(2 * np.pi * hz * t)
        return x.astype(np.float32)

    def test_clean_speech_passes(self):
        report = vaudio.hum_report(self.speech(), 13.0)
        self.assertEqual(report["problems"], [], report)
        self.assertGreater(report["gap_db"], 30)

    def test_a_pad_is_named_by_its_tone(self):
        report = vaudio.hum_report(self.speech(hum=0.004), 13.0)
        self.assertTrue(any("гул" in p for p in report["problems"]), report)
        self.assertTrue(100 <= report["tone_hz"] <= 180, report)

    def test_a_loud_floor_is_named_by_the_gap(self):
        report = vaudio.hum_report(self.speech(floor=0.04), 13.0)
        self.assertLess(report["gap_db"], vaudio.MIN_GAP_DB)
        self.assertTrue(any("ниже речи" in p for p in report["problems"]), report)

    def test_silence_in_the_tail(self):
        x = np.concatenate([self.speech(10.0), np.zeros(4 * self.SR, dtype=np.float32)])
        self.assertLess(vaudio.tail_peak_db(x, 10.1), -100)
        self.assertGreater(vaudio.tail_peak_db(self.speech(14.0), 10.1), -60)


@unittest.skipUnless(HAS_NUMPY and shutil.which("ffmpeg"), "numpy or ffmpeg is missing")
class CallSecondsTest(unittest.TestCase):
    def test_flat_curtain_at_the_end_is_counted(self):
        tmp = Path(tempfile.mkdtemp(prefix="vcta-"))
        self.addCleanup(shutil.rmtree, str(tmp), True)
        busy, flat = tmp / "busy.mp4", tmp / "flat.mp4"
        base = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i"]
        subprocess.run(base + ["testsrc2=size=1080x1920:rate=30:duration=3", "-pix_fmt", "yuv420p", str(busy)], check=True)
        subprocess.run(base + ["color=c=0x0E0E10:size=1080x1920:rate=30:duration=2.5", "-pix_fmt", "yuv420p", str(flat)], check=True)
        whole = tmp / "whole.mp4"
        (tmp / "list.txt").write_text("file 'busy.mp4'\nfile 'flat.mp4'\n", encoding="utf-8")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-i", str(tmp / "list.txt"), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(whole)], check=True)
        self.assertAlmostEqual(vmeasure.call_seconds(whole), 2.5, delta=0.2)
        self.assertAlmostEqual(vmeasure.call_seconds(busy), 0.0, delta=0.1)


class SoundGraphTest(unittest.TestCase):
    def test_only_speech_and_one_click(self):
        parts = vsound.graph([[0.0, 5.0], [8.0, 9.0]], 1.2, 10.0, 4.0)
        text = ";".join(parts)
        self.assertIn("atempo=1.2000", text)
        self.assertEqual(text.count("[1:a]"), 1)
        self.assertIn("adelay=4000", text)
        self.assertNotIn("[2:a]", text)  # no pad
        self.assertIn("afade=t=out", text)
        self.assertTrue(parts[-1].endswith("[mix]"))

    def test_without_a_click_the_graph_has_one_input(self):
        text = ";".join(vsound.graph([[0.0, 5.0]], 1.0, 8.0, None))
        self.assertNotIn("[1:a]", text)


class DesignMarkTest(unittest.TestCase):
    def test_mark_from_tokens_or_a_neutral_ring(self):
        self.assertEqual(design.mark_of({"overlay": {"mark": "0 0 0 2px #123456"}}), "0 0 0 2px #123456")
        self.assertEqual(design.mark_of({}), design.MARK)
        self.assertEqual(design.mark_of({"overlay": {"mark": "  "}}), design.MARK)
        self.assertNotIn("FF4A00", design.MARK.upper())


class NoCallTest(unittest.TestCase):
    def data(self, **over):
        d = sample()
        d.pop("cta_lead"); d.pop("cta_tail"); d["cta"] = None
        d.update(over)
        return d

    def test_a_clip_without_a_call(self):
        for cta in (None, {}, {"lead": "", "before": " ", "word": "", "after": ""}):
            d = self.data(cta=cta)
            vspans.check(d)
            self.assertFalse(vspans.has_cta(d))
            self.assertEqual(vspans.clip_frames(d, "c1"), 300)
            self.assertIsNone(vspans.cta_start(d, "c1"))
            self.assertEqual(vspans.cta_needed(d), 0.0)

    def test_lead_and_tail_without_words_are_refused(self):
        with self.assertRaises(ToolError):
            vspans.check(self.data(cta_tail=4.0))
        with self.assertRaises(ToolError):
            vspans.check(self.data(cta_lead=2.0))
        vspans.check(self.data(cta_lead=0, cta_tail=0))

    def test_no_click_without_a_call(self):
        self.assertNotIn("[1:a]", ";".join(vsound.graph([[0.0, 5.0]], 1.2, 4.0, None)))

    def test_the_check_skips_the_call_and_the_tail(self):
        d = self.data()
        with self.patched(d, tail=-90.0) as lines:
            self.assertTrue(lines[0])
            self.assertFalse(any("призыв" in t and t.startswith(("есть", "НЕТ")) for t in lines[1]))
            self.assertTrue(any("призыва в этом ролике нет" in t for t in lines[1]))

    def patched(self, data, lufs=-14.0, peak=-2.0, tail=-90.0, hum=None, stood=6.0, target=-14.0, accepted=None):
        info = {"width": 1080, "height": 1920, "fps": 30.0, "video": vspans.clip_seconds(data, "c1"), "audio": vspans.clip_seconds(data, "c1"), "total": 0}
        report = hum or {"problems": [], "gap_db": 30.0, "tone_hz": None, "tone_db": None}
        patches = [mock.patch.object(vmeasure, "probe", return_value=info), mock.patch.object(vmeasure, "loudness", return_value=(lufs, peak)),
                   mock.patch.object(vaudio, "decode", return_value=[0.0]), mock.patch.object(vaudio, "tail_peak_db", return_value=tail),
                   mock.patch.object(vaudio, "hum_report", return_value=report), mock.patch.object(vmeasure, "call_seconds", return_value=stood)]

        @contextlib.contextmanager
        def ctx():
            with contextlib.ExitStack() as stack:
                for p in patches:
                    stack.enter_context(p)
                yield vmeasure.check_clip(Path("x.mp4"), data, "c1", target, accepted)
        return ctx()


class CheckClipTest(NoCallTest):
    def test_the_target_loudness_is_the_given_one(self):
        d = sample()
        with self.patched(d, lufs=-16.0, target=-16.0) as (ok, lines):
            self.assertTrue(ok, lines)
            self.assertTrue(any("-16 LUFS" in t for t in lines))
        with self.patched(d, lufs=-14.0, target=-16.0) as (ok, lines):
            self.assertFalse(ok)
            self.assertTrue(any(t.startswith("НЕТ") and "-16 LUFS" in t for t in lines))

    def test_peak_above_minus_one_fails(self):
        with self.patched(sample(), peak=-0.5) as (ok, _):
            self.assertFalse(ok)
        with self.patched(sample(), peak=-1.0) as (ok, _):
            self.assertTrue(ok)

    def test_hum_stops_the_file_unless_accepted_with_a_reason(self):
        hum = {"problems": ["в тихих местах стоит тон 160 Гц"], "gap_db": 12.0, "tone_hz": 160.0, "tone_db": 15.0}
        with self.patched(sample(), hum=hum) as (ok, lines):
            self.assertFalse(ok)
        with self.patched(sample(), hum=hum, accepted="сплошная речь, прослушал") as (ok, lines):
            self.assertTrue(ok, lines)
            warning = [t for t in lines if t.startswith("ПРЕДУПРЕЖДЕНИЕ")]
            self.assertEqual(len(warning), 1)
            self.assertIn("сплошная речь, прослушал", warning[0])

    def test_a_short_call_fails(self):
        with self.patched(sample(), stood=2.0) as (ok, _):
            self.assertFalse(ok)


@unittest.skipUnless(HAS_NUMPY and shutil.which("ffmpeg"), "numpy or ffmpeg is missing")
class CallBandTest(unittest.TestCase):
    def test_a_light_shadow_below_and_a_light_curtain_do_not_hide_the_call(self):
        tmp = Path(tempfile.mkdtemp(prefix="vband-"))
        self.addCleanup(shutil.rmtree, str(tmp), True)
        base = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i"]
        subprocess.run(base + ["testsrc2=size=1080x1920:rate=30:duration=3", "-pix_fmt", "yuv420p", str(tmp / "busy.mp4")], check=True)
        # a curtain of the design's own colour (not near #0E0E10), a lighter card with its shadow reaching the side columns
        curtain = "color=c=0x2A2A32:size=1080x1920:rate=30:duration=2.5,drawbox=x=0:y=380:w=1080:h=900:color=0x4A4A56:t=fill,drawbox=x=70:y=500:w=940:h=500:color=0x1B1C1F:t=fill"
        subprocess.run(base + [curtain, "-pix_fmt", "yuv420p", str(tmp / "flat.mp4")], check=True)
        (tmp / "list.txt").write_text("file 'busy.mp4'\nfile 'flat.mp4'\n", encoding="utf-8")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-i", str(tmp / "list.txt"), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(tmp / "whole.mp4")], check=True)
        self.assertAlmostEqual(vmeasure.call_seconds(tmp / "whole.mp4"), 2.5, delta=0.2)


class NamesTest(unittest.TestCase):
    def test_names_equal_after_case_and_form_are_refused(self):
        d = sample()
        d["spans"]["c2"] = [[0, 1.0]]
        d["names"] = {"c1": "Clip", "c2": "clip"}
        with self.assertRaises(ToolError):
            vspans.check(d)
        d["names"] = {"c1": unicodedata.normalize("NFC", "Caf\u00e9"), "c2": unicodedata.normalize("NFD", "Caf\u00e9")}
        with self.assertRaises(ToolError):
            vspans.check(d)
        d["names"] = {"c1": "One", "c2": "Two"}
        vspans.check(d)

    def test_a_name_equal_to_the_default_name_of_another_clip_is_refused(self):
        d = sample()
        d["spans"]["c2"] = [[0, 1.0]]
        d["names"] = {"c2": "C1"}
        with self.assertRaises(ToolError):
            vspans.check(d)


class TimeMapTest(unittest.TestCase):
    ROWS = [[0, 10, 0, 10, 0], [10, 20, 15, 25, 0]]

    def test_to_old_and_to_new(self):
        self.assertEqual(vmap.to_old(self.ROWS, 5), 5)
        self.assertEqual(vmap.to_old(self.ROWS, 12), 17)
        self.assertEqual(vmap.to_old(self.ROWS, 99), 25)
        self.assertEqual(vmap.to_new(self.ROWS, 17), 12)
        self.assertEqual(vmap.to_new(self.ROWS, 12), 10)  # cut out: the start of the next piece
        self.assertEqual(vmap.to_old([], 7.5), 7.5)

    def test_clip_second(self):
        d = sample()
        d["spans"]["c1"] = [[2.0, 4.0], [10.0, 12.0]]
        self.assertAlmostEqual(vmap.clip_second(d, "c1", 3.0), 1.0 / 1.2)
        self.assertAlmostEqual(vmap.clip_second(d, "c1", 11.0), 3.0 / 1.2)
        self.assertIsNone(vmap.clip_second(d, "c1", 6.0))

    def test_words_in_three_kinds_of_seconds_and_the_warning(self):
        tmp = Path(tempfile.mkdtemp(prefix="vmap-"))
        self.addCleanup(shutil.rmtree, str(tmp), True)
        work = work_folder(tmp)
        (work / "src" / "data" / "time-map.json").write_text(json.dumps({"rows": self.ROWS}), encoding="utf-8")
        d = sample()
        d["spans"]["c1"] = [[0.0, 2.0], [11.0, 13.0]]
        found = vmap.clip_words([(1.0, "one"), (12.0, "two")], vmap.load_rows(work), d, "c1")
        self.assertEqual([w[3] for w in found], ["one", "two"])
        self.assertAlmostEqual(found[1][1], 12.0)
        self.assertAlmostEqual(found[1][2], 17.0)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            say_rows = vmap.load_rows(work)
            self.assertTrue(say_rows)
        self.assertIn("toOld", vmap.explain(say_rows))

    def test_init_prints_the_warning_only_for_a_folder_with_a_map(self):
        tmp = Path(tempfile.mkdtemp(prefix="vmap-"))
        self.addCleanup(shutil.rmtree, str(tmp), True)
        work = work_folder(tmp)
        (work / "src" / "data" / "time-map.json").write_text(json.dumps({"rows": self.ROWS}), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            vinit.run_init(argparse.Namespace(work=str(work), spans=None, renew=False))
        self.assertIn("toOld", out.getvalue())
        (work / "src" / "data" / "time-map.json").write_text('{"rows": []}', encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            vinit.run_init(argparse.Namespace(work=str(work), spans=None, renew=True))
        self.assertNotIn("toOld", out.getvalue())


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is missing")
class SourceSecondsTest(unittest.TestCase):
    def test_a_spans_file_for_another_recording_stops_init_before_any_write(self):
        tmp = Path(tempfile.mkdtemp(prefix="vsrc-"))
        self.addCleanup(shutil.rmtree, str(tmp), True)
        work = work_folder(tmp)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=black:size=64x36:rate=30:duration=4", "-pix_fmt", "yuv420p",
                        str(work / "public" / "clips" / "source.mp4")], check=True)
        own = tmp / "own.json"
        own.write_text(json.dumps({**sample(), "source_seconds": 9.0}), encoding="utf-8")
        with self.assertRaises(ToolError) as caught:
            vinit.run_init(argparse.Namespace(work=str(work), spans=str(own), renew=False))
        self.assertIn("9.00", str(caught.exception))
        self.assertFalse((work / "src" / "vertical").exists())
        own.write_text(json.dumps({**sample(), "source_seconds": 4.2}), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vinit.run_init(argparse.Namespace(work=str(work), spans=str(own), renew=False)), 0)


class FinalTest(unittest.TestCase):
    def args(self, dest, **kw):
        ns = argparse.Namespace(work="/w", dest=str(dest), ids=[], lufs=-14.0, hum_accepted=None)
        for k, v in kw.items():
            setattr(ns, k, v)
        return ns

    def test_numpy_is_looked_for_before_the_render(self):
        with mock.patch.object(vfinal, "_np", side_effect=ToolError("нужен numpy")), mock.patch.object(vfinal.vplan, "load_plan") as plan:
            with self.assertRaises(ToolError):
                vfinal.run_final(self.args(Path("/tmp/x")))
            plan.assert_not_called()

    def test_an_empty_reason_is_refused(self):
        with self.assertRaises(ToolError):
            vfinal.run_final(self.args(Path("/tmp/x"), hum_accepted="  "))

    def test_a_write_error_is_a_message_not_a_traceback(self):
        with mock.patch.object(vfinal, "_np"), mock.patch.object(vfinal.vplan, "load_plan", return_value=(Path("/w"), sample(), ["c1"])), \
                mock.patch.object(vfinal.vplan, "typecheck"), mock.patch.object(vfinal, "finish", side_effect=OSError(28, "No space left")):
            with self.assertRaises(ToolError) as caught:
                vfinal.run_final(self.args(Path(tempfile.gettempdir()) / "vfinal-x"))
        self.assertIn("No space left", str(caught.exception))
        shutil.rmtree(str(Path(tempfile.gettempdir()) / "vfinal-x"), ignore_errors=True)

    def test_success_removes_an_old_failed_file_of_the_clip(self):
        tmp = Path(tempfile.mkdtemp(prefix="vfin-"))
        self.addCleanup(shutil.rmtree, str(tmp), True)
        work = tmp / "w"
        (work / "public" / "clips").mkdir(parents=True)
        (work / "public" / "clips" / "speech.wav").write_bytes(b"x")
        dest = tmp / "d"
        dest.mkdir()
        (dest / ".c1.failed.mp4").write_bytes(b"old")

        def fake_mix(speech, click, silent, spans, rate, total, click_at, out, lufs):
            Path(out).write_bytes(b"new")

        with mock.patch.object(vfinal, "render_silent", return_value=tmp / "s.mp4"), mock.patch.object(vfinal.vsound, "mix", side_effect=fake_mix), \
                mock.patch.object(vfinal.vmeasure, "check_clip", return_value=(True, [])), contextlib.redirect_stdout(io.StringIO()), \
                mock.patch.object(vfinal, "warn"):
            self.assertTrue(vfinal.finish(work, dest, sample(), "c1", -14.0, None))
        self.assertTrue((dest / "Example clip.mp4").is_file())
        self.assertFalse((dest / ".c1.failed.mp4").exists())


class SourceTextTest(unittest.TestCase):
    def test_timeouts_of_the_frame_script_match_the_final(self):
        text = (KIT / "tools" / "vertical-frames.mjs").read_text(encoding="utf-8")
        self.assertEqual(text.count("timeoutInMilliseconds: 120000"), 2)

    def test_no_hard_coded_white_edge_and_the_card_is_audited(self):
        kit = (VERTICAL / "VKit.tsx").read_text(encoding="utf-8")
        self.assertNotIn("#fff", kit.lower())
        self.assertIn("data-cta-card", kit)
        self.assertIn("data-cta", kit)
        self.assertIn("data-cta-card", (VERTICAL / "audit.tsx").read_text(encoding="utf-8"))

    def test_the_call_is_optional_in_typescript(self):
        self.assertIn("HAS_CTA", (VERTICAL / "clips.ts").read_text(encoding="utf-8"))
        self.assertIn("!HAS_CTA", (VERTICAL / "VKit.tsx").read_text(encoding="utf-8"))


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = overlay.main(argv)
    return code, out.getvalue(), err.getvalue()


class WordsCommandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vwords-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.work = work_folder(self.tmp)
        (self.work / "src" / "vertical").mkdir()
        (self.work / "src" / "vertical" / "spans.json").write_text(json.dumps({**sample(), "spans": {"c1": [[0.0, 3.0]]}}), encoding="utf-8")  # no scenes at all
        self.words = self.tmp / "words.txt"
        self.words.write_text("   1.00 one\n   2.50 two\n   9.00 late\n", encoding="utf-8")

    def test_works_on_a_folder_without_scenes_with_words_from_a_file(self):
        code, out, err = run_main(["vertical-words", str(self.work), "--words", str(self.words)])
        self.assertEqual(code, 0, err)
        self.assertIn("one", out)
        self.assertIn("two", out)
        self.assertNotIn("late", out)

    def test_a_clip_that_is_not_in_the_data_is_named(self):
        code, _, err = run_main(["vertical-words", str(self.work), "c9", "--words", str(self.words)])
        self.assertEqual(code, 2)
        self.assertIn("c9", err)

    def test_missing_words_name_the_way_out(self):
        code, _, err = run_main(["vertical-words", str(self.work)])
        self.assertEqual(code, 2)
        self.assertIn("--words", err)

    def test_the_set_is_needed(self):
        (self.work / "src" / "vertical" / "spans.json").unlink()
        code, _, err = run_main(["vertical-words", str(self.work), "--words", str(self.words)])
        self.assertEqual(code, 2)
        self.assertIn("vertical-init", err)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is missing")
    def test_with_a_map_words_past_the_end_of_the_file_stop(self):
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=black:size=64x36:rate=30:duration=4", "-pix_fmt", "yuv420p",
                        str(self.work / "public" / "clips" / "source.mp4")], check=True)
        (self.work / "src" / "data" / "time-map.json").write_text(json.dumps({"rows": TimeMapTest.ROWS}), encoding="utf-8")
        self.words.write_text("   1.00 one\n  50.00 old-seconds\n", encoding="utf-8")
        code, _, err = run_main(["vertical-words", str(self.work), "--words", str(self.words)])
        self.assertEqual(code, 2)
        self.assertIn("старых секундах", err)
        self.words.write_text("   1.00 one\n   3.00 three\n", encoding="utf-8")
        code, out, err = run_main(["vertical-words", str(self.work), "--words", str(self.words)])
        self.assertEqual(code, 0, err)
        self.assertIn("toOld", out)


class HumSummaryTest(FinalTest):
    def run_with(self, passed_ids):
        def fake_finish(work, dest, data, cid, lufs, reason, passed=None):
            if passed is not None and cid in passed_ids:
                passed.append(cid)
            return True
        out = io.StringIO()
        with mock.patch.object(vfinal, "_np"), mock.patch.object(vfinal.vplan, "load_plan", return_value=(Path("/w"), sample(), ["c1", "c2"])), \
                mock.patch.object(vfinal.vplan, "typecheck"), mock.patch.object(vfinal, "finish", side_effect=fake_finish), contextlib.redirect_stdout(out):
            code = vfinal.run_final(self.args(Path(tempfile.mkdtemp(prefix="vfin-")), hum_accepted="listened, nonstop speech"))
        return code, out.getvalue()

    def test_only_the_clips_where_a_finding_was_let_through_are_named(self):
        code, text = self.run_with(["c2"])
        self.assertEqual(code, 0)
        self.assertIn("c2", text.split("Гул пропущен")[1].split("по основанию")[0])
        self.assertNotIn("c1", text.split("Гул пропущен")[1].split("по основанию")[0])

    def test_no_summary_of_a_waiver_that_was_not_used(self):
        _, text = self.run_with([])
        self.assertNotIn("Гул пропущен", text)
        self.assertIn("не понадобился", text)

    def test_finish_records_the_clip_whose_hum_was_waived(self):
        tmp = Path(tempfile.mkdtemp(prefix="vfin-"))
        self.addCleanup(shutil.rmtree, str(tmp), True)
        work = tmp / "w"
        (work / "public" / "clips").mkdir(parents=True)
        (work / "public" / "clips" / "speech.wav").write_bytes(b"x")
        dest = tmp / "d"
        dest.mkdir()
        passed = []
        with mock.patch.object(vfinal, "render_silent", return_value=tmp / "s.mp4"), mock.patch.object(vfinal.vsound, "mix", side_effect=lambda *a, **k: Path(a[7]).write_bytes(b"n")), \
                mock.patch.object(vfinal.vmeasure, "check_clip", return_value=(True, ["ПРЕДУПРЕЖДЕНИЕ гул пропущен по основанию «x»: y"])), \
                contextlib.redirect_stdout(io.StringIO()), mock.patch.object(vfinal, "warn"):
            vfinal.finish(work, dest, sample(), "c1", -14.0, "x", passed)
        self.assertEqual(passed, ["c1"])


class BundleTest(unittest.TestCase):
    def test_each_run_has_its_own_bundle_folder(self):
        tmp = Path(tempfile.mkdtemp(prefix="vbun-"))
        self.addCleanup(shutil.rmtree, str(tmp), True)
        with mock.patch.object(vcheck, "run"), mock.patch.object(vcheck.remotion, "_npx", return_value="npx"):
            a, b = vcheck.bundle(tmp), vcheck.bundle(tmp)
        self.assertNotEqual(a, b)
        self.assertNotEqual(a.parent, b.parent)
        self.assertTrue(a.parent.is_dir() and b.parent.is_dir())


class SameSpansTest(unittest.TestCase):
    def test_spans_pointing_at_the_own_file_is_a_normal_case(self):
        tmp = Path(tempfile.mkdtemp(prefix="vsame-"))
        self.addCleanup(shutil.rmtree, str(tmp), True)
        work = work_folder(tmp)
        with contextlib.redirect_stdout(io.StringIO()):
            vinit.run_init(argparse.Namespace(work=str(work), spans=None, renew=False))
        own = work / "src" / "vertical" / "spans.json"
        before = own.read_text(encoding="utf-8")
        for renew in (True, False):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(vinit.run_init(argparse.Namespace(work=str(work), spans=str(own), renew=renew)), 0)
            self.assertIn("тот же", out.getvalue())
        self.assertEqual(own.read_text(encoding="utf-8"), before)


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is missing")
class FaceTrackWarningTest(unittest.TestCase):
    def init_with(self, track_end):
        tmp = Path(tempfile.mkdtemp(prefix="vface-"))
        self.addCleanup(shutil.rmtree, str(tmp), True)
        work = work_folder(tmp)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=black:size=64x36:rate=30:duration=20", "-pix_fmt", "yuv420p",
                        str(work / "public" / "clips" / "source.mp4")], check=True)
        (work / "src" / "data" / "face.json").write_text(json.dumps([[t * 0.5, 0.5, 0.4, 0.4] for t in range(int(track_end * 2) + 1)]), encoding="utf-8")
        (work / "src" / "data" / "time-map.json").write_text(json.dumps({"rows": TimeMapTest.ROWS}), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            vinit.run_init(argparse.Namespace(work=str(work), spans=None, renew=False))
        return out.getvalue()

    def test_a_track_as_long_as_the_file_is_flagged_when_there_is_a_map(self):
        self.assertIn("трек лица", self.init_with(20.0))

    def test_a_longer_track_is_not(self):
        self.assertNotIn("трек лица", self.init_with(31.0))


class TextsTest(unittest.TestCase):
    def test_no_promise_of_a_pad_and_one_length_definition(self):
        md = (KIT / "vertical.md").read_text(encoding="utf-8")
        self.assertNotIn("unless the person asked", md)
        self.assertNotIn("Count length limits", md)
        self.assertNotIn("20-60", md)
        self.assertNotIn("unless the person asked", (KIT / "tools" / "overlaylib" / "vsound.py").read_text(encoding="utf-8"))
        self.assertIn("time-map.json", md)
        self.assertIn("face.json", md)


class NothingPersonalTest(unittest.TestCase):
    FORBIDDEN = ["УРОК", "Хотите", "пришлю", "Напишите", "AlexFisenkov", "fisenkov", "/Users/", "Movies", "Documents/", "Яндекс"]

    def test_files_exist(self):
        for path in (VERTICAL / "VKit.tsx", KIT / "examples" / "vertical" / "c1.tsx", KIT / "tools" / "vertical-frames.mjs"):
            self.assertTrue(path.is_file(), path)

    def test_no_owner_words_paths_or_call_text_in_code(self):
        for path in NEW_FILES:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for word in self.FORBIDDEN:
                self.assertNotIn(word, text, "{} in {}".format(word, path.name))

    def test_typescript_has_no_cyrillic_outside_the_audit_vocabulary(self):
        for path in [*VERTICAL.glob("*.ts*"), KIT / "examples" / "vertical" / "c1.tsx"]:
            if path.name == "audit.tsx":
                continue  # the names of the findings are the report's vocabulary
            self.assertIsNone(re.search("[А-Яа-яЁё]", path.read_text(encoding="utf-8")), path.name)

    def test_the_call_to_action_text_is_data(self):
        data = sample()
        self.assertTrue(data["cta"]["word"])
        for name in ("VKit.tsx", "clips.ts"):
            text = (VERTICAL / name).read_text(encoding="utf-8")
            self.assertIn("CTA.", text) if name == "VKit.tsx" else None
            self.assertNotIn(data["cta"]["word"], text)


if __name__ == "__main__":
    unittest.main()
