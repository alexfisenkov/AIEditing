"""Node packages in AIEditing's own npm prefix (HyperFrames): is the pin here, and installing it.

Never global. A row with `lock` (a folder of catalog/ with package.json + a checked package-lock.json)
is installed reproducibly: both files into the prefix, then `npm ci --ignore-scripts` — every
dependency at the locked version and hash, no install scripts run. Node itself is the person's
(doctor --install node). Telemetry, update checks and self-installs of the package stay off.
"""
from __future__ import annotations

import json
import shutil
from typing import Callable, List, Optional

from runtime.render.hf_ready import node_major
from runtime.render.hyperframes import NODE_MAJOR, QUIET, node_prefix

from .paths import CATALOG_DIR

NPM_FLAGS = ["--no-fund", "--no-audit", "--ignore-scripts"]


def npm_status(package: str, row: dict) -> dict:
    meta = node_prefix() / "node_modules" / package / "package.json"
    try:
        version = json.loads(meta.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return {"ok": False, "version": None, "note": "не установлено в {}".format(node_prefix())}
    if row.get("pin_kind") == "exact" and version != row["pin"]:
        return {"ok": False, "version": version, "note": "версия {} вместо пина {}".format(version, row["pin"])}
    return {"ok": True, "version": version, "note": "версия {} в {}".format(version, node_prefix())}


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


def _npm_argv(step: dict) -> List[str]:
    """`npm ci` from the catalog's lockfile (copied into the prefix first), else a pinned `npm install`."""
    prefix, npm = node_prefix(), shutil.which("npm") or "npm"
    prefix.mkdir(parents=True, exist_ok=True)
    if not step.get("lock"):
        return [npm, "install", "--prefix", str(prefix), "--save-exact"] + NPM_FLAGS + [step["package"]]
    for name in ("package.json", "package-lock.json"):
        shutil.copyfile(str(CATALOG_DIR / step["lock"] / name), str(prefix / name))
    return [npm, "ci", "--prefix", str(prefix)] + NPM_FLAGS


def install_npm(step: dict, run: Callable) -> str:
    """run(argv, env) -> «поставлено…» | «не получилось…» (installers._run). `after`: the package's own
    first-run command (HyperFrames: `browser ensure` finds or fetches its Chrome on its standard path)."""
    hint = node_hint()
    if hint:
        return hint
    done = run(_npm_argv(step), QUIET)
    if done.startswith("не получилось") or not step.get("after"):
        return done
    name = step["package"].rsplit("@", 1)[0]
    return done + "\n" + run([shutil.which("node") or "node", str(_bin(name))] + list(step["after"]), QUIET)
