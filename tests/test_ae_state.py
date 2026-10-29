"""The workshop's state and page: stages, waits, formats, frames, layout, design variants, trial clips."""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from _support import SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))

import runtime.look  # noqa: E402
import runtime.pipelines  # noqa: E402
import runtime.render  # noqa: E402


def png(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 16)
    return path


class Base(TempDirCase):
    def setUp(self):
        super().setUp()
        self.work = self.tmp / "work"
        env = {"AIEDITING_WORK": str(self.work), "AIEDITING_NO_SERVE": "1"}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.ae("init", "--title", "Проба")

    def ae(self, *args, code=0):
        from aelib.cli import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            got = main([str(a) for a in args])
        self.assertEqual(got, code, buf.getvalue())
        return buf.getvalue()

    def state(self):
        from state import read

        return read(self.work)

    def page_state(self):
        page = (self.work / "dashboard.html").read_text(encoding="utf-8")
        body = page.split("/*STATE-BEGIN*/window.STATE=", 1)[1].split(";/*STATE-END*/", 1)[0]
        return json.loads(body)


class Workshop(Base):
    def test_init_writes_state_and_page_snapshot(self):
        self.assertEqual(self.state()["app"], "aiediting")
        self.assertEqual(self.page_state()["rev"], self.state()["rev"])
        self.assertTrue((self.work / "index.html").is_file())
        self.assertIn("ошибка", self.ae("init", code=1))
        self.ae("init", "--fresh", "--mode", "refine")
        self.assertEqual(self.state()["mode"], "refine")

    def test_stage_closes_earlier_ones(self):
        self.ae("stage", "interview")
        got = {s["id"]: s["status"] for s in self.state()["stages"]}
        self.assertEqual((got["start"], got["formats"], got["interview"], got["design"]),
                         ("done", "skipped", "active", "pending"))

    def test_ask_and_answer_are_on_the_page(self):
        self.ae("ask", "question", "--note", "Раунд 1: паузы, субтитры, главы")
        self.assertEqual(self.page_state()["waiting"]["note"], "Раунд 1: паузы, субтитры, главы")
        self.ae("answered", "--note", "1б, остальное ок")
        state = self.state()
        self.assertIsNone(state["waiting"])
        self.assertEqual(state["log"][-1]["note"], "1б, остальное ок")

    def test_formats_answer_drafts_profiles_and_own_format_is_marked(self):
        self.ae("formats", "урок, подкаст")
        rows = self.state()["formats"]
        self.assertEqual([(r["skill"], r["custom"]) for r in rows], [("монтаж-урок", False), ("монтаж-подкаст", True)])
        self.ae("profile", "set", "монтаж-подкаст", "params.gap=0.4", "approval=parts")
        self.ae("profile", "taste", "монтаж-подкаст", "плашки", "мельче", "--video", "проба-01")
        profile = json.loads((self.work / "монтаж-подкаст" / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual((profile["params"]["gap"], profile["approval"]), (0.4, "parts"))
        self.assertEqual(profile["taste"][-1]["note"], "плашки мельче")

    def test_frames_layout_and_design_variants_reach_the_page(self):
        names = ["frame_00{}_t{}.0s.png".format(i, i * 10) for i in (1, 2, 3)]
        shots = [png(self.tmp / "look" / n) for n in names]
        video = png(self.tmp / "исходник.mp4")
        with mock.patch.object(runtime.look, "frames", create=True, return_value=shots) as frames:
            self.ae("frames", video, "--n", "3")
        self.assertEqual(frames.call_args.kwargs["outdir"], (self.work / "sources" / "s1").resolve())
        guess = {"kind": "screen_face_window", "face": [10, 10, 40, 40], "confidence": 0.8}
        with mock.patch.object(runtime.look, "detect_layout", create=True, return_value=guess):
            self.ae("layout", "s1")
        src = self.page_state()["sources"][0]
        self.assertEqual(src["frames"], ["sources/s1/" + n for n in names])  # the time stays in the name
        self.assertTrue(all((self.work / f).is_file() for f in src["frames"]))
        self.assertEqual(src["layout"]["kind"], "screen_face_window")
        self.ae("layout", "s1", "--set", "kind=face_full")
        self.assertEqual(self.state()["sources"][0]["layout"]["by"], "person")
        variants = [png(self.tmp / "render" / "v{}.png".format(i)) for i in range(3)]
        with mock.patch.object(runtime.render, "samples", create=True, return_value=variants) as samples:
            self.ae("samples", "монтаж-урок", "--element", "chapter")
        self.assertEqual(samples.call_args.kwargs["kind"], "chapter")
        self.assertEqual(samples.call_args.kwargs["face"], [10, 10, 40, 40])
        self.assertEqual(len(self.page_state()["design"]["samples"][0]["files"]), 3)
        self.ae("choose", "монтаж-урок", "chapter", "2")
        self.assertTrue((self.work / "монтаж-урок" / "design" / "samples" / "chapter.png").is_file())


class Trial(Base):
    def setUp(self):
        super().setUp()
        self.ae("formats", "урок")
        self.video = png(self.tmp / "урок.mp4")

    def test_trial_clip_is_shown_and_asks_if_it_is_liked(self):
        def run(src, profile, outdir, approve):
            self.assertEqual(profile["skill_name"], "монтаж-урок")
            return {"output": png(Path(outdir) / "ролик.mp4")}

        with mock.patch.object(runtime.pipelines, "run", create=True, side_effect=run):
            self.ae("trial", "монтаж-урок", self.video)
        state = self.page_state()
        self.assertEqual(state["trials"][0]["video"], "монтаж-урок/trials/01/out/ролик.mp4")
        self.assertEqual(state["waiting"]["kind"], "trial")
        self.ae("verdict", "монтаж-урок", "no", "--note", "паузы длинные")
        self.assertEqual(self.state()["trials"][0]["verdict"], "no")

    def test_a_decision_stops_the_trial_until_answered(self):
        seen = {}

        def run(src, profile, outdir, approve):
            payload = {"key": "regions", "regions": [1, 2]}
            if approve("blur", payload):
                seen["regions"] = payload["regions"]
            return {"output": png(Path(outdir) / "ролик.mp4")}

        with mock.patch.object(runtime.pipelines, "run", create=True, side_effect=run):
            self.ae("trial", "монтаж-урок", self.video, code=3)
            folder = self.work / "монтаж-урок" / "trials" / "01"
            self.assertEqual(json.loads((folder / "вопросы.json").read_text(encoding="utf-8"))["key"], "regions")
            answers = folder / "ответы.json"
            answers.write_text(json.dumps({"regions": {"ok": True, "payload": {"regions": [2]}}}), encoding="utf-8")
            self.ae("trial", "монтаж-урок", self.video, "--answers", answers)
        self.assertEqual(seen["regions"], [2])
        self.assertEqual(len(self.state()["trials"]), 1)


if __name__ == "__main__":
    unittest.main()
