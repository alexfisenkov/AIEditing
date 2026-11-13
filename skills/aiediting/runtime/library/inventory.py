"""The inventory: one JSON line per file, per kind. Code measures new files; the agent describes them.

Progress (`опись/прогресс.json`) keeps, per kind, the folders scanned and the measured files still
waiting for a description, so a batch interrupted by a limit continues where it stopped.
"""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from . import store
from .meta import is_media, measure
from .paths import KINDS, LAYOUT, LibraryError
from .sheet import sheet

__all__ = ["ROW", "scan", "pending", "describe", "load", "summary", "file_of", "sheet"]

ROW = {"f": "", "kind": "", "date": None, "where": "", "who": [], "what": "", "type": "фото", "orient": None,
       "dur": None, "best": [], "quality": "", "tags": [], "phrases": [], "never": False, "plan": None,
       "motion": None, "log": False, "source": None}
_LISTS = ("who", "best", "tags", "phrases")


def _kind_file(library: Path, kind: str) -> Path:
    if kind not in KINDS:
        raise LibraryError("Нет такого вида описи: {}; есть: {}".format(kind, ", ".join(KINDS)))
    return Path(library) / LAYOUT["inventory"] / KINDS[kind]


def _progress(library: Path) -> dict:
    data = store.read_json(Path(library) / LAYOUT["progress"], {})
    data.setdefault("kinds", {})
    return data


def _save_progress(library: Path, data: dict) -> None:
    store.write_json(Path(library) / LAYOUT["progress"], data)


def _of(data: dict, kind: str) -> dict:
    return data["kinds"].setdefault(kind, {"roots": [], "pending": [], "described": 0, "updated": None})


def _rel(library: Path, path: Path) -> str:
    try:
        return path.relative_to(Path(library).resolve()).as_posix()
    except ValueError:
        return str(path)


def file_of(library: Path, row: dict) -> Path:
    """The file a row names: relative to the library or absolute."""
    path = Path(row["f"])
    return path if path.is_absolute() else Path(library) / path


def _media(roots: List[Path]) -> Iterator[Path]:
    for root in roots:
        if root.is_file():
            if is_media(root):
                yield root
            continue
        for folder, subs, names in os.walk(str(root)):
            subs[:] = sorted(s for s in subs if not s.startswith("."))
            for name in sorted(names):
                if not name.startswith(".") and is_media(Path(name)):
                    yield Path(folder) / name


def scan(library: Path, kind: str, roots: List[Path]) -> List[dict]:
    """Files under `roots` (or the folders scanned before) not yet described, measured, without a description."""
    known = {r.get("f") for r in store.read_jsonl(_kind_file(library, kind))}
    data = _progress(library)
    state = _of(data, kind)
    roots = [Path(r).expanduser().resolve() for r in roots] or [Path(r) for r in state["roots"]]
    waiting = {r["f"]: r for r in state["pending"]}
    found = []
    for path in _media([r for r in roots if r.exists()]):
        f = _rel(library, path)
        if f not in known:
            found.append(waiting.get(f) or dict(ROW, f=f, kind=kind, **measure(path)))
    state["roots"] = sorted(set(state["roots"]) | {str(r) for r in roots})
    fresh = {r["f"] for r in found}
    state["pending"] = found + [r for r in state["pending"] if r["f"] not in fresh and r["f"] not in known]
    state["updated"] = dt.date.today().isoformat()
    _save_progress(library, data)
    return found


def pending(library: Path, kind: str) -> List[dict]:
    known = {r.get("f") for r in store.read_jsonl(_kind_file(library, kind))}
    return [r for r in _of(_progress(library), kind)["pending"] if r["f"] not in known]


def _clean(row: dict, kind: str, measured: Optional[dict]) -> dict:
    if not isinstance(row, dict) or not str(row.get("f") or "").strip():
        raise LibraryError("В строке описи нет поля f (путь к файлу): {}".format(str(row)[:120]))
    out = dict(ROW, kind=kind)
    out.update(measured or {})
    out.update({k: v for k, v in row.items() if k in ROW and k != "kind"})
    for key in _LISTS:
        if not isinstance(out[key], list):
            out[key] = [out[key]] if out[key] else []
    out["never"], out["log"] = bool(out["never"]), bool(out["log"])
    return out


def describe(library: Path, kind: str, rows: List[dict]) -> int:
    """Writes the agent's rows (by `f`: new ones appended, known ones replaced); returns how many."""
    path = _kind_file(library, kind)
    data = _progress(library)
    state = _of(data, kind)
    measured = {r["f"]: r for r in state["pending"]}
    clean = [_clean(r, kind, measured.get(str(r.get("f")) if isinstance(r, dict) else None)) for r in rows]
    clean = list({r["f"]: r for r in clean}.values())  # one row per file, the last one wins
    saved = store.read_jsonl(path)
    index = {r.get("f"): i for i, r in enumerate(saved)}
    if any(r["f"] in index for r in clean):
        for row in clean:
            if row["f"] in index:
                saved[index[row["f"]]] = row
            else:
                index[row["f"]] = len(saved)
                saved.append(row)
        store.write_jsonl(path, saved)
    else:
        store.append_jsonl(path, clean)
    done = {r["f"] for r in clean}
    state["pending"] = [r for r in state["pending"] if r["f"] not in done]
    state["described"] = len(store.read_jsonl(path))
    state["updated"] = dt.date.today().isoformat()
    _save_progress(library, data)
    return len(clean)


def load(library: Path, kinds: Optional[List[str]] = None) -> List[dict]:
    rows = []
    for kind in kinds or list(KINDS):
        rows += [dict(r, kind=kind) for r in store.read_jsonl(_kind_file(library, kind))]
    return rows


def summary(library: Path) -> Dict[str, dict]:
    """{kind: {"described", "pending", "roots"}} for the status line."""
    data = _progress(library)
    return {kind: {"described": len(store.read_jsonl(_kind_file(library, kind))),
                   "pending": len(pending(library, kind)), "roots": _of(data, kind)["roots"]} for kind in KINDS}
