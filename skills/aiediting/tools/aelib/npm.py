"""Node packages in AIEditing's own npm prefix (HyperFrames): is the pin here, and installing it.

Never global: `npm install --prefix <node_prefix()> --save-exact <name>@<pin>`; Node itself is the
person's (doctor --install node). Telemetry, update checks and self-installs of the package stay off.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Callable, Optional

from runtime.render.hyperframes import NODE_MAJOR, QUIET, node_prefix


def npm_status(package: str, row: dict) -> dict:
    meta = node_prefix() / "node_modules" / package / "package.json"
    try:
        version = json.loads(meta.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return {"ok": False, "version": None, "note": "не установлено в {}".format(node_prefix())}
    if row.get("pin_kind") == "exact" and version != row["pin"]:
        return {"ok": False, "version": version, "note": "версия {} вместо пина {}".format(version, row["pin"])}
    return {"ok": True, "version": version, "note": "версия {} в {}".format(version, node_prefix())}


def node_major() -> Optional[int]:
    node = shutil.which("node")
    if not node:
        return None
    try:
        out = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    found = re.findall(r"\d+", out or "")
    return int(found[0]) if found else None


def node_hint() -> Optional[str]:
    """None when Node (NODE_MAJOR or newer) and npm are here; otherwise what to do, in Russian."""
    major = node_major()
    if major is None or not shutil.which("npm"):
        return ("Нет Node.js {n}+ — он нужен для HyperFrames. Поставьте его: `python tools/ae.py doctor --install "
                "node --yes` (macOS — brew, Windows — winget) или установщиком с nodejs.org, затем повторите "
                "эту команду. Ничего не поставлено.").format(n=NODE_MAJOR)
    if major < NODE_MAJOR:
        return ("Node.js {} старше нужного {}: обновите его (nodejs.org, brew upgrade node, winget upgrade "
                "OpenJS.NodeJS.LTS) и повторите. Ничего не поставлено.").format(major, NODE_MAJOR)
    return None


def _bin(name: str):
    meta = json.loads((node_prefix() / "node_modules" / name / "package.json").read_text(encoding="utf-8"))
    entry = meta.get("bin", {})
    entry = entry.get(name) if isinstance(entry, dict) else entry
    return node_prefix() / "node_modules" / name / entry


def install_npm(step: dict, run: Callable) -> str:
    """run(argv, env) -> «поставлено…» | «не получилось…» (installers._run). `after`: the package's own
    first-run command (HyperFrames: `browser ensure` finds or fetches its Chrome on its standard path)."""
    hint = node_hint()
    if hint:
        return hint
    prefix = node_prefix()
    prefix.mkdir(parents=True, exist_ok=True)
    env = QUIET
    done = run([shutil.which("npm") or "npm", "install", "--prefix", str(prefix), "--save-exact", "--no-fund",
                "--no-audit", step["package"]], env)
    if done.startswith("не получилось") or not step.get("after"):
        return done
    name = step["package"].rsplit("@", 1)[0]
    return done + "\n" + run([shutil.which("node") or "node", str(_bin(name))] + list(step["after"]), env)
