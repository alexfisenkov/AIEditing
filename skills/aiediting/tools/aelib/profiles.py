"""Format profiles as data: a fresh one from a preset, dotted edits, taste notes, read and write."""
from __future__ import annotations

import copy
import datetime as dt
import json
from pathlib import Path
from typing import Iterable, Optional

from .paths import PRESETS_DIR

DEFAULT_ASR = {"provider": "whispercpp", "language": "ru", "model": None,
               "base_url": None, "api_key_env": None, "command": None}


def new_profile(fmt: dict, language: str = "ru", output_dir: str = "выпуски") -> dict:
    """fmt is one item of formats.parse_answer; every format, listed or own, starts the same way."""
    preset = json.loads((PRESETS_DIR / (fmt["preset"] + ".json")).read_text(encoding="utf-8"))
    asr = dict(DEFAULT_ASR, language=language)
    return {"format": fmt["word"], "skill_name": fmt["skill"], "language": language, "asr": asr,
            "steps": list(preset["steps"]), "params": copy.deepcopy(preset["params"]),
            "approval": preset.get("approval", "plan"), "design": "design/", "taste": [],
            "output_dir": output_dir}


def _value(text: str):
    try:
        return json.loads(text)
    except ValueError:
        return text


def set_values(profile: dict, assignments: Iterable[str]) -> dict:
    """«params.gap=0.4», «steps=["cut_spans"]», «asr.provider=scribe»; values are JSON when they parse."""
    for item in assignments:
        key, sep, raw = item.partition("=")
        if not sep or not key.strip():
            raise ValueError("Ожидалось ключ=значение, получено {!r}".format(item))
        node, parts = profile, key.strip().split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
            if not isinstance(node, dict):
                raise ValueError("{} — не раздел профиля".format(part))
        node[parts[-1]] = _value(raw.strip())
    return profile


def add_taste(profile: dict, note: str, video: str = "", date: Optional[str] = None) -> dict:
    """Every remark from the trial loop goes into the profile — the taste is kept in the skill."""
    if not note.strip():
        raise ValueError("Пустое замечание не записываю")
    entry = {"date": date or dt.date.today().isoformat(), "video": video, "note": note.strip()}
    profile.setdefault("taste", []).append(entry)
    return profile


def read(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(profile: dict, path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path
