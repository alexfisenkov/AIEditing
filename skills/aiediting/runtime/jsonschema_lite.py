"""The part of JSON Schema (draft-07) the profile uses, with no third-party packages.

Supported: $ref to #/definitions, type, enum, required, properties, additionalProperties,
items, minLength, pattern, minimum, maximum.
"""
from __future__ import annotations

import re
from typing import Any, List

_TYPES = {
    "object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str), "null": lambda v: v is None,
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
}


def _where(path: str) -> str:
    return path or "(корень)"


def _resolve(schema: dict, root: dict) -> dict:
    while "$ref" in schema:
        node: Any = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        schema = node
    return schema


def _object(value: dict, schema: dict, root: dict, path: str, errors: List[str]) -> None:
    for key in schema.get("required", []):
        if key not in value:
            errors.append("{}: нет обязательного поля".format("{}.{}".format(path, key) if path else key))
    props = schema.get("properties", {})
    extra = schema.get("additionalProperties", True)
    for key, item in value.items():
        sub = "{}.{}".format(path, key) if path else key
        if key in props:
            _check(item, props[key], root, sub, errors)
        elif extra is False:
            errors.append("{}: лишнее поле".format(sub))
        elif isinstance(extra, dict):
            _check(item, extra, root, sub, errors)


def _check(value: Any, schema: dict, root: dict, path: str, errors: List[str]) -> None:
    schema = _resolve(schema, root)
    types = schema.get("type")
    if types is not None:
        types = [types] if isinstance(types, str) else types
        if not any(_TYPES[t](value) for t in types):
            errors.append("{}: ожидался тип {}, получено {!r}".format(_where(path), "|".join(types), value))
            return
    if "enum" in schema and value not in schema["enum"]:
        errors.append("{}: {!r} не из списка {}".format(_where(path), value, schema["enum"]))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append("{}: пустая строка".format(_where(path)))
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append("{}: {!r} не подходит под шаблон {}".format(_where(path), value, schema["pattern"]))
    if _TYPES["number"](value):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append("{}: меньше {}".format(_where(path), schema["minimum"]))
        if "maximum" in schema and value > schema["maximum"]:
            errors.append("{}: больше {}".format(_where(path), schema["maximum"]))
    if isinstance(value, dict):
        _object(value, schema, root, path, errors)
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            _check(item, schema["items"], root, "{}[{}]".format(path, i), errors)


def validate(instance: Any, schema: dict) -> List[str]:
    """Human-readable errors (Russian), each starting with the path to the bad value; [] when valid."""
    errors: List[str] = []
    _check(instance, schema, schema, "", errors)
    return errors
