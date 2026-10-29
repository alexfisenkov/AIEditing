"""The issue folder: `<output_dir>/<YYYY-MM-DD>-<topic>/`, the only place a format skill writes to."""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Optional

_BAD = re.compile(r"[/\\:*?\"<>|\s]+")


def topic_of(text: str) -> str:
    topic = _BAD.sub("-", text.strip().lower()).strip("-.")
    return topic[:60] or "выпуск"


def issue_folder(profile: dict, src: Path, topic: Optional[str] = None,
                 today: Optional[dt.date] = None) -> Path:
    """Same date and topic → same folder, so a run resumed after a decision lands in one place."""
    base = Path(profile["output_dir"]).expanduser()
    if not base.is_absolute():
        base = Path.cwd() / base
    day = (today or dt.date.today()).isoformat()
    return (base / "{}-{}".format(day, topic_of(topic or Path(src).stem))).resolve()
