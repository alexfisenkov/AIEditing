#!/usr/bin/env python3
"""AIEditing workshop — one call per event, for the agent. The person never runs it.

    python ae.py init --mode new|refine [--title T] [--fresh] [--no-questions]   dashboard + server on 127.0.0.1
    python ae.py no-questions                                       the person asked for no more questions
    python ae.py stage <id> [done|skip] [--note N]                  start|formats|sources|interview|design|trial|build
    python ae.py ask <kind> --note N  ·  answered [--note N]        the workshop waits for the person
    python ae.py formats "эфир, урок, подкаст" [--preset P] [--like F]   parse the answer, draft one profile per format
                                                                    (--like: an own word narrowed from a catalog format, with its paths)
    python ae.py profile set|taste|check|open <skill> …             edit the draft profile in the workshop folder
                                                                    (taste --replace PART: instead of that line)
    python ae.py frames <video> [--n 6]  ·  layout <source-id>      frames and layout on the dashboard
    python ae.py design-example <skill>  ·  samples <skill> [--frame F]
    python ae.py variant <skill> [<id>] [--own WORD] [--keep]       the paths of a format: list them, choose one
    python ae.py trial <skill> <video> [--start S --duration D] [--answers F] [--variant ID]   --variant: a short probe of that path
    python ae.py show <skill> <video> [--variant ID]                a clip made by the kit, on the dashboard
    python ae.py hear <skill> <video>                               what the draft's recogniser hears in a finished clip
    python ae.py kit <skill> own|renew                              a kit changed after its build: keep it as the format's own, or renew
    python ae.py build-skill <profile.json> <dest> [--replace]
    python ae.py install-skill <built folder>  ·  list-skills [--json]
    python ae.py backup-skill <name>  ·  restore-skill <name> [--backup ID]
    python ae.py doctor [--steps a,b] [--asr P] [--install ID] [--yes]
    python ae.py finish --result R  ·  python ae.py                  (bare: re-raise the server)
"""
import os
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
for _p in (str(TOOLS.parent), str(TOOLS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from aelib.paths import venv_python  # noqa: E402


def _in_private_env() -> bool:
    """Pillow/OpenCV live in AIEditing's own venv (doctor puts them there): run inside it when it exists."""
    if os.environ.get("AIEDITING_IN_VENV") or sys.prefix != sys.base_prefix or not venv_python().is_file():
        return False
    env = dict(os.environ, AIEDITING_IN_VENV="1")
    sys.exit(subprocess.call([str(venv_python()), str(Path(__file__).resolve()), *sys.argv[1:]], env=env))


if __name__ == "__main__":
    _in_private_env()
    from aelib.cli import main

    sys.exit(main(sys.argv[1:]))
