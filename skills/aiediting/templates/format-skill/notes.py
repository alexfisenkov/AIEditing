"""Remarks after a finished video go into its report and the person's own rules, never into the profile.

The profile (steps, design) changes only through AIEditing («доработка»); the report keeps what to
bring there. With a library on this computer the remark is also a personal rule from the next video on.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Optional

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


def remember(issue: Path, text: str, skill_name: str, fmt: Optional[str] = None) -> str:
    """The report, as always, and — when the person has a library — their rules (the format's section
    when `fmt` is given). No library is not an error: the remark stays in the report."""
    said = add_note(issue, text, skill_name)
    from runtime.library import find_library
    from runtime.library.paths import LAYOUT
    from runtime.library.rules import add_rule

    library = find_library()
    if library is None:
        return said
    add_rule(library, text, fmt=fmt, video=Path(issue).name)
    where = "правила формата «{}»".format(fmt) if fmt else "общие правила"
    return ("Записал в отчёт: {} и в ваши {} ({}): со следующего ролика {} монтирует так. "
            "Шаги и дизайн формата меняет AIEditing — доработка {}.".format(
                Path(issue) / REPORT, where, library / LAYOUT["rules"], skill_name, skill_name))
