"""`doctor` knows HyperFrames: only a format with animations needs it, no Node → a plain hint, the pinned
version goes into AIEditing's own npm prefix, then its browser on the standard path — installer faked."""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

from _support import SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))
AE = SKILL / "tools" / "ae.py"
ROW = next(r for r in json.loads((SKILL / "catalog" / "tools.json").read_text(encoding="utf-8"))["tools"]
           if r["id"] == "hyperframes")
LESSON = ["speech_spans", "cut_spans", "write_srt", "plate", "overlay_png"]


class HyperFramesDoctor(TempDirCase):
    def setUp(self):
        super().setUp()
        self.prefix = self.tmp / "node prefix"
        self.env = mock.patch.dict(os.environ, {"AIEDITING_NODE_PREFIX": str(self.prefix)})
        self.env.start()
        self.calls = []

    def tearDown(self):
        self.env.stop()
        super().tearDown()

    def fake_run(self, argv, env=None):
        self.calls.append((list(argv), dict(env or {})))
        if "install" in argv:  # what npm leaves behind
            pkg = self.prefix / "node_modules" / "hyperframes"
            pkg.mkdir(parents=True)
            (pkg / "package.json").write_text(json.dumps({"version": "0.8.201", "bin": {
                "hyperframes": "./bin/hyperframes.mjs"}}), encoding="utf-8")
        return "поставлено"

    def install(self, major):
        from aelib import installers, npm

        with mock.patch.object(npm, "node_major", return_value=major), \
                mock.patch.object(installers, "_run", side_effect=self.fake_run), \
                mock.patch.object(npm.shutil, "which", side_effect=lambda n: "/opt/bin/" + n):
            return installers.run_install(ROW)

    def test_only_a_format_with_animations_needs_node_and_hyperframes(self):
        from aelib import catalog

        self.assertEqual([t for t in catalog.needs(LESSON + ["animations"], "scribe")["tools"]
                          if t in ("node", "hyperframes")], ["node", "hyperframes"])
        self.assertFalse({"node", "hyperframes"} & set(catalog.needs(LESSON, "scribe")["tools"]))
        self.assertEqual((ROW["pin"], ROW["pin_kind"], ROW["license"]), ("0.8.201", "exact", "Apache-2.0"))

    def test_no_node_gives_a_plain_hint_and_installs_nothing(self):
        out = self.install(None)
        self.assertIn("Нет Node.js 22+", out)
        self.assertIn("--install node", out)
        self.assertIn("Ничего не поставлено", out)
        self.assertEqual(self.calls, [])
        self.assertIn("старше нужного 22", self.install(20))

    def test_installs_the_pin_into_the_own_prefix_then_its_browser_quietly(self):
        out = self.install(26)
        self.assertTrue(out.startswith("поставлено"), out)
        (npm_argv, npm_env), (ensure_argv, ensure_env) = self.calls
        self.assertEqual(npm_argv[1:3], ["install", "--prefix"])
        self.assertEqual(Path(npm_argv[3]), self.prefix)
        self.assertIn("--save-exact", npm_argv)
        self.assertEqual(npm_argv[-1], "hyperframes@0.8.201")
        self.assertNotIn("-g", npm_argv)
        self.assertEqual(Path(ensure_argv[1]), self.prefix / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs")
        self.assertEqual(ensure_argv[2:], ["browser", "ensure"])
        for env in (npm_env, ensure_env):
            self.assertEqual(env.get("HYPERFRAMES_NO_TELEMETRY"), "1")
            self.assertEqual(env.get("DO_NOT_TRACK"), "1")

    def test_status_is_the_exact_pin_in_the_prefix(self):
        from aelib.checks import status

        self.assertFalse(status(ROW)["ok"])
        self.install(26)
        self.assertTrue(status(ROW)["ok"])
        meta = self.prefix / "node_modules" / "hyperframes" / "package.json"
        meta.write_text(json.dumps({"version": "0.8.212"}), encoding="utf-8")
        self.assertIn("вместо пина 0.8.201", status(ROW)["note"])

    def test_doctor_lists_them_for_the_step_and_plans_without_installing(self):
        env = dict(os.environ, AIEDITING_NODE_PREFIX=str(self.prefix), AIEDITING_IN_VENV="1")
        run = lambda *a: subprocess.run([sys.executable, str(AE), "doctor", *a], capture_output=True,  # noqa: E731
                                        text=True, encoding="utf-8", env=env)
        listed = run("--steps", "animations")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertRegex(listed.stdout, r"hyperframes\s+нет")
        self.assertIn("node", listed.stdout)
        planned = run("--install", "hyperframes")
        self.assertIn("npm install --prefix", planned.stdout)
        self.assertIn("hyperframes@0.8.201", planned.stdout)
        self.assertIn("нужно «да»", planned.stdout)
        self.assertFalse(self.prefix.exists())
