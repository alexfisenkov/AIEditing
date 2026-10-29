"""Loading and checking a format profile against `profile.schema.json`."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Union

from .asr.keyfile import NOT_A_PATH, looks_like_path
from .jsonschema_lite import validate

SCHEMA_NAME = "profile.schema.json"


def default_schema_path() -> Path:
    """`schema/` next to `runtime/` (the AIEditing skill); a format skill may keep it inside `runtime/`."""
    here = Path(__file__).resolve().parent
    for candidate in (here.parent / "schema" / SCHEMA_NAME, here / SCHEMA_NAME):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Не найдена схема профиля {}".format(SCHEMA_NAME))


def load_schema(schema: Union[dict, str, Path, None] = None) -> dict:
    if isinstance(schema, dict):
        return schema
    path = Path(schema) if schema else default_schema_path()
    return json.loads(path.read_text(encoding="utf-8"))


def check_profile(profile: dict, schema: Union[dict, str, Path, None] = None) -> List[str]:
    """[] when the profile is valid, otherwise one Russian message per problem.

    `asr.key_file` must look like a path; checked here, not by a schema pattern, so a key pasted there
    by mistake is never repeated in a message.
    """
    errors = validate(profile, load_schema(schema))
    asr = profile.get("asr") if isinstance(profile, dict) else None
    key_file = asr.get("key_file") if isinstance(asr, dict) else None
    if isinstance(key_file, str) and key_file and not looks_like_path(key_file):
        errors.append(NOT_A_PATH)
    return errors


def load_profile(path: Union[str, Path], schema: Optional[Union[dict, str, Path]] = None) -> dict:
    """Reads profile.json and raises ValueError listing every problem."""
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = check_profile(profile, schema)
    if errors:
        raise ValueError("Профиль {} не прошёл проверку:\n- {}".format(path, "\n- ".join(errors)))
    return profile
