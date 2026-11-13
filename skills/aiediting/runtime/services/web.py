"""HTTP for the services with the standard library: a multipart POST, a GET of JSON, a download. Errors carry the
service's name and HTTP status, never the key."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib import error, parse, request

from ..asr.http import _body

TIMEOUT = 900
MAX_BYTES = 2 * 1024 * 1024 * 1024


class ServiceError(RuntimeError):
    """A service cannot do what was asked now; the message says why and what to do, without the key."""


def _host(url: str) -> str:
    return (parse.urlsplit(url).hostname or "").lower()


class _KeyStaysHome(request.HTTPRedirectHandler):
    """urllib carries every header over a redirect; the key must not leave the host it was sent to."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and _host(newurl) != _host(req.full_url):
            for name in [k for k in list(new.headers) + list(new.unredirected_hdrs) if k.lower() in SECRET_HEADERS]:
                new.remove_header(name)
        return new


SECRET_HEADERS = {"authorization", "x-api-key", "xi-api-key", "cookie"}
_OPENER = request.build_opener(_KeyStaysHome)


def _open(req: request.Request, what: str, secret: str):
    try:
        return _OPENER.open(req, timeout=TIMEOUT)
    except error.HTTPError as exc:
        with exc:
            detail = exc.read()[:300].decode("utf-8", "replace")
        detail = detail.replace(secret, "***") if secret else detail
        hint = " (ключ не принят — проверьте его в файле .env)" if exc.code in (401, 403) else (
            " (лимит запросов исчерпан, попробуйте позже)" if exc.code == 429 else "")
        raise ServiceError("{} ответил {}{}: {}".format(what, exc.code, hint, detail))
    except (error.URLError, OSError) as exc:
        raise ServiceError("Нет связи с {} ({}): {}".format(what, req.full_url.split("?")[0], getattr(exc, "reason", exc)))


def _json(raw: bytes, what: str) -> Dict:
    try:
        data = json.loads(raw.decode("utf-8"))
    except ValueError:
        raise ServiceError("{} вернул не JSON".format(what))
    return data if isinstance(data, dict) else {}


def post_form(url: str, fields: List[Tuple[str, str]], file_field: str, path: Path, headers: Dict[str, str],
              what: str, secret: str = "") -> Dict:
    body, ctype = _body(fields, file_field, Path(path))
    req = request.Request(url, data=body, method="POST", headers=dict(headers, **{"Content-Type": ctype}))
    with _open(req, what, secret) as resp:
        return _json(resp.read(), what)


def get_json(url: str, headers: Dict[str, str], what: str, secret: str = "") -> Dict:
    with _open(request.Request(url, headers=headers), what, secret) as resp:
        return _json(resp.read(), what)


def download(url: str, headers: Dict[str, str], out: Path, what: str, secret: str = "", limit: Optional[int] = None) -> Path:
    """The body into `out` through a temporary name: a broken download never leaves a half file under the real one."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".part")
    size = 0
    try:
        with _open(request.Request(url, headers=headers), what, secret) as resp, open(str(tmp), "wb") as fh:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                size += len(chunk)
                if size > (limit or MAX_BYTES):
                    raise ServiceError("{}: файл результата слишком большой".format(what))
                fh.write(chunk)
        if size == 0:
            raise ServiceError("{}: файл результата пустой".format(what))
        os.replace(str(tmp), str(out))
    finally:
        if tmp.exists():
            tmp.unlink()
    return out
