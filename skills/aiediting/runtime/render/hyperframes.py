"""HyperFrames (Apache-2.0), pinned: where AIEditing keeps it and how one composition becomes a clip.

Installed by `ae.py doctor --install hyperframes --yes` into node_prefix(); run as `node <cli>` (no
shell, no .cmd shims) with telemetry, update checks and self-installs switched off, and its project
history kept inside the run folder of the issue (never ~/.cache/hyperframes/history).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from .errors import RenderError

PIN = "0.9.28"
NODE_MAJOR = 22  # Minimum runtime; setup installs the current supported LTS.
QUIET = {"HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1", "HYPERFRAMES_NO_UPDATE_CHECK": "1",
         "HYPERFRAMES_NO_AUTO_INSTALL": "1", "HYPERFRAMES_NO_OPTIONAL_INSTALL": "1"}
TIMEOUT = 900
HINT = "поставьте: `python tools/ae.py doctor --install {} --yes` в AIEditing"


def node_prefix() -> Path:
    """npm prefix of AIEditing's own Node packages; AIEDITING_NODE_PREFIX overrides."""
    if os.environ.get("AIEDITING_NODE_PREFIX"):
        return Path(os.environ["AIEDITING_NODE_PREFIX"]).expanduser()
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "AIEditing" / "node"
    return Path.home() / ".aiediting" / "node"


def cli() -> Path:
    """The CLI entry (AIEDITING_HYPERFRAMES may point at another hyperframes.mjs)."""
    own = os.environ.get("AIEDITING_HYPERFRAMES")
    return Path(own).expanduser() if own else node_prefix() / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"


def missing() -> Optional[str]:
    """Why HyperFrames cannot start here, in Russian; None when it can (cheap: no process is run)."""
    if not shutil.which("node"):
        return "нет Node.js {}+ в PATH ({})".format(NODE_MAJOR, HINT.format("node"))
    if not cli().is_file():
        return "нет HyperFrames {} ({})".format(PIN, HINT.format("hyperframes"))
    return None


def env(history: Optional[Path] = None) -> dict:
    """Quiet settings; the project history into `history`; our ffmpeg/ffprobe when AIEditing has its own."""
    out = dict(os.environ, **QUIET)
    if history is not None:
        out["HYPERFRAMES_HISTORY_ROOT"] = str(history)
    for ours, theirs in (("AIEDITING_FFMPEG", "HYPERFRAMES_FFMPEG_PATH"), ("AIEDITING_FFPROBE", "HYPERFRAMES_FFPROBE_PATH")):
        if os.environ.get(ours):
            out[theirs] = os.environ[ours]
    return out


def command(args: List[str]) -> List[str]:
    return [shutil.which("node") or "node", str(cli())] + [str(a) for a in args]


def render_mov(project: Path, out: Path, fps: int = 30) -> Path:
    """index.html of `project` → `out`, ProRes 4444 with alpha (MOV keeps rounded corners and see-through).

    The history HyperFrames keeps of a project goes next to it (inside the run folder, removed with it).
    """
    why = missing()
    if why:
        raise RenderError("Анимацию не отрисовать: " + why)
    project = Path(project)
    argv = command(["render", project, "--format", "mov", "-o", out, "--fps", fps, "--quiet"])
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env=env(project.parent / "hf-history"), timeout=TIMEOUT, cwd=str(project))
    except (OSError, subprocess.SubprocessError) as exc:
        raise RenderError("HyperFrames не запускается: {}".format(exc))
    if proc.returncode != 0 or not Path(out).is_file():
        tail = "\n".join(((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()[-6:])
        raise RenderError("HyperFrames не отрисовал {} (код {}):\n{}".format(project.name, proc.returncode, tail))
    return Path(out)
