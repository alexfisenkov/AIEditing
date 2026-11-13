"""A sheet of small numbered frames, so the agent describes a batch of files by looking once.

A video gives its middle frame. Frames are cut by ffmpeg; Pillow (when installed) turns photos by
EXIF, lays the grid and draws the numbers; without Pillow ffmpeg lays the grid and the numbers are
the order, left to right, top to bottom.
"""
from __future__ import annotations

import math
import tempfile
from pathlib import Path
from typing import List

from .meta import kind_of

CELL = 256
GAP = 6
BACK = (32, 32, 32)
_FIT = "scale={0}:{0}:force_original_aspect_ratio=decrease,pad={0}:{0}:(ow-iw)/2:(oh-ih)/2:color=0x202020"


def _middle(path: Path) -> float:
    from ..media.probe import probe

    try:
        return max(0.0, probe(path)["duration"] / 2.0)
    except Exception:  # a broken file still gets its cell
        return 0.0


def _frame(src: Path, dst: Path) -> bool:
    """One square frame of `src` in `dst`; False when ffmpeg cannot read it."""
    from ..media.ffmpeg import run

    seek = ["-ss", "{:.2f}".format(_middle(src))] if kind_of(src) == "видео" else []
    proc = run(seek + ["-i", str(src), "-frames:v", "1", "-vf", _FIT.format(CELL), str(dst)], check=False)
    return proc.returncode == 0 and dst.is_file()


def _photo(src: Path, dst: Path) -> bool:
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return False
    try:
        with Image.open(str(src)) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((CELL, CELL))
            cell = Image.new("RGB", (CELL, CELL), BACK)
            cell.paste(im, ((CELL - im.width) // 2, (CELL - im.height) // 2))
            cell.save(str(dst))
            return True
    except Exception:
        return False


def _with_pillow(cells: List[Path], out: Path, grid: int) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False
    rows = math.ceil(len(cells) / grid)
    sheet = Image.new("RGB", (grid * (CELL + GAP) + GAP, rows * (CELL + GAP) + GAP), BACK)
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=28)
    except TypeError:  # Pillow older than 10.1
        font = ImageFont.load_default()
    for i, cell in enumerate(cells):
        x, y = GAP + (i % grid) * (CELL + GAP), GAP + (i // grid) * (CELL + GAP)
        if cell.is_file():
            with Image.open(str(cell)) as im:
                sheet.paste(im.convert("RGB"), (x, y))
        draw.rectangle([x, y, x + 46, y + 36], fill=(0, 0, 0))
        draw.text((x + 6, y + 3), str(i + 1), fill=(255, 255, 255), font=font)
    sheet.save(str(out), quality=88)
    return True


def _with_ffmpeg(cells: List[Path], out: Path, grid: int, tmp: Path) -> None:
    from ..media.ffmpeg import run

    rows = math.ceil(len(cells) / grid)
    for i, cell in enumerate(cells):
        target = tmp / "{:04d}.png".format(i + 1)
        if cell.is_file():
            cell.replace(target)
        else:
            run(["-f", "lavfi", "-i", "color=c=0x202020:s={0}x{0}".format(CELL), "-frames:v", "1", str(target)])
    run(["-framerate", "1", "-i", str(tmp / "%04d.png"), "-frames:v", "1",
         "-vf", "tile={}x{}:padding={}:margin={}:color=0x202020".format(grid, rows, GAP, GAP), str(out)])


def sheet(files: List[Path], out: Path, grid: int = 6) -> Path:
    """`out` (JPEG): `files` in a grid of `grid` columns, cell N is file N (from 1)."""
    if not files:
        raise ValueError("Нет файлов для листа")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    grid = max(1, min(int(grid), len(files)))
    with tempfile.TemporaryDirectory(prefix="aiediting-sheet-") as name:
        tmp = Path(name)
        cells = []
        for i, src in enumerate(files):
            cell = tmp / "cell-{:04d}.png".format(i)
            if not (kind_of(Path(src)) == "фото" and _photo(Path(src), cell)):
                _frame(Path(src), cell)
            cells.append(cell)
        if not _with_pillow(cells, out, grid):
            _with_ffmpeg(cells, out, grid, tmp)
    return out
