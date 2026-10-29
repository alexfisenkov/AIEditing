"""Remarks after a finished video go into its report, never into the profile.

The profile changes only through AIEditing («доработка»); the report keeps what to bring there.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

REPORT = "отчёт.md"
SECTION = "## Замечания для доработки"


def add_note(issue: Path, text: str, skill_name: str) -> str:
    """Appends one remark under the section and returns the line to say to the person."""
    text = " ".join(text.split())
    if not text:
        raise ValueError("Пустое замечание не записываю")
    report = Path(issue) / REPORT
    body = report.read_text(encoding="utf-8") if report.is_file() else "# Отчёт\n"
    line = "- {}: {}".format(dt.date.today().isoformat(), text)
    if SECTION in body:
        head, _, tail = body.partition(SECTION)
        rest = tail.lstrip("\n").split("\n## ", 1)
        before = rest[0].rstrip("\n")
        notes = (before + "\n" if before else "") + line + "\n"
        body = head + SECTION + "\n\n" + notes + ("\n## " + rest[1] if len(rest) > 1 else "")
    else:
        body = body.rstrip("\n") + "\n\n" + SECTION + "\n\n" + line + "\n"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(body, encoding="utf-8")
    return ("Записал в отчёт: {}. Чтобы {} монтировал так всегда, запустите AIEditing — "
            "доработка {}.".format(report, skill_name, skill_name))
