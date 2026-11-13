"""What the person's answer to the `broll` question becomes: inserts in the plan, places on the shoot list."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ..library import inventory, search
from . import broll_place as place

_STILL = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tif", ".tiff", ".bmp"}


def kind_of(row: Dict) -> str:
    return "photo" if row.get("type") == "фото" else ("stock" if row.get("kind") == "стоки" else "video")


def _put(ctx, row: Dict, file: Path, kind: str, shown: str, extra: Dict) -> None:
    ctx.broll.append(dict(extra, file=str(file), kind=kind, shown=shown, who=list(row.get("who") or [])))
    if row.get("log"):
        ctx.note("{}: снято в лог-профиле, а цветового пресета (LUT) нет — цвет может не совпасть с основным кадром".format(
            row["f"]))


def settle(ctx, lib: Path, answer: Dict, stock, by_file: Dict, never: List[str], proposed: Dict) -> None:
    for r in answer.get("rows", []):
        if r.get("ok") is False or r.get("no"):
            continue
        start, end = float(r["start"]), float(r["end"])
        extra = {"start": start, "end": end, "phrase": r.get("phrase", ""), "from": float(r.get("from") or 0.0)}
        if not place.MIN_LEN - 1e-6 <= end - start <= place.MAX_LEN + 1e-6:
            ctx.note("Вставка в {:.1f} с не поставлена: длина {:.1f} с, а нужно от 3 до 6 с".format(start, end - start))
        elif r.get("file"):
            name = str(r["file"])
            row = by_file.get(name) or {"f": name, "type": "фото" if Path(name).suffix.lower() in _STILL else "видео"}
            file = inventory.file_of(lib, row)
            if search.blocked(row, never) or row.get("never"):
                ctx.note("Кадр {} назван в «чего нельзя» и не поставлен".format(name))
            elif not file.is_file():
                ctx.note("Кадра {} нет на диске, вставка не поставлена".format(name))
            else:
                if name != proposed.get(round(start, 3)):  # another frame: its own best stretch
                    extra["from"] = (place.piece_of(row) or (0.0, 0.0))[0]
                _put(ctx, row, file, kind_of(row), "сток" if row.get("kind") == "стоки" else name, extra)
        elif r.get("stock"):
            row = stock.fetch(r["stock"].get("provider"), r["stock"].get("id")) if stock else None
            if row:
                _put(ctx, row, inventory.file_of(lib, row), "stock", "сток", dict(extra, **{"from": 0.0}))
            else:
                _shoot(ctx, r)
        else:
            _shoot(ctx, r)


def _shoot(ctx, r: Dict) -> None:
    ctx.shoot_list.append({"start": float(r["start"]), "end": float(r["end"]), "phrase": r.get("phrase", ""),
                           "what": r.get("want") or "Кадр под слова «{}»".format(r.get("phrase", "")),
                           "dur": int(round(float(r["end"]) - float(r["start"]))), "orient": "горизонтальный"})
