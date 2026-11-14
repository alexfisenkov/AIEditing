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
    python ae.py design-example <skill>  ·  samples <skill> [--frame F] [--element E]  ·  choose <skill> <element> <n>
    python ae.py variant <skill> [<id>] [--own WORD] [--keep]       the paths of a format: list them, choose one
    python ae.py trial <skill> <video> [--start S --duration D] [--answers F] [--variant ID]   --variant: a short probe of that path
    python ae.py show <skill> <video> [--variant ID]                a clip made by the kit, on the dashboard
    python ae.py hear <skill> <video>                               what the draft's recogniser hears in a finished clip
    python ae.py verdict <skill> yes|no [--note N]                  the person's word on the trial clip
    python ae.py kit <skill> own|renew                              a kit changed after its build: keep it as the format's own, or renew
    python ae.py build-skill <profile.json> <dest> [--replace]
    python ae.py install-skill <built folder>  ·  list-skills [--json]
    python ae.py backup-skill <name>  ·  restore-skill <name> [--backup ID]
    python ae.py doctor [--steps a,b] [--asr P] [--install ID] [--yes]
    python ae.py setup [--check] [--steps a,b] [--asr P]            install / check the local toolkit (of these steps only)
    python ae.py capabilities [--json]                              the tools and FFmpeg filters on this machine
    python ae.py intro [set <key>=<answer> … | apply [<skill>]]     what the person told at the start: kept, laid into the draft
                                                                    and the library; keys: computer videos camera program blog
                                                                    materials services liked disliked forbid
    python ae.py library <command> …                                the person's library: where, set, status, scan, sheet, describe,
                                                                    find, rule, rules, forbid, stock
    python ae.py voice-try <skill> [<video>] [--start S --duration D] [--check]   Auphonic presets on a minute of theirs; --check: the key
    python ae.py background <video> <out> --mode remove|solid|image|video|blur|chromakey [--value V]   a person apart from the background
    python ae.py image-cutout <image> <out.png>                      a still without its background
    python ae.py finish --result R  ·  stop-server  ·  python ae.py  (bare: re-raise the server)
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
    private = venv_python()
    if (os.environ.get("AIEDITING_IN_VENV") or not private.is_file()
            or Path(sys.prefix).resolve() == private.parent.parent.resolve()):
        return False
    env = dict(os.environ, AIEDITING_IN_VENV="1")
    sys.exit(subprocess.call([str(private), str(Path(__file__).resolve()), *sys.argv[1:]], env=env))


def _flag(argv, name):
    key = "--" + name
    for i, arg in enumerate(argv):
        if arg.startswith(key + "="):
            return arg.split("=", 1)[1]
        if arg == key and i + 1 < len(argv):
            return argv[i + 1]
    return None


def _prepare_python_for_requested_tools() -> None:
    """Before command imports: a repair that needs modern Python gets a private interpreter first."""
    argv = sys.argv[1:]
    if not argv or (argv[0] == "setup" and "--check" in argv):
        return
    from aelib.cli import parser

    parser().parse_args(argv)
    from aelib import catalog
    from aelib.checks import current_os
    from aelib.setup import selected_tools

    if argv[0] == "setup":
        ids = selected_tools(_flag(argv, "steps"), _flag(argv, "asr"))
    elif argv[0] == "background":
        ids = [] if _flag(argv, "mode") == "chromakey" else ["numpy", "onnxruntime"]
    elif argv[0] == "image-cutout":
        ids = ["rembg", "onnxruntime"]
    elif argv[0] == "doctor" and _flag(argv, "install") and "--yes" in argv:
        ids = [_flag(argv, "install")]
    else:
        return
    rows = catalog.tools()
    if any(rows.get(name, {}).get("install", {}).get(current_os(), {}).get("kind") == "pip" for name in ids):
        from aelib.bootstrap import ensure_python

        ensure_python()


if __name__ == "__main__":
    from aelib.checks import refresh_path

    refresh_path()
    from aelib.session import CliError

    try:
        _prepare_python_for_requested_tools()
    except (CliError, ValueError, OSError) as exc:
        print("ошибка: {}".format(exc))
        sys.exit(1)
    _in_private_env()
    from aelib.cli import main

    sys.exit(main(sys.argv[1:]))
