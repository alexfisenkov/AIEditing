"""The one error of `look` and the hint that points a human at `ae.py doctor`."""
from __future__ import annotations

import importlib

DOCTOR = "запустите `python tools/ae.py doctor` — он поставит недостающее по пинам"


class LookError(RuntimeError):
    """Something needed to look at frames is missing or failed; the message is for a human."""


def need(module: str, why: str):
    """Imports an optional package (Pillow, numpy, cv2) or explains how to get it."""
    try:
        return importlib.import_module(module)
    except ImportError:
        raise LookError("Для «{}» нужен пакет {}: {}.".format(why, module, DOCTOR))
