"""The four insert templates of Chrome & Graphite: no script, no network, filled from the tokens.

The real HyperFrames render runs only with AIEDITING_REAL_HYPERFRAMES=1 (needs Node 22+, HyperFrames
0.9.16 from `ae.py doctor --install hyperframes --yes` and its browser).
"""
import os
import re
import subprocess
import unittest

from _support import TempDirCase, needs_ffmpeg
from runtime.render import hyperframes
from runtime.render.anim_page import page
from runtime.render.anim_spec import box, spec, template_file
from runtime.render.design import default_design, load_design

NAMES = ("файлы", "шаги", "список", "число")
SLOT = {"template": "файлы", "title": "Файлы <проекта>", "items": ["agents.md", "memory.md", "spec", "plan"]}


class Templates(TempDirCase):
    def test_each_template_is_a_quiet_scene(self):
        for name in NAMES:
            text = template_file(default_design(), name).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"https?://|<script|@import", name)
            self.assertIn("data-no-timeline", text, "CSS motion: HyperFrames must not wait for a GSAP timeline")
            self.assertIn("<!--item-->", text)
        self.assertIsNone(template_file(default_design(), "видео"))

    def test_page_is_filled_from_the_tokens_and_brings_its_fonts(self):
        design = load_design(default_design())
        s = spec(design)
        size = box(SLOT, s, (1920, 1080))
        self.assertEqual([v % 2 for v in size], [0, 0], "even sizes for the codec")
        self.assertEqual(size[0], 576, "the token's 0.3 of the frame width")
        folder = page(template_file(design, "файлы"), SLOT, design, s, size, 1080, 5.4, self.tmp / "p")
        html = (folder / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("{{", html)
        self.assertEqual(html.count('class="row"'), 4)
        self.assertIn("Файлы &lt;проекта&gt;", html, "text is escaped")
        self.assertIn("--bg:rgba(32,33,35,0.820)", html, "graphite-soft at the token's alpha")
        self.assertIn('data-duration="5.400"', html)
        self.assertTrue(re.search(r'data-width="{}" data-height="{}"'.format(*size), html))
        fonts = sorted(p.name for p in (folder / "assets" / "fonts").iterdir())
        self.assertIn("JetBrainsMono.ttf", fonts)
        self.assertIn("Onest.ttf", fonts)


@needs_ffmpeg
@unittest.skipUnless(os.environ.get("AIEDITING_REAL_HYPERFRAMES") == "1" and hyperframes.missing() is None,
                     "real HyperFrames render is opt-in (AIEDITING_REAL_HYPERFRAMES=1)")
class RealRender(TempDirCase):
    def test_files_clip_has_alpha_and_its_length(self):
        from runtime.render import animation

        clip = animation(SLOT, default_design(), (1920, 1080), self.tmp / "a", 5.0)
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=pix_fmt,duration", "-of",
                              "default=nw=1", str(clip["video"])], capture_output=True, text=True).stdout
        self.assertIn("pix_fmt=yuva444p", out)
        self.assertAlmostEqual(float(re.search(r"duration=([\d.]+)", out).group(1)), 5.0, delta=0.05)
