"""The product names no outside author and no outside material: only its own owner (README, LICENSE).

The words are stored reversed so that this file does not hold them itself. Searched: every text file
the repository would ship (git: tracked and not ignored; without git: all but the service folders).
"""
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from _support import ROOT, TempDirCase

SKIP_DIRS = {".git", ".engineering", ".aispa-work", ".критики", "node_modules", "__pycache__", ".pytest_cache"}
REVERSED = ["вохерб", "voherb", "vohkerb", "voherbazaf", "ажатном яицутитснок", "noitutitsnoc"]
WORDS = [w[::-1] for w in REVERSED]
# A person's home folder with a name in it: whoever's, it is a personal path.
HOME_PATH = re.compile(r"(?<![:\w])/(?:Users|home)/(?!Test/|you/|user/|name/)[^/\s\"'`|\\<>{}*()\[\]]+/")
BINARY = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".ttf", ".otf", ".mp4", ".mov",
          ".wav", ".mp3", ".m4a", ".zip", ".onnx", ".pdf"}


def shipped(root: Path):
    """Files of the repository as git would ship them; a plain walk when there is no git."""
    if (root / ".git").exists() and shutil.which("git"):
        proc = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                              capture_output=True)
        if proc.returncode == 0:
            names = [n for n in proc.stdout.decode("utf-8", "replace").split("\0") if n]
            return [root / n for n in names if not (set(Path(n).parts) & SKIP_DIRS)]
    found = []
    for folder, subs, files in os.walk(str(root)):
        subs[:] = [s for s in subs if s not in SKIP_DIRS]
        found += [Path(folder) / f for f in files]
    return found


def offenders(files, root: Path):
    """[(file, what)] for each forbidden word or personal path in a file's name or text."""
    bad = []
    for path in files:
        if not path.is_file() or path.suffix.lower() in BINARY:
            continue
        name = path.relative_to(root).as_posix() if root in path.parents else path.name
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        low = (name + "\n" + text).casefold()
        bad += [(name, word) for word in WORDS if word in low]
        bad += [(name, m.group(0)) for m in HOME_PATH.finditer(text)]
    return bad


class TheCheckItself(TempDirCase):
    def test_a_planted_name_or_personal_path_is_caught(self):
        (self.tmp / "a.md").write_text("По мотивам " + WORDS[0].title() + "а", encoding="utf-8")
        (self.tmp / "b.py").write_text('SRC = "/' + 'Users/somebody/Documents/x"\n', encoding="utf-8")
        (self.tmp / "c.md").write_text("Default: C:/Users/Test/AppData; ~/.aiediting/library.json\n", encoding="utf-8")
        found = offenders(shipped(self.tmp), self.tmp)
        self.assertEqual(sorted(name for name, _ in found), ["a.md", "b.py"])


class NoReferenceNames(unittest.TestCase):
    def test_no_outside_author_or_material_or_personal_path_in_the_repository(self):
        files = shipped(ROOT)
        self.assertGreater(len(files), 100)
        self.assertEqual(offenders(files, ROOT), [])


if __name__ == "__main__":
    unittest.main()
