"""A pinned file fetched by `doctor --install`: into `<name>.part`, the sha256 checked, then renamed into place."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from urllib import request

from .session import CliError

TIMEOUT = 60


def fetch(url: str) -> bytes:
    """The whole body of `url`. Tests replace this; nothing else in the tools touches the network."""
    req = request.Request(url, headers={"User-Agent": "aiediting-doctor"})
    with request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310 - https URL from our own catalog
        return resp.read()


def _target(step: dict) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(step["save_to"])))


def download(step: dict) -> str:
    """Installs one `download` step; raises CliError («!! …») when it cannot, leaving no half-file behind."""
    dest = _target(step)
    part = dest.with_name(dest.name + ".part")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        body = fetch(step["url"])
        got = hashlib.sha256(body).hexdigest()
        if got != step["sha256"].lower():
            raise CliError("!! Сумма sha256 файла с {} не совпала (ждали {}…, пришло {}…): файл не сохранён, "
                           "ничего не поставлено.".format(step["url"], step["sha256"][:12], got[:12]))
        part.write_bytes(body)
        os.replace(str(part), str(dest))
    except OSError as e:
        raise CliError("!! Не получилось скачать {}: {}. Проверьте сеть и повторите.".format(step["url"], e))
    finally:
        if part.exists():
            part.unlink()
    return "поставлено: {}".format(dest)
