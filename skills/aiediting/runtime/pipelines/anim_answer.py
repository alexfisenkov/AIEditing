"""The person's answer to `animations`, read leniently: points as a list or one line with commas,
`start` in seconds or as 0:01:23, an end no later than 15 s after the start."""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from .points import MAX_ITEMS

LONGEST = 15.0
_CLOCK = re.compile(r"^\s*(?:(\d+):)?(\d+):(\d+(?:[.,]\d+)?)\s*$")


def seconds(value) -> Optional[float]:
    """83.5, "83,5", "1:23", "0:01:23.5" → seconds; None when it is none of these."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value or "").strip().replace(",", ".")
    m = _CLOCK.match(text)
    if m:
        return int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    try:
        return float(text)
    except ValueError:
        return None


def points(value) -> List[str]:
    """A list of points, or one line with commas; empty ones dropped, at most MAX_ITEMS."""
    raw = value.split(",") if isinstance(value, str) else list(value or [])
    return [str(p).strip() for p in raw if str(p).strip()][:MAX_ITEMS]


def span(item: Dict, default_length: float):
    """(start, end) or (None, why): a start it cannot read gives a reason in Russian."""
    start = seconds(item.get("start"))
    if start is None or start < 0:
        return None, "не понял start «{}» — нужны секунды (83.5) или время 0:01:23".format(item.get("start"))
    end = seconds(item.get("end"))
    end = end if end is not None and end > start + 1.0 else start + default_length
    return (start, min(end, start + LONGEST)), None
