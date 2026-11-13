"""The tool catalog and the step vocabulary: which runtime packages and tools a set of steps needs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .paths import CATALOG_DIR

# media imports render.overlay at its top, so render always goes along; look only when a step needs it.
# library: every format skill reads and adds to the person's library without the workshop.
BASE_RUNTIME = ["asr", "library", "media", "pipelines", "render"]
OPTIONAL_RUNTIME = ["look"]


def _load(name: str, base: Optional[Path] = None) -> dict:
    return json.loads(((base or CATALOG_DIR) / name).read_text(encoding="utf-8"))


def tools(base: Optional[Path] = None) -> Dict[str, dict]:
    rows = list(_load("tools.json", base)["tools"])
    extra = (base or CATALOG_DIR) / "extra-tools.json"
    if extra.is_file():
        rows += json.loads(extra.read_text(encoding="utf-8"))["tools"]
    found = {}
    for row in rows:
        if row["id"] in found:
            raise ValueError("Повторяется id инструмента: " + row["id"])
        found[row["id"]] = row
    return found


def steps(base: Optional[Path] = None) -> dict:
    return _load("steps.json", base)


def check_steps(chosen: List[str], base: Optional[Path] = None) -> List[str]:
    """Names that are not in the step vocabulary — one Russian message each."""
    known = steps(base)["steps"]
    return ["Неизвестный шаг {!r}; известны: {}".format(s, ", ".join(sorted(known)))
            for s in chosen if s not in known]


def needs(chosen: List[str], asr_provider: Optional[str], base: Optional[Path] = None,
          verify_provider: Optional[str] = None) -> dict:
    """{"runtime": [...], "tools": [...]} for exactly the chosen steps and recognisers, in catalog order."""
    data = steps(base)
    runtime, wanted = set(BASE_RUNTIME), set()
    for name in chosen:
        step = data["steps"][name]
        runtime.update(step.get("runtime", []))
        wanted.update(step.get("tools", []))
    for provider in (asr_provider, verify_provider):
        if provider and provider not in data["asr_tools"]:
            raise ValueError("Неизвестный распознаватель {!r}; доступны: {}".format(provider, ", ".join(data["asr_tools"])))
        wanted.update(data["asr_tools"].get(provider or "", []))
    order = list(tools(base))
    return {"runtime": sorted(runtime), "tools": [t for t in order if t in wanted]}
