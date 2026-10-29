"""The page: a copy of the template in the workshop folder, with the state written inside it.

Same trick as AISpa (MIT, see NOTICE.md): a snapshot between /*STATE-BEGIN*/ and /*STATE-END*/ makes the
page show something even from file:// or data:, while http keeps polling state.js for live updates.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "dashboard.html"
PAGE = "dashboard.html"
BEGIN, END = "/*STATE-BEGIN*/", "/*STATE-END*/"


def install_page(work: Path) -> Path:
    """dashboard.html and index.html (a copy, not a symlink — works on Windows without rights)."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    for name in (PAGE, "index.html"):
        shutil.copy2(str(TEMPLATE), str(work / name))
    return work / PAGE


def write_snapshot(work: Path, state: dict) -> str:
    payload = "window.STATE=" + json.dumps(state, ensure_ascii=False).replace("</", "<\\/") + ";"
    for name in (PAGE, "index.html"):
        path = Path(work) / name
        try:
            page = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return "страницы нет — ae.py init положит её заново"
        i, j = page.find(BEGIN), page.find(END)
        if i < 0 or j < 0:
            return "страница без маркеров снимка — ae.py init положит её заново"
        new = page[: i + len(BEGIN)] + payload + page[j:]
        if new != page:
            tmp = path.with_name(name + ".tmp")
            tmp.write_text(new, encoding="utf-8")
            os.replace(str(tmp), str(path))
    return "дашборд обновлён"
