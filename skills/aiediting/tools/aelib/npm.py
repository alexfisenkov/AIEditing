"""Node packages in AIEditing's own npm prefix (HyperFrames): is the pin here, and installing it.

Never global. A row with `lock` (a folder of catalog/ with package.json + a checked package-lock.json)
is installed reproducibly: both files into the prefix, then `npm ci --ignore-scripts` — every
dependency at the locked version and hash, no install scripts run. Node itself is the person's
(doctor --install node). Telemetry, update checks and self-installs of the package stay off.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
from pathlib import Path
from typing import Callable, List, Optional

from runtime.render.hf_ready import node_major
from runtime.render.hyperframes import NODE_MAJOR, QUIET, node_prefix

from .paths import CATALOG_DIR

NPM_FLAGS = ["--no-fund", "--no-audit", "--ignore-scripts"]


def npm_status(package: str, row: dict) -> dict:
    prefix = prefix_for(package)
    meta = prefix / "node_modules" / package / "package.json"
    try:
        version = json.loads(meta.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return {"ok": False, "version": None, "note": "не установлено в {}".format(prefix)}
    if row.get("pin_kind") == "exact" and version != row["pin"]:
        return {"ok": False, "version": version, "note": "версия {} вместо пина {}".format(version, row["pin"])}
    hint = node_hint()
    if hint:
        return {"ok": False, "version": version, "note": hint}
    from . import catalog
    from .checks import status

    node = catalog.tools().get("node")
    if node and status(node)["ok"] is not True:
        return {"ok": False, "version": version, "note": "нужна версия Node.js из каталога"}
    try:
        entry = _bin(package)
    except (OSError, ValueError, TypeError, KeyError):
        return {"ok": False, "version": version, "note": "нет CLI пакета"}
    if not entry.is_file():
        return {"ok": False, "version": version, "note": "нет CLI {}".format(entry)}
    if package == "remotion":
        cli_meta = prefix / "node_modules" / "@remotion" / "cli" / "package.json"
        if json.loads(cli_meta.read_text(encoding="utf-8")).get("version") != row["pin"]:
            return {"ok": False, "version": version, "note": "версия CLI Remotion отличается от пина"}
    browser = _browser(package)
    if browser is None or not browser.is_file():
        return {"ok": False, "version": version, "note": "нет браузера рендера"}
    return {"ok": True, "version": version, "note": "версия {} и браузер в {}".format(version, prefix)}


def prefix_for(package: str) -> Path:
    if package == "remotion":
        return Path(os.environ["AIEDITING_REMOTION_PREFIX"]).expanduser() if os.environ.get("AIEDITING_REMOTION_PREFIX") else Path.home() / ".aiediting" / "remotion"
    return node_prefix()


def _browser(package: str) -> Optional[Path]:
    if package == "hyperframes":
        from runtime.render.hf_ready import browser

        return browser()
    if os.environ.get("OVERLAY_BROWSER"):
        return Path(os.environ["OVERLAY_BROWSER"])
    machine = platform.machine().lower()
    system = platform.system().lower()
    target = ("mac-arm64" if machine == "arm64" else "mac-x64") if system == "darwin" else (
        "win64" if system == "windows" else "linux-arm64" if machine == "arm64" else "linux64")
    folder = prefix_for(package) / "node_modules" / ".remotion" / "chrome-headless-shell" / target / (
        "chrome-headless-shell-" + target)
    candidates = ("headless_shell", "chrome-headless-shell.exe", "chrome-headless-shell")
    return next((folder / name for name in candidates if (folder / name).is_file()), None)


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
    pkg = "@remotion/cli" if name == "remotion" else name
    meta = json.loads((prefix_for(name) / "node_modules" / pkg / "package.json").read_text(encoding="utf-8"))
    entry = meta.get("bin", {})
    entry = entry.get(name) if isinstance(entry, dict) else entry
    if not entry:
        raise ValueError("package has no CLI")
    return prefix_for(name) / "node_modules" / pkg / entry


def _npm_argv(step: dict) -> List[str]:
    """`npm ci` from the catalog's lockfile (copied into the prefix first), else a pinned `npm install`."""
    package = step["package"].rsplit("@", 1)[0]
    prefix, npm = prefix_for(package), shutil.which("npm") or "npm"
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
    return done + "\n" + run([shutil.which("node") or "node", str(_bin(name))] + list(step["after"]), QUIET,
                             cwd=str(prefix_for(name)))
