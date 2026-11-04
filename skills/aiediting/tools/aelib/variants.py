"""The paths of a format: ways to edit the same thing. Each is a row in catalog/formats.json and a preset, nothing else.

A format with paths is shown on the person's video path by path, and is not built until one is chosen.
"""
from __future__ import annotations

import copy
import json
from typing import List, Optional

from .formats import format_word, load_formats
from .paths import PRESETS_DIR

OWN = "own:"  # a way the catalog does not have yet: its steps and parameters are set by hand in the draft


def catalog_format(word: str) -> Optional[dict]:
    """The row of a format in the catalog by any of its names; None for a word that is not there."""
    key = format_word(word or "")
    return next((f for f in load_formats() if key in (f["id"], format_word(f["word"]), format_word(f["title"]))), None)


def of_profile(profile: dict) -> List[dict]:
    """The paths of the format this draft is of, or is narrowed from (`like`); [] for a format with one way or a word of its own."""
    fmt = catalog_format(profile.get("like") or profile.get("format") or "")
    return list(fmt.get("variants") or []) if fmt else []


def by_id(profile: dict, wanted: str) -> dict:
    if str(wanted).startswith(OWN) and profile.get("variant") == wanted:  # the way set by hand in this draft, for a probe of it
        return {"id": wanted, "title": str(wanted)[len(OWN):], "hint": "", "short": {"params": {"clips": [1, 1]}}}
    rows = of_profile(profile)
    for row in rows:
        if row["id"] == wanted:
            return row
    if not rows:
        raise ValueError("У формата «{}» один путь, выбирать нечего".format(profile.get("format")))
    raise ValueError("Пути {} нет; есть: {}".format(wanted, ", ".join(r["id"] for r in rows)))


def named_by_preset(fmt: dict, preset: Optional[str]) -> Optional[str]:
    """`ae.py formats … --preset P` that names one of the format's paths has chosen it."""
    return next((r["id"] for r in fmt.get("variants") or [] if r["preset"] == preset), None)


def unchosen(profile: dict) -> Optional[str]:
    """What stops the build of a format whose path nobody chose; None when there is nothing to choose."""
    rows, mark = of_profile(profile), str(profile.get("variant") or "")
    if not rows or mark.startswith(OWN) or mark in [r["id"] for r in rows]:
        return None
    return ("Формат «{}» идёт одним из путей ({}), а путь не выбран: сначала короткая проба каждого на видео человека и "
            "его выбор, потом ae.py variant {} <путь>".format(profile.get("format"), ", ".join(r["id"] for r in rows),
                                                             profile.get("skill_name")))


def _preset(name: str) -> dict:
    return json.loads((PRESETS_DIR / (name + ".json")).read_text(encoding="utf-8"))


def _current_params(profile: dict) -> dict:
    rows, mark = of_profile(profile), profile.get("variant")
    if mark and str(mark).startswith(OWN):
        return {}
    row = next((r for r in rows if r["id"] == mark), rows[0] if rows else None)
    return _preset(row["preset"])["params"] if row else {}


def switched(profile: dict, row: dict, short: bool = False) -> dict:
    """The draft on another path: that preset's steps and parameters, under what the person has answered so far
    (whatever differs from the preset the draft stands on). `short`: a probe of the path, without what `short` leaves out."""
    out = copy.deepcopy(profile)
    if "preset" in row:  # a way set by hand stands on what the draft already has
        old, new = _current_params(profile), _preset(row["preset"])
        answers = {k: v for k, v in (profile.get("params") or {}).items() if k not in old or old[k] != v}
        out["steps"], out["params"] = list(new["steps"]), dict(copy.deepcopy(new["params"]), **copy.deepcopy(answers))
    if short:
        probe = row.get("short") or {}
        out["steps"] = [s for s in out["steps"] if s not in probe.get("without", [])]
        out["params"].update(copy.deepcopy(probe.get("params") or {}))
    return out
