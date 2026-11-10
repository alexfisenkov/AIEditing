"""A format skill with `animations` carries the insert templates and names Node and HyperFrames in its needs;
one without them has neither (G32: only what the interview chose)."""
import json
import subprocess
import sys

from _support import SKILL, TempDirCase
from test_build_skill import LESSON_STEPS, profile_for

AE = SKILL / "tools" / "ae.py"


class AnimationsInTheSkill(TempDirCase):
    def build(self, steps):
        profile = profile_for("урок", steps)
        profile["params"]["animations"] = {"every": 45}
        folder = self.tmp / "work" / profile["skill_name"]
        (folder / "design").mkdir(parents=True, exist_ok=True)
        (folder / "design" / "tokens.json").write_text('{"font": "Onest"}', encoding="utf-8")
        (folder / "profile.json").write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(AE), "build-skill", str(folder / "profile.json"),
                               str(self.tmp / "out"), "--replace"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return self.tmp / "out" / "монтаж-урок"

    def test_templates_and_needs_come_only_with_the_step(self):
        skill = self.build(LESSON_STEPS + ["animations"])
        names = sorted(p.name for p in (skill / "design" / "animations").iterdir())
        self.assertEqual(names, ["files.html", "list.html", "number.html", "steps.html"])
        pins = json.loads((skill / "pins.json").read_text(encoding="utf-8"))
        self.assertEqual(pins["tools"]["hyperframes"]["pin"], "0.9.28")
        self.assertIn("node", pins["tools"])
        self.assertIn("HyperFrames 0.9.28", (skill / "SKILL.md").read_text(encoding="utf-8"))
        plain = self.build(LESSON_STEPS)
        self.assertFalse((plain / "design" / "animations").exists())
        self.assertNotIn("hyperframes", json.loads((plain / "pins.json").read_text(encoding="utf-8"))["tools"])
