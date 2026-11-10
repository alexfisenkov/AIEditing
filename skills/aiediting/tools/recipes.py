#!/usr/bin/env python3
"""Run the checked examples behind the parent's tool methods; no workshop or format edits."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for folder in (HERE.parent, HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))


def parser():
    from recipe_lib import analysis, finishing
    ap = argparse.ArgumentParser(description="AIEditing: checked local tool methods")
    sub = ap.add_subparsers(dest="command", required=True)
    analysis.register(sub)
    finishing.register(sub)
    return ap


def main(argv=None):
    opt = parser().parse_args(argv)
    from aelib.paths import venv_python
    private = venv_python()
    if not private.is_file():
        print("Run AIEditing tools/ae.py setup to prepare the private tool environment", file=sys.stderr)
        return 1
    if Path(sys.prefix).resolve() != private.parent.parent.resolve():
        target = str(private.parent.parent.resolve())
        if os.environ.get("AIEDITING_RECIPES_REEXEC") == target:
            print("Private Python did not activate its environment; repair it with AIEditing setup", file=sys.stderr)
            return 1
        return subprocess.call([str(private), "-B", str(Path(__file__).resolve()), *(sys.argv[1:] if argv is None else argv)],
                               env=dict(os.environ, AIEDITING_RECIPES_REEXEC=target))
    from aelib.checks import refresh_path
    from recipe_lib.common import RecipeError
    refresh_path()
    try:
        result = opt.handler(opt)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (RecipeError, OSError, ValueError, ImportError) as exc:
        print("Recipe failed: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
