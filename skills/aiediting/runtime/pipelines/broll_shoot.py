"""`досъёмка.md`: the places that found no frame, as time — phrase — what to shoot, how long, which way up."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .timeline import to_out

NAME = "досъёмка.md"


def _cell(text) -> str:
    return " ".join(str(text or "").replace("|", "/").split())


def write(ctx, rate: float = 1.0) -> Optional[Path]:
    """The file next to the video when there is a place to shoot; nothing is written (or removed) otherwise."""
    from .report import stamp

    if not ctx.shoot_list:
        return None
    lines = ["# Досъёмка", "",
             "Здесь под слова не нашлось кадра. Снятое положите в папку «футажи» библиотеки: при следующем запуске оно "
             "встанет на место. Не снимете — место останется стоком или графикой.", "",
             "| Время | Фраза | Что снять | Секунд | Кадр |", "|---|---|---|---|---|"]
    for row in sorted(ctx.shoot_list, key=lambda r: r["start"]):
        at = to_out(row["start"], ctx.keep)
        lines.append("| {} | «{}» | {} | {} | {} |".format(stamp((row["start"] if at is None else at) / rate),
                                                           _cell(row["phrase"]), _cell(row["what"]), row["dur"],
                                                           row["orient"]))
    path = ctx.outdir / NAME
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
