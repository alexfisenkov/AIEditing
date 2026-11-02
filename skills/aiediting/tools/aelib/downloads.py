"""A pinned file fetched by `doctor --install`: into `<name>.part`, the sha256 checked, then renamed into place.

A model is gigabytes, so it goes to the disk piece by piece and never sits in memory.
"""
from __future__ import annotations

import hashlib
import http.client
import os
from pathlib import Path
from typing import Iterator
from urllib import request

from .session import CliError

TIMEOUT = 60
PIECE = 1024 * 1024
SAY_EVERY = 256  # pieces between progress lines


def fetch(url: str) -> Iterator[bytes]:
    """The body of `url`, piece by piece. Tests replace this; nothing else in the tools touches the network."""
    req = request.Request(url, headers={"User-Agent": "aiediting-doctor"})
    with request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310 - https URL from our own catalog
        for piece in iter(lambda: resp.read(PIECE), b""):
            yield piece


def _target(step: dict) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(step["save_to"])))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for piece in iter(lambda: f.read(PIECE), b""):
            digest.update(piece)
    return digest.hexdigest()


def download(step: dict) -> str:
    """Installs one `download` step; raises CliError («!! …») when it cannot, leaving no half-file behind."""
    dest = _target(step)
    part = dest.with_name(dest.name + ".part")
    want = step["sha256"].lower()
    try:
        if dest.is_file() and _sha256(dest) == want:
            return "уже на месте: {}".format(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        with part.open("wb") as out:
            for n, piece in enumerate(fetch(step["url"]), 1):
                digest.update(piece)
                out.write(piece)
                if n % SAY_EVERY == 0:
                    print("скачано {} МБ".format(n), flush=True)
        got = digest.hexdigest()
        if got != want:
            raise CliError("!! Сумма sha256 файла с {} не совпала (ждали {}…, пришло {}…): файл не сохранён, "
                           "ничего не поставлено.".format(step["url"], want[:12], got[:12]))
        os.replace(str(part), str(dest))
    except (OSError, http.client.HTTPException) as e:
        raise CliError("!! Не получилось скачать {}: {}. Проверьте сеть и повторите.".format(step["url"], e))
    finally:
        if part.exists():
            part.unlink()
    return "поставлено: {}".format(dest)
