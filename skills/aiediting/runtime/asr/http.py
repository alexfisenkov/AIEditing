"""A multipart POST with the standard library. Errors carry the HTTP status, never the key."""
from __future__ import annotations

import json
import mimetypes
import uuid
from pathlib import Path
from typing import Dict, List, Tuple
from urllib import error, request

from .contract import AsrError

TIMEOUT = 900  # seconds; long recordings upload and transcribe slowly


def _body(fields: List[Tuple[str, str]], file_field: str, path: Path) -> Tuple[bytes, str]:
    boundary = "aiediting-" + uuid.uuid4().hex
    parts = []
    for name, value in fields:
        parts.append('--{}\r\nContent-Disposition: form-data; name="{}"\r\n\r\n{}\r\n'.format(
            boundary, name, value).encode("utf-8"))
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    parts.append('--{}\r\nContent-Disposition: form-data; name="{}"; filename="{}"\r\n'
                 'Content-Type: {}\r\n\r\n'.format(boundary, file_field, path.name, ctype).encode("utf-8"))
    parts.append(path.read_bytes())
    parts.append("\r\n--{}--\r\n".format(boundary).encode("utf-8"))
    return b"".join(parts), "multipart/form-data; boundary=" + boundary


def post_file(url: str, fields: List[Tuple[str, str]], file_field: str, path: Path,
              headers: Dict[str, str], secret: str = "") -> dict:
    """POSTs `fields` plus the file and returns the JSON reply."""
    body, ctype = _body(fields, file_field, Path(path))
    req = request.Request(url, data=body, method="POST", headers=dict(headers, **{"Content-Type": ctype}))
    try:
        with request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
    except error.HTTPError as exc:
        with exc:
            detail = exc.read()[:300].decode("utf-8", "replace")
        if secret:
            detail = detail.replace(secret, "***")
        hint = " (ключ не принят — проверьте его в файле .env)" if exc.code in (401, 403) else ""
        raise AsrError("Сервис распознавания ответил {}{}: {}".format(exc.code, hint, detail))
    except (error.URLError, OSError) as exc:
        reason = str(getattr(exc, "reason", exc))
        raise AsrError("Нет связи с сервисом распознавания {}: {}".format(url.split("?")[0], reason))
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError:
        raise AsrError("Сервис распознавания вернул не JSON.")
