"""catalog/tools.json is complete and open; `ae.py doctor` shows what is missing and installs only after «да»."""
import json
import os
import subprocess
import sys
import unittest

from _support import SKILL, TempDirCase

AE = SKILL / "tools" / "ae.py"
CATALOG = json.loads((SKILL / "catalog" / "tools.json").read_text(encoding="utf-8"))
STEPS = json.loads((SKILL / "catalog" / "steps.json").read_text(encoding="utf-8"))


class Catalog(unittest.TestCase):
    def test_every_row_has_license_os_pin_and_weight(self):
        for row in CATALOG["tools"]:
            for key in ("id", "what", "license", "os", "pin", "install", "heavy", "skills_section"):
                self.assertIn(key, row, row.get("id"))
            self.assertTrue(set(row["os"]) <= {"mac", "win"} and row["os"], row["id"])
            self.assertIsInstance(row["heavy"], bool)
            self.assertTrue(str(row["pin"]).strip(), row["id"])

    def test_no_kinetic_and_openmontage_only_as_a_link(self):
        text = json.dumps(CATALOG, ensure_ascii=False).lower()
        self.assertNotIn("kinetic", text)
        self.assertNotIn("openmontage", [r["id"] for r in CATALOG["tools"]])
        self.assertEqual([l["id"] for l in CATALOG["links"]], ["openmontage"])

    def test_closed_licences_carry_a_warning(self):
        remotion = next(r for r in CATALOG["tools"] if r["id"] == "remotion")
        self.assertIn("warning", remotion)
        self.assertTrue(remotion["heavy"])

    def test_steps_name_only_catalog_tools(self):
        ids = {r["id"] for r in CATALOG["tools"]}
        for name, step in STEPS["steps"].items():
            self.assertTrue(set(step["tools"]) <= ids, name)
        for tools in STEPS["asr_tools"].values():
            self.assertTrue(set(tools) <= ids)


class Doctor(TempDirCase):
    def setUp(self):
        super().setUp()
        self.marker = self.tmp / "поставлено.txt"
        os_key = "mac" if sys.platform == "darwin" else "win"
        row = {"id": "fake", "what": "проба", "license": "MIT", "os": [os_key], "pin": "1.0", "heavy": False,
               "skills_section": "проба", "check": {"file": str(self.marker)},
               "install": {os_key: {"kind": "command", "argv": ["{python}", "-c",
                                    "import sys; open(sys.argv[1], 'w').write('ok')", str(self.marker)]}}}
        (self.tmp / "cat").mkdir()
        (self.tmp / "cat" / "tools.json").write_text(json.dumps({"tools": [row], "links": []}), encoding="utf-8")
        self.env = dict(os.environ, HOME=str(self.tmp), USERPROFILE=str(self.tmp))

    def doctor(self, *args):
        proc = subprocess.run([sys.executable, str(AE), "doctor", "--catalog", str(self.tmp / "cat"), *args],
                              capture_output=True, text=True, encoding="utf-8", env=self.env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout

    def test_missing_is_shown_and_nothing_installs_without_yes(self):
        self.assertRegex(self.doctor(), r"fake\s+нет")
        out = self.doctor("--install", "fake")
        self.assertIn("нужно «да»", out)
        self.assertFalse(self.marker.exists())

    def test_installs_by_the_catalog_after_yes(self):
        self.doctor("--install", "fake", "--yes")
        self.assertTrue(self.marker.is_file())
        self.assertRegex(self.doctor(), r"fake\s+есть")


if __name__ == "__main__":
    unittest.main()
