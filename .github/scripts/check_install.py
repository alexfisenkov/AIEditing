"""After `npx skills add … -g`: the installed copy exists, imports, and has the version of this checkout."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = [Path.home() / ".agents" / "skills" / "aiediting", Path.home() / ".claude" / "skills" / "aiediting"]


def expected_version() -> str:
    text = (ROOT / "skills" / "aiediting" / "runtime" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__ = "([^"]+)"', text).group(1)


def main() -> int:
    installed = next((p for p in CANDIDATES if (p / "SKILL.md").is_file()), None)
    if installed is None:
        print("Скилл не найден ни в одном из мест: " + ", ".join(map(str, CANDIDATES)))
        return 1
    probe = ("import sys; sys.path.insert(0, sys.argv[1]); import runtime, runtime.asr, runtime.media; "
             "print(runtime.__version__)")
    proc = subprocess.run([sys.executable, "-I", "-c", probe, str(installed)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
    if proc.returncode != 0:
        print("Поставленная копия не импортируется:\n" + proc.stderr)
        return 1
    got, want = proc.stdout.strip(), expected_version()
    print("Поставлено в {}: версия {} (ожидалась {})".format(installed, got, want))
    return 0 if got == want else 1


if __name__ == "__main__":
    sys.exit(main())
