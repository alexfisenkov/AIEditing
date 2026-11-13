"""Free stock video (Pexels, Pixabay) by the person's own key: a search, and a file in `стоки/` with a row of the inventory.

Queries are cached in the library, files are fetched one at a time on a person's say, never in bulk. The key is read by
variable name (`runtime/asr/secrets.py`) and is never printed. The service is named only in the row's `source`.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from urllib import parse

from ..asr.contract import AsrError
from ..asr.secrets import read_key
from . import inventory, store
from .paths import LAYOUT, LibraryError, find_library

KEYS = {"pexels": "PEXELS_API_KEY", "pixabay": "PIXABAY_API_KEY"}
URLS = {"pexels": "https://api.pexels.com/v1/videos/search", "pixabay": "https://pixabay.com/api/videos/"}
MAX_BYTES = 400 * 1024 * 1024
CACHE = "стоки-запросы.json"
FRESH_DAYS = 30
WIDE = 1920  # the size a video of ours is cut in


class StockError(LibraryError):
    """The stock service cannot be used now; the message says why, without the key."""


WHAT = "Сервис стоков"


def _get(url: str, headers: Dict[str, str], secret: str = "") -> dict:
    """JSON of the service through `services.web`: a redirect to another host goes there without the key."""
    from ..services import web

    try:
        return web.get_json(url, headers, WHAT, secret)
    except web.ServiceError as exc:
        raise StockError(str(exc))


def _kind(width: int, height: int) -> str:
    return "гор" if width > height else ("верт" if width < height else "кв")


def _pick(files: List[dict], landscape: bool) -> Optional[dict]:
    """The file nearest to full-HD width; a tall one only when tall ones were asked for."""
    fit = [f for f in files if f.get("link") and (f["width"] >= f["height"]) == landscape]
    return min(fit, key=lambda f: abs(f["width"] - WIDE)) if fit else None


def _hit(provider: str, ident, page: str, dur, file: dict, query: str) -> dict:
    return {"provider": provider, "id": str(ident), "url": page or "", "width": file["width"],
            "height": file["height"], "dur": float(dur or 0), "link": file["link"], "query": query}


def _pexels(data: dict, query: str, landscape: bool) -> List[dict]:
    found = []
    for v in data.get("videos") or []:
        files = [{"width": int(f.get("width") or 0), "height": int(f.get("height") or 0), "link": f.get("link")}
                 for f in v.get("video_files") or [] if "mp4" in str(f.get("file_type") or "mp4")]
        best = _pick(files, landscape)
        if best:
            found.append(_hit("pexels", v.get("id"), v.get("url"), v.get("duration"), best, query))
    return found


def _pixabay(data: dict, query: str, landscape: bool) -> List[dict]:
    found = []
    for h in data.get("hits") or []:
        files = [{"width": int(s.get("width") or 0), "height": int(s.get("height") or 0), "link": s.get("url")}
                 for s in (h.get("videos") or {}).values() if isinstance(s, dict)]
        best = _pick(files, landscape)
        if best:
            found.append(_hit("pixabay", h.get("id"), h.get("pageURL"), h.get("duration"), best, query))
    return found


def _cache_file() -> Optional[Path]:
    lib = find_library()
    return lib / LAYOUT["inventory"] / CACHE if lib is not None else None


def _cached(name: str) -> Optional[List[dict]]:
    path = _cache_file()
    entry = store.read_json(path, {}).get(name) if path else None
    try:
        age = (dt.date.today() - dt.date.fromisoformat(entry["day"])).days if entry else None
    except (KeyError, ValueError):
        return None
    return entry["hits"] if entry and age is not None and age <= FRESH_DAYS else None


def _remember(name: str, hits: List[dict]) -> None:
    path = _cache_file()
    if path is not None:
        data = store.read_json(path, {})
        data[name] = {"day": dt.date.today().isoformat(), "hits": hits}
        store.write_json(path, data)


def search(query: str, provider: str = "pexels", orientation: str = "landscape", per_page: int = 5,
           key_file: Optional[str] = None) -> List[dict]:
    """[{provider, id, url, width, height, dur, link, query}]; StockError without a key, a link or an answer."""
    query = " ".join(str(query or "").split())[:100]
    if provider not in KEYS:
        raise StockError("Нет такого стока: {}; есть: {}".format(provider, ", ".join(KEYS)))
    if not query:
        raise StockError("Пустой запрос к стоку")
    per_page = max(3, int(per_page))
    name = "|".join((provider, orientation, str(per_page), query))
    hits = _cached(name)
    if hits is not None:
        return hits
    try:
        key = read_key(KEYS[provider], key_file)
    except AsrError as exc:
        raise StockError(str(exc))
    if provider == "pexels":
        url = URLS[provider] + "?" + parse.urlencode({"query": query, "orientation": orientation,
                                                      "size": "medium", "per_page": per_page})
        headers = {"Authorization": key}
    else:
        url = URLS[provider] + "?" + parse.urlencode({"key": key, "q": query, "per_page": per_page})
        headers = {}
    data = _get(url, dict(headers, **{"User-Agent": "aiediting"}), key)
    read = _pexels if provider == "pexels" else _pixabay
    hits = read(data, query, orientation == "landscape")[:per_page]
    _remember(name, hits)
    return hits


def _save(link: str, path: Path) -> None:
    if not link.startswith(("http://", "https://")):
        raise StockError("Ссылка на файл стока не похожа на адрес")
    from ..services import web

    try:  # in pieces, through a temporary name: the file is never held in memory, a broken one never stays
        web.download(link, {"User-Agent": "aiediting"}, path, WHAT, limit=MAX_BYTES)
    except web.ServiceError as exc:
        raise StockError(str(exc))


def download(hit: dict, library: Path) -> dict:
    """The hit's file into `стоки/` (once) and its row into the inventory; returns the row."""
    if not all(hit.get(k) for k in ("provider", "id", "link")):
        raise StockError("В описании стока нет ссылки на файл")
    ident = hashlib.sha1("{}:{}".format(hit["provider"], hit["id"]).encode("utf-8")).hexdigest()[:10]
    rel = "{}/сток-{}.mp4".format(LAYOUT["stock"], ident)
    path = Path(library) / rel
    if not path.is_file():
        _save(str(hit["link"]), path)
    query = str(hit.get("query") or "")
    row = dict(inventory.ROW, f=rel, kind="стоки", what=query, type="видео", dur=hit.get("dur") or None,
               orient=_kind(int(hit.get("width") or 0), int(hit.get("height") or 0)),
               tags=[w for w in query.split() if len(w) >= 3], phrases=[query] if query else [],
               quality="сток", source="{} {}".format(hit["provider"], hit.get("url") or hit["id"]).strip())
    inventory.describe(library, "стоки", [row])
    return row
