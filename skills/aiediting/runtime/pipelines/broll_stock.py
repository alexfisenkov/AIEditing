"""Free stock for a place no frame of the person's own fits: only their keys, and a service without a key is not asked twice."""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from ..library import stock
from ..library.stock import StockError
from .broll_place import MIN_LEN

ORDER = ("pexels", "pixabay")
_WORD = re.compile(r"\w+", re.UNICODE)


def query_of(text: str) -> str:
    """The longer words of a phrase: a search line, not a sentence."""
    words = [w for w in _WORD.findall(text) if len(w) >= 4 and not w.isdigit()]
    return " ".join(words[:6]) or text[:60]


class Stock:
    def __init__(self, ctx, library):
        self.ctx, self.library = ctx, library
        self.dead: Dict[str, str] = {}   # service -> why it cannot be used this run
        self.hits: Dict[tuple, dict] = {}

    def _tell(self) -> None:
        if len(self.dead) == len(ORDER):  # one service short of a key is no news while the other works
            for message in self.dead.values():
                self.ctx.note("Сток: {}".format(message))

    def find(self, text: str) -> Optional[dict]:
        """The first horizontal clip of three seconds or more from a service that answers; None if there is none."""
        for provider in ORDER:
            if provider in self.dead:
                continue
            try:
                found: List[dict] = stock.search(query_of(text), provider, "landscape", 5)
            except StockError as exc:
                self.dead[provider] = str(exc)
                continue
            for hit in found:
                if hit["dur"] >= MIN_LEN and hit["width"] >= hit["height"]:
                    self.hits[(hit["provider"], hit["id"])] = hit
                    return hit
        self._tell()
        return None

    def fetch(self, provider: str, ident: str) -> Optional[dict]:
        """The row of the inventory for a hit the person accepted, after its file is in the library; None if it failed."""
        hit = self.hits.get((provider, ident))
        if hit is None:
            return None
        try:
            return stock.download(hit, self.library)
        except StockError as exc:
            self.ctx.note("Сток: {}".format(exc))
            return None
