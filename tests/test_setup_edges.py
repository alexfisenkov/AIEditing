"""Regression cases from independent review: plans, environments and concurrent repair."""
import contextlib
import hashlib
import importlib.util
import io
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _support import SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))


def entrypoint():
    spec = importlib.util.spec_from_file_location("ae_review_edges", SKILL / "tools" / "ae.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SetupEdges(TempDirCase):
    def test_doctor_plan_does_not_prepare_python(self):
        ae = entrypoint()
        with mock.patch.object(sys, "argv", ["ae.py", "doctor", "--install", "rembg"]), \
                mock.patch("aelib.bootstrap.ensure_python") as prepare:
            ae._prepare_python_for_requested_tools()
        prepare.assert_not_called()

    def test_invalid_command_is_rejected_before_installing_anything(self):
        ae = entrypoint()
        with mock.patch.object(sys, "argv", ["ae.py", "setup", "--not-a-flag"]), \
                mock.patch("aelib.bootstrap.ensure_python") as prepare, \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            ae._prepare_python_for_requested_tools()
        prepare.assert_not_called()

    def test_unknown_recogniser_cannot_skip_its_dependencies(self):
        from aelib import catalog
        with self.assertRaises(ValueError):
            catalog.needs(["write_srt"], "whispercPP")

    def test_behind_head_cannot_build_without_graphics(self):
        from aelib.coherence import problems
        self.assertTrue(problems({"steps": ["behind_head"], "params": {}}))
        self.assertFalse(problems({"steps": ["behind_head", "plate"], "params": {}}))

    def test_explicit_model_does_not_require_downloading_the_default(self):
        from aelib.cmd_background import run
        source, model, result = self.tmp / "source.mp4", self.tmp / "custom.onnx", self.tmp / "result.mov"
        source.write_bytes(b"video")
        model.write_bytes(b"model")
        opt = SimpleNamespace(video=str(source), output=str(result), mode="remove", model=str(model), value=None,
                              downsample_ratio=None)
        with mock.patch("aelib.setup.ensure_tools", return_value="ready") as ensure, \
                mock.patch("runtime.media.background.edit_background", return_value=result), \
                contextlib.redirect_stdout(io.StringIO()):
            run(opt)
        self.assertNotIn("rvm-model", ensure.call_args.args[0])

    def test_parallel_downloads_have_separate_verified_temporary_files(self):
        from aelib import downloads
        body, barrier = b"verified-model-data" * 10, threading.Barrier(2)
        dest = self.tmp / "model.onnx"
        step = {"url": "https://example.invalid/model", "save_to": str(dest),
                "sha256": hashlib.sha256(body).hexdigest()}
        sources = []
        real_replace = os.replace

        def fetch(url):
            barrier.wait(timeout=5)
            yield body[:9]
            barrier.wait(timeout=5)
            yield body[9:]

        def replace(src, target):
            sources.append(str(src))
            real_replace(src, target)

        with mock.patch("aelib.downloads.fetch", fetch), mock.patch("aelib.downloads.os.replace", replace):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(downloads.download, [step, step]))
        self.assertEqual(len(results), 2)
        self.assertEqual(len(set(sources)), 2)
        self.assertEqual(dest.read_bytes(), body)
        self.assertEqual(list(self.tmp.glob("*.part")), [])

    def test_foreign_venv_still_hands_off_to_private_python(self):
        if os.name == "nt":
            self.skipTest("test executable uses a POSIX shebang; Windows selection is covered separately")
        home = self.tmp / "fake-home"
        private = home / ".aiediting" / "venv" / "bin" / "python"
        marker = self.tmp / "private-used"
        private.parent.mkdir(parents=True)
        private.write_text("#!{}\nfrom pathlib import Path\nPath({!r}).write_text('yes')\n".format(sys.executable, str(marker)))
        private.chmod(0o755)
        target = SKILL / "templates" / "format-skill" / "run.py"
        wrapper = ("import sys,runpy; from pathlib import Path; from unittest import mock; "
                   "sys.prefix='foreign-venv'; sys.argv=[{!r},'check']; "
                   "patch=mock.patch('pathlib.Path.home',return_value=Path({!r})); patch.start(); "
                   "runpy.run_path({!r},run_name='__main__')").format(str(target), str(home), str(target))
        proc = subprocess.run([sys.executable, "-B", "-c", wrapper], capture_output=True, text=True,
                              env={k: v for k, v in os.environ.items() if k != "AIEDITING_IN_VENV"})
        self.assertTrue(marker.is_file(), proc.stdout + proc.stderr)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_symlinked_binary_is_not_the_identity_of_a_virtual_environment(self):
        import venv
        if os.name == "nt":
            self.skipTest("POSIX symlink regression; Windows venv selection has separate coverage")
        folder = self.tmp / "real-venv"
        venv.EnvBuilder(with_pip=False, symlinks=True).create(folder)
        private = folder / "bin" / "python"
        self.assertEqual(private.resolve(), Path(sys.executable).resolve())
        ae = entrypoint()
        with mock.patch.object(ae, "venv_python", return_value=private), \
                mock.patch.dict(os.environ, {"AIEDITING_IN_VENV": ""}), \
                mock.patch.object(ae.subprocess, "call", return_value=0) as handoff, \
                self.assertRaises(SystemExit):
            ae._in_private_env()
        self.assertEqual(handoff.call_args.args[0][0], str(private))
