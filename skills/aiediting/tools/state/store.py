"""state.js of the workshop: read, write atomically, stamp the time, keep a short event feed.

Pattern taken from AISpa's ap.py (MIT, see NOTICE.md): `window.STATE =` + JSON, written through a
.tmp file and os.replace, `rev` grows on every write so the page knows to repaint.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Optional

STATE = "state.js"
LOG_KEPT = 300


def now() -> str:
    return dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def read(work: Path) -> Optional[dict]:
    try:
        raw = (Path(work) / STATE).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    first = raw.split("\n", 1)[0]
    body = raw.split("=", 1)[1] if "=" in first else raw
    try:
        return json.loads(body.strip().rstrip(";"))
    except ValueError as e:
        raise ValueError("state.js не разбирается ({}) — начните заново: ae.py init".format(e))


def save(work: Path, state: dict) -> None:
    state["rev"] = (state.get("rev") or 0) + 1
    state["updatedAt"] = now()
    path = Path(work) / STATE
    tmp = path.with_name(STATE + ".tmp")
    tmp.write_text("window.STATE =\n" + json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(path))


def log(state: dict, event: str, **kw) -> None:
    entry = {"t": now(), "k": event}
    entry.update({k: v for k, v in kw.items() if v not in (None, "", [])})
    state.setdefault("log", []).append(entry)
    del state["log"][:-LOG_KEPT]


def rel(work: Path, path: Path) -> str:
    """A path the page can load: relative to the workshop folder, with forward slashes."""
    return Path(path).resolve().relative_to(Path(work).resolve()).as_posix()
