"""`ae.py library …` — the person's library, through the very functions a format skill's `run.py library` uses."""
from __future__ import annotations


def cmd_library(opt):
    from runtime.library.cli import run

    return run(list(opt.args))  # LibraryError is a ValueError: ae.py prints it as one line, code 1
