"""File names in speech: «agents.md», and «agents MD» said as two words."""
from __future__ import annotations

import re
from typing import List

from .points import MAX_ITEMS, content, split_and

EXT = {"md", "py", "js", "ts", "json", "txt", "yaml", "yml", "html", "css", "csv", "pdf", "sh", "toml", "env"}
FILE = re.compile(r"^[\w-]+\.[a-z][a-z0-9]{0,4}$", re.I)  # agents.md, run.py, tokens.json

def file_items(pieces: List[List[str]], trigger) -> List[str]:
    """Every file name said, in order; after «файлы …» also short bare names (spec, plan)."""
    out, seen = [], False
    for piece in pieces:
        for part in split_and(piece):
            if trigger and any(trigger.match(w) for w in part):
                seen, part = True, part[max(k for k, w in enumerate(part) if trigger.match(w)) + 1:]
            names = [w for w in part if FILE.match(w)]
            bare = content(part)
            out += names if names else ([" ".join(bare)] if seen and bare and len(bare) <= 2 else [])
    unique = list(dict.fromkeys(out))
    return unique[:MAX_ITEMS]
