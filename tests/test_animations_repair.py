"""F6 review repairs: history kept in the run folder, readiness before asking, 9:16 readable, one broken
insert never breaks the video, answers read leniently (no Node, Chrome or ffmpeg needed)."""
import os
import unittest
from pathlib import Path
from unittest import mock

from _support import TempDirCase
from runtime.pipelines.anim_answer import points, seconds, span
from runtime.render import RenderError, hf_ready, hyperframes
from runtime.render.anim_page import page
from runtime.render.anim_spec import REFERENCE, box, spec, template_file, unit
from runtime.render.design import default_design, load_design

FILES = {"template": "файлы", "title": "Файлы", "items": ["agents.md", "memory.md", "spec", "plan"]}


class History(TempDirCase):
    def test_env_points_history_and_ffmpeg_where_aiediting_says(self):
        with mock.patch.dict(os.environ, {"AIEDITING_FFMPEG": "/opt/ff/ffmpeg", "AIEDITING_FFPROBE": "/opt/ff/ffprobe"}):
            env = hyperframes.env(self.tmp / "h")
        self.assertEqual(env["HYPERFRAMES_HISTORY_ROOT"], str(self.tmp / "h"))
        self.assertEqual(env["HYPERFRAMES_FFMPEG_PATH"], "/opt/ff/ffmpeg")
        self.assertEqual(env["HYPERFRAMES_FFPROBE_PATH"], "/opt/ff/ffprobe")
        self.assertEqual(env["HYPERFRAMES_NO_TELEMETRY"], "1")

    def test_render_keeps_the_history_next_to_the_project(self):
        project, out, seen = self.tmp / "run" / "000" / "project", self.tmp / "run" / "000" / "insert.mov", {}
        project.mkdir(parents=True)

        def fake(argv, **kw):
            seen.update(kw)
            out.write_bytes(b"mov")
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(hyperframes, "missing", return_value=None), \
                mock.patch.object(hyperframes.subprocess, "run", side_effect=fake):
            hyperframes.render_mov(project, out)
        root = Path(seen["env"]["HYPERFRAMES_HISTORY_ROOT"])
        self.assertEqual(root.parent, project.parent, "inside the run folder, removed with it")
        self.assertNotIn(".cache", root.parts)


class Ready(unittest.TestCase):
    def test_old_node_or_no_browser_is_a_reason_not_a_question(self):
        with mock.patch.object(hyperframes, "missing", return_value=None):
            with mock.patch.object(hf_ready, "node_major", return_value=20):
                self.assertIn("старше нужного 22", hf_ready.problem())
            with mock.patch.object(hf_ready, "node_major", return_value=26), \
                    mock.patch.object(hf_ready, "browser", return_value=None):
                self.assertIn("нет браузера рендера", hf_ready.problem())


class Vertical(TempDirCase):
    def test_on_9x16_the_insert_is_as_readable_as_on_16x9(self):
        s = spec(default_design())
        self.assertEqual(box(FILES, s, (1080, 1920)), box(FILES, s, (1920, 1080)))
        self.assertEqual(unit((1080, 1920)), 1080)
        w, _h = box(FILES, s, (1080, 1920))
        body = s["body_size"] * 1080
        free = w - 2 * s["pad"] * 1080 - body * 1.4  # the file mark and the gap
        self.assertGreater(free, len("memory.md") * 0.62 * body, "the longest name fits in mono")
        self.assertGreater(body, 24, "body text at least 24 px on a 1080-wide phone frame")

    def test_a_long_figure_shrinks_to_fit(self):
        design = load_design(default_design())
        slot = {"template": "число", "title": "200 тысяч", "items": ["токенов"]}
        s = spec(design)
        size = box(slot, s, (1080, 1920))
        html = (page(template_file(design, "число"), slot, design, s, size, 1080, 5.0, self.tmp / "p")
                / "index.html").read_text(encoding="utf-8")
        figure = float(html.split("--number-size:")[1].split("px")[0])
        self.assertLess(figure * 0.68 * len("200 тысяч"), size[0] - 2 * s["pad"] * 1080 + 1)


class Tokens(TempDirCase):
    def test_missing_or_broken_tokens_fall_back_to_the_reference(self):
        own = {"root": self.tmp, "color": {"ink": "#111111"}, "font": {},
               "video": {"animation": {"size": "крупно", "bg": "нет-такого", "radius": 0.01}}}
        s = spec(own)
        self.assertEqual(s["size"], REFERENCE["size"])
        self.assertEqual(s["radius"], 0.01)
        self.assertEqual(s["body_size"], REFERENCE["body_size"])
        with mock.patch("runtime.render.anim_page._fonts", return_value=[]):
            folder = page(template_file(own, "файлы"), FILES, own, s, box(FILES, s, (1920, 1080)), 1080, 5.0,
                          self.tmp / "p")
        self.assertIn("--bg:rgba(32,33,35,0.820)", (folder / "index.html").read_text(encoding="utf-8"))


class OneInsertFails(TempDirCase):
    def test_a_failing_insert_is_noted_and_the_next_one_is_made(self):
        from runtime.pipelines.anim_layer import layers

        class Ctx:
            layout, notes, report = None, [], {}

            def p(self, name, default=None):
                return default

            def design(self, vertical=False):
                return load_design(default_design())

            def note(self, text):
                self.notes.append(text)

        made = iter([OSError("шрифт не читается"), {"video": self.tmp / "b.mov", "size": (576, 300)}])

        def fake(*_a, **_k):
            got = next(made)
            if isinstance(got, Exception):
                raise got
            return got

        items = [dict(FILES, kind="animation", start=1.0, end=6.0), dict(FILES, kind="animation", start=50.0, end=55.0)]
        ctx = Ctx()
        with mock.patch("runtime.render.animation", side_effect=fake):
            out = layers(ctx, {"id": None}, items, (1920, 1080), self.tmp)
        self.assertEqual([o["start"] for o in out], [50.0])
        self.assertTrue(any("не сделана: шрифт не читается" in n for n in ctx.notes), ctx.notes)
        self.assertEqual(len(ctx.report["animations"]), 1)
        with mock.patch("runtime.render.animation", side_effect=RenderError("нет шаблона")):
            self.assertEqual(layers(ctx, {"id": None}, items[:1], (1920, 1080), self.tmp), [])


class Answer(unittest.TestCase):
    def test_points_start_and_end_are_read_leniently(self):
        self.assertEqual(points("agents.md, memory.md,, spec"), ["agents.md", "memory.md", "spec"])
        self.assertEqual(len(points(["a", "b", "c", "d", "e", "f", "g", "h"])), 6)
        self.assertEqual(seconds("0:01:23"), 83.0)
        self.assertEqual(seconds("1:23.5"), 83.5)
        self.assertEqual(seconds("83,5"), 83.5)
        self.assertIsNone(seconds("в начале"))
        self.assertEqual(span({"start": "0:01:23", "end": 200}, 5.0)[0], (83.0, 98.0), "at most 15 s")
        self.assertEqual(span({"start": 10, "end": 9}, 5.0)[0], (10.0, 15.0))
        times, why = span({"start": "в начале"}, 5.0)
        self.assertIsNone(times)
        self.assertIn("0:01:23", why)


if __name__ == "__main__":
    unittest.main()
