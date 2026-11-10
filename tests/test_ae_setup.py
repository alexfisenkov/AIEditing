"""An incomplete toolkit must never be reported as ready or installed."""
import json
import hashlib
import io
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from _support import SKILL, TempDirCase

sys.path.insert(0, str(SKILL / "tools"))

from aelib import checks, cli, doctor, installers, npm  # noqa: E402


class AccurateChecks(TempDirCase):
    def test_command_failure_is_missing_even_with_a_version_banner(self):
        row = {"pin": "9.0.2", "pin_kind": "minimum", "check": {
            "command": [sys.executable, "-c", 'import sys; print("ffmpeg version 9.0.2"); sys.exit(7)'],
            "version": r"ffmpeg version (\d+(?:\.\d+)*)"}}
        self.assertFalse(checks.status(row)["ok"])

    def test_command_without_parseable_version_is_missing(self):
        row = {"pin": "9.0.2", "pin_kind": "minimum", "check": {
            "command": [sys.executable, "-c", 'print("unknown")'],
            "version": r"ffmpeg version (\d+(?:\.\d+)*)"}}
        self.assertFalse(checks.status(row)["ok"])

    def test_ffmpeg_row_requires_companion_ffprobe(self):
        row = {"pin": "9.0.2", "pin_kind": "minimum", "check": {
            "command": [sys.executable, "-c", 'print("ffmpeg version 9.0.2")'],
            "version": r"ffmpeg version (\d+(?:\.\d+)*)",
            "also": {"command": [sys.executable, "-c", "import sys; sys.exit(2)"]}}}
        self.assertFalse(checks.status(row)["ok"])

    def test_missing_whisper_model_is_reported_as_missing(self):
        row = next(r for r in json.loads((SKILL / "catalog" / "tools.json").read_text())["tools"]
                   if r["id"] == "whisper-model")
        with mock.patch.dict("os.environ", {"HOME": str(self.tmp)}):
            self.assertFalse(checks.status(row)["ok"])

    def test_existing_model_with_wrong_checksum_is_missing(self):
        file = self.tmp / "model.onnx"
        file.write_bytes(b"corrupt")
        row = {"check": {"file": str(file)}, "install": {checks.current_os(): {
            "kind": "download", "sha256": "0" * 64}}}
        self.assertFalse(checks.status(row)["ok"])

    def test_importable_python_package_at_wrong_pin_is_missing(self):
        fake_python = self.tmp / "python"
        fake_python.write_text("")
        row = next(r for r in json.loads((SKILL / "catalog" / "tools.json").read_text())["tools"]
                   if r["id"] == "pillow")
        with mock.patch.object(checks, "venv_python", return_value=fake_python), \
                mock.patch.object(checks.subprocess, "run", return_value=subprocess.CompletedProcess(
                    [str(fake_python)], 0, "12.0.0\n3.12\n", "")):
            self.assertFalse(checks.status(row)["ok"])

    def test_python_requirement_extras_are_removed_from_distribution_lookup(self):
        fake_python = self.tmp / "python"
        fake_python.write_text("")
        row = {"check": {"python": "rembg"}, "install": {checks.current_os(): {
            "kind": "pip", "package": "rembg[cpu,cli]==2.1.0"}}}

        def fake_run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0 if argv[-1] == "rembg" else 1,
                                               "2.1.0\n3.14\n", "")

        with mock.patch.object(checks, "venv_python", return_value=fake_python), \
                mock.patch.object(checks.subprocess, "run", side_effect=fake_run):
            self.assertTrue(checks.status(row)["ok"])

    def test_python_slow_first_import_uses_catalog_timeout(self):
        fake_python = self.tmp / "python"
        fake_python.write_text("")
        row = {"check": {"python": "rembg", "timeout": 180},
               "install": {checks.current_os(): {"kind": "pip", "package": "rembg==2.0.87"}}}
        with mock.patch.object(checks, "venv_python", return_value=fake_python), \
                mock.patch.object(checks.subprocess, "run", side_effect=subprocess.TimeoutExpired("python", 180)):
            found = checks.status(row)
        self.assertFalse(found["ok"])
        self.assertIn("180", found["note"])

    def test_windows_whisper_check_finds_private_cli(self):
        private = self.tmp / "AIEditing" / "bin" / "whisper-cpp" / "whisper-cli.exe"
        private.parent.mkdir(parents=True)
        private.write_text("")
        with mock.patch.object(checks, "current_os", return_value="win"), \
                mock.patch.dict("os.environ", {"LOCALAPPDATA": str(self.tmp)}), \
                mock.patch.object(checks.shutil, "which", return_value=None):
            argv = checks.argv_of(["whisper-cli", "--version"])
        self.assertEqual(argv[0], str(private))

    def test_refresh_path_adds_new_package_manager_bins_to_current_process(self):
        folder = self.tmp / "new bin"
        folder.mkdir()
        with mock.patch.dict("os.environ", {"PATH": "/existing"}), \
                mock.patch.object(checks, "_system_path_entries", return_value=[str(folder)]):
            checks.refresh_path()
            self.assertIn(str(folder), checks.os.environ["PATH"].split(checks.os.pathsep))


class FailedInstall(unittest.TestCase):
    def test_failed_external_command_gives_nonzero_cli_exit(self):
        row = {"id": "broken", "pin": "1", "license": "MIT", "install": {checks.current_os(): {
            "kind": "command", "argv": ["false"]}}}
        with mock.patch.object(doctor.catalog, "tools", return_value={"broken": row}), \
                mock.patch.object(installers.subprocess, "run", return_value=subprocess.CompletedProcess(
                    ["false"], 7, "", "failed")):
            self.assertNotEqual(cli.main(["doctor", "--install", "broken", "--yes"]), 0)


class NodeReadiness(TempDirCase):
    def test_hyperframes_package_without_cli_or_browser_is_not_ready(self):
        prefix = self.tmp / "node"
        package = prefix / "node_modules" / "hyperframes"
        package.mkdir(parents=True)
        (package / "package.json").write_text('{"version":"0.9.28"}')
        row = {"id": "hyperframes", "pin": "0.9.28", "pin_kind": "exact"}
        with mock.patch.dict("os.environ", {"AIEDITING_NODE_PREFIX": str(prefix),
                                         "HYPERFRAMES_BROWSER_PATH": str(self.tmp / "missing-browser")}), \
                mock.patch.object(npm, "node_hint", return_value=None):
            self.assertFalse(npm.npm_status("hyperframes", row)["ok"])

    def test_remotion_uses_checked_lock_in_shared_prefix_and_requires_browser(self):
        prefix = self.tmp / "remotion"
        browser = self.tmp / "browser"
        row = next(r for r in json.loads((SKILL / "catalog" / "tools.json").read_text())["tools"]
                   if r["id"] == "remotion")
        calls = []

        def fake_run(argv, env=None, cwd=None):
            calls.append((list(argv), cwd))
            if "ci" in argv:
                pkg = prefix / "node_modules" / "remotion"
                pkg.mkdir(parents=True)
                (pkg / "package.json").write_text('{"version":"4.0.542"}')
                cli_pkg = prefix / "node_modules" / "@remotion" / "cli"
                cli_pkg.mkdir(parents=True)
                (cli_pkg / "package.json").write_text(
                    '{"version":"4.0.542","bin":{"remotion":"remotion-cli.js"}}')
                (cli_pkg / "remotion-cli.js").write_text("")
            if "ensure" in argv:
                browser.write_text("")
            return "поставлено"

        with mock.patch.dict("os.environ", {"AIEDITING_REMOTION_PREFIX": str(prefix),
                                         "OVERLAY_BROWSER": str(browser)}), \
                mock.patch.object(npm, "node_hint", return_value=None):
            self.assertFalse(npm.npm_status("remotion", row)["ok"])
            npm.install_npm(row["install"][checks.current_os()], fake_run)
            self.assertTrue(npm.npm_status("remotion", row)["ok"])
        self.assertEqual(calls[0][0][1], "ci")
        self.assertEqual(calls[1][1], str(prefix))
        self.assertEqual(calls[1][0][-2:], ["browser", "ensure"])
        self.assertEqual((prefix / "package-lock.json").read_bytes(),
                         (SKILL / "overlay-kit" / "template" / "package-lock.json").read_bytes())


class CompleteSetup(TempDirCase):
    def test_requirements_skip_package_unsupported_by_host_python(self):
        rows = [
            {"install": {checks.current_os(): {"kind": "pip", "package": "old==1"}}},
            {"min_python": "3.11", "install": {checks.current_os(): {"kind": "pip", "package": "new==2"}}},
        ]
        with mock.patch.object(doctor.sys, "version_info", (3, 9)):
            self.assertEqual(doctor.requirements(rows), "old==1")

    def test_selected_steps_only_request_their_tools(self):
        from aelib import setup

        self.assertEqual(setup.selected_tools("background"),
                         ["ffmpeg", "numpy", "opencv-python", "onnxruntime", "rvm-model"])
        self.assertEqual(setup.selected_tools("write_srt", "whispercpp"),
                         ["ffmpeg", "whisper-cpp", "whisper-model"])

    def test_check_exits_nonzero_when_a_selected_tool_is_missing(self):
        from aelib import setup

        row = {"id": "missing", "check": {"file": str(self.tmp / "missing")},
               "install": {checks.current_os(): {"kind": "command", "argv": ["false"]}}}
        with mock.patch.object(setup.catalog, "tools", return_value={"missing": row}):
            self.assertNotEqual(cli.main(["setup", "--check"]), 0)

    def test_setup_collects_failure_after_installing_other_tool(self):
        from aelib import setup

        good = self.tmp / "good"
        rows = {"good": {"id": "good", "check": {"file": str(good)}, "install": {checks.current_os(): {
            "kind": "command", "argv": [sys.executable, "-c", "import sys; open(sys.argv[1], 'w').close()", str(good)]}}},
                "bad": {"id": "bad", "check": {"file": str(self.tmp / "bad")}, "install": {checks.current_os(): {
                    "kind": "command", "argv": [sys.executable, "-c", "import sys; sys.exit(5)"]}}}}
        with mock.patch.object(setup.catalog, "tools", return_value=rows):
            with self.assertRaisesRegex(Exception, "bad"):
                setup.ensure_tools(["good", "bad"])
        self.assertTrue(good.is_file())


class PrivateArchiveInstall(TempDirCase):
    def _zip(self, names):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as out:
            for name, data in names.items():
                out.writestr(name, data)
        return buf.getvalue()

    def test_pinned_windows_archive_installs_cli_and_dll_privately(self):
        from aelib import archives

        blob = self._zip({"Release/whisper-cli.exe": b"exe", "Release/whisper.dll": b"dll"})
        dest = self.tmp / "private whisper"
        step = {"save_to": str(dest), "archives": {"x64": {"url": "https://example.test/whisper.zip",
                "sha256": hashlib.sha256(blob).hexdigest()}}}
        with mock.patch.object(archives, "fetch", return_value=iter([blob])):
            archives.install_archive(step, arch="x64")
        self.assertEqual((dest / "whisper-cli.exe").read_bytes(), b"exe")
        self.assertEqual((dest / "whisper.dll").read_bytes(), b"dll")

    def test_zip_slip_is_rejected_before_replacing_existing_install(self):
        from aelib import archives

        blob = self._zip({"Release/whisper-cli.exe": b"new", "../escape.dll": b"bad"})
        dest = self.tmp / "private whisper"
        dest.mkdir()
        (dest / "whisper-cli.exe").write_bytes(b"old")
        step = {"save_to": str(dest), "archives": {"x64": {"url": "https://example.test/whisper.zip",
                "sha256": hashlib.sha256(blob).hexdigest()}}}
        with mock.patch.object(archives, "fetch", return_value=iter([blob])):
            with self.assertRaises(Exception):
                archives.install_archive(step, arch="x64")
        self.assertEqual((dest / "whisper-cli.exe").read_bytes(), b"old")
        self.assertFalse((self.tmp / "escape.dll").exists())


class PrivatePythonBootstrap(TempDirCase):
    def test_paths_prefer_complete_toolkit_venv(self):
        from aelib import paths

        home = self.tmp
        modern = home / ".aiediting" / "toolkit-venv" / "bin" / "python"
        modern.parent.mkdir(parents=True)
        modern.write_text("")
        (modern.parent.parent / "toolkit.ready").write_text("3.14\n")
        with mock.patch.object(paths, "home", return_value=home):
            self.assertEqual(paths.venv_python(), modern)

    def test_paths_ignore_partial_toolkit_venv(self):
        from aelib import paths

        home = self.tmp
        modern = home / ".aiediting" / "toolkit-venv" / "bin" / "python"
        modern.parent.mkdir(parents=True)
        modern.write_text("")
        with mock.patch.object(paths, "home", return_value=home):
            self.assertEqual(paths.venv_dir(), home / ".aiediting" / "venv")

    def test_existing_modern_private_python_does_not_bootstrap(self):
        from aelib import bootstrap

        modern = self.tmp / "python"
        modern.write_text("")
        with mock.patch.object(bootstrap, "private_candidates", return_value=[modern]), \
                mock.patch.object(bootstrap, "python_version", return_value=(3, 14)), \
                mock.patch.object(bootstrap, "_run") as run:
            self.assertEqual(bootstrap.ensure_python(), modern)
        run.assert_not_called()

    def test_private_python_newer_than_supported_is_not_selected(self):
        from aelib import bootstrap

        future = self.tmp / "future"
        modern = self.tmp / "modern"
        for path in (future, modern):
            path.write_text("")
        with mock.patch.object(bootstrap, "private_candidates", return_value=[future, modern]), \
                mock.patch.object(bootstrap, "python_version", side_effect=lambda path: (3, 15) if path == future else (3, 14)), \
                mock.patch.object(bootstrap, "_run") as run:
            self.assertEqual(bootstrap.ensure_python(), modern)
        run.assert_not_called()

    def test_uv_creates_private_venv_with_pip(self):
        from aelib import bootstrap

        dest = self.tmp / "toolkit-venv"
        uv = self.tmp / "bootstrap-venv" / "bin" / "uv"
        uv.parent.mkdir(parents=True)
        uv.write_text("")
        (uv.parent / "python").write_text("")
        calls = []
        with mock.patch.object(bootstrap, "_run", side_effect=lambda argv, env=None: calls.append(argv)):
            bootstrap._bootstrap_with_uv(dest)
        self.assertIn("--seed", calls[-1])
        self.assertIn("3.14", calls[-1])

    def test_failed_new_toolkit_creation_cleans_only_its_partial_folder(self):
        from aelib import bootstrap
        from aelib.session import CliError

        dest = self.tmp / "toolkit-venv"

        def fail(argv, env=None):
            dest.mkdir()
            raise CliError("simulated creation failure")

        with mock.patch.object(bootstrap, "private_candidates", return_value=[]), \
                mock.patch.object(bootstrap, "toolkit_venv_dir", return_value=dest), \
                mock.patch.object(bootstrap, "_external_candidates", return_value=[[sys.executable]]), \
                mock.patch.object(bootstrap, "python_version", return_value=(3, 14)), \
                mock.patch.object(bootstrap, "_run", side_effect=fail):
            with self.assertRaises(CliError):
                bootstrap.ensure_python()
        self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
