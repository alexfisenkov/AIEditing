"""Python packages of the catalog install together on every supported Python: pins chosen by version.

The expected sets were resolved and installed together (pip, then `pip check`) in clean venvs on
Python 3.9, 3.11, 3.12 and 3.14 on 29.10.2026; CI repeats the install (ci.yml, job «pins»).
"""
import json
import os
import subprocess
import sys
import unittest

from _support import ROOT, SKILL

sys.path.insert(0, str(SKILL / "tools"))

EXPECTED = {
    (3, 9): {"Pillow==11.3.0", "numpy==2.0.2", "opencv-python==5.0.0.93", "onnxruntime==1.19.2",
             "scenedetect==0.6.7.1", "soundfile==0.13.1", "librosa==0.11.0", "pysubs2==1.8.0"},
    (3, 11): {"Pillow==12.3.0", "numpy==2.2.6", "opencv-python==5.0.0.93", "onnxruntime==1.31.1",
              "scenedetect==0.7.3", "soundfile==0.14.0", "librosa==0.11.0", "pysubs2==1.8.0",
              "rembg==2.0.87"},
    (3, 12): {"Pillow==13.0.0", "numpy==2.5.4", "opencv-python==5.0.0.93", "onnxruntime==1.31.1",
              "scenedetect==0.7.3", "soundfile==0.14.0", "librosa==1.0.0", "pysubs2==1.9.1",
              "rembg==2.0.87"},
    (3, 14): {"Pillow==13.0.0", "numpy==2.5.4", "opencv-python==5.0.0.93", "onnxruntime==1.31.1",
              "scenedetect==0.7.3", "soundfile==0.14.0", "librosa==1.0.0", "pysubs2==1.9.1",
              "rembg==2.0.87"},
}


def pip_rows():
    from aelib.catalog import tools

    return [r for r in tools().values() if any(s.get("kind") == "pip" for s in r["install"].values())]


class PinsByPython(unittest.TestCase):
    def test_one_pin_per_package_for_each_python(self):
        from aelib.installers import pip_package

        for version, expected in EXPECTED.items():
            for os_key in ("mac", "win"):
                got = {pip_package(r["install"][os_key], version) for r in pip_rows()
                       if not r.get("min_python") or version >= tuple(map(int, r["min_python"].split(".")))}
                self.assertEqual(got, expected, "Python {}.{} on {}".format(version[0], version[1], os_key))

    def test_doctor_prints_the_set_for_this_python(self):
        proc = subprocess.run([sys.executable, str(SKILL / "tools" / "ae.py"), "doctor", "--requirements"],
                              capture_output=True, text=True, encoding="utf-8",
                              env=dict(os.environ, AIEDITING_IN_VENV="1"))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        mine = max(v for v in EXPECTED if v <= sys.version_info[:2])
        self.assertEqual(set(proc.stdout.split()), EXPECTED[mine])

    def test_ci_installs_the_set_on_oldest_and_newest_python(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("doctor --requirements", ci)
        self.assertIn("pip check", ci)
        for version in ('"3.9"', '"3.12"'):
            self.assertIn(version, ci)

    def test_readmes_describe_modern_toolkit_and_older_host_bootstrap(self):
        for name in ("README.md", "README.ru.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("3.9", text, name)
            self.assertIn("numpy 2.5.4", text, name)
            self.assertRegex(text, r"OpenCV\s+5\.0\.0\.93")
            self.assertIn("Python 3.12–3.14", text, name)
            self.assertIn("setup --check", text, name)


if __name__ == "__main__":
    unittest.main()
