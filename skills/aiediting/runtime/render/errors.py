"""The one error of `render` and the way to an optional package (Pillow)."""
from __future__ import annotations

import importlib


class RenderError(RuntimeError):
    """The design layer cannot be drawn; the message is for a human."""


def need(module: str):
    try:
        return importlib.import_module(module)
    except ImportError:
        raise RenderError("Для дизайн-слоя нужен пакет Pillow: запустите `python tools/ae.py doctor` — "
                          "он поставит недостающее по пинам.")
