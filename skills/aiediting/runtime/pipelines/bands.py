"""The `bands` step: a clip's headline and the format's call to action on the fields of a horizontal picture in 9:16."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Dict

from .errors import PipelineError

COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")
LONGEST_ROW = 70  # letters of one line of the call to action: more would be too small to read on a phone
FORBIDDEN = re.compile(r'[/\\:*?"<>|%]+')


def clean_name(name: str) -> str:
    """A file name from the model's words: no folders, nothing a disk or ffmpeg refuses, no leading dot."""
    return FORBIDDEN.sub(" ", str(name)).strip(" .")


def name_key(name: str) -> str:
    """Two names are one file when this is equal: APFS and NTFS do not tell case or composed letters apart."""
    return unicodedata.normalize("NFC", clean_name(name)).casefold()


def plan_bands(ctx) -> None:
    """Refused before the questions and the rendering, not in the middle of them."""
    from ..media.vertical import shown_size
    from ..render.design import spec
    from ..render.errors import RenderError

    layout = ctx.p("layout")
    w, h = shown_size(ctx.info)
    if not (isinstance(layout, dict) and layout.get("kind") == "native") or w <= h:
        raise PipelineError("Заголовок и призыв лежат на полях вокруг горизонтальной картинки: нужен горизонтальный "
                            "исходник и params.layout {\"kind\": \"native\"}. При кадрировании полей нет: уберите шаг bands.")
    background = layout.get("background")
    if background and not COLOUR.match(str(background)):
        raise PipelineError("params.layout.background — цвет вида #000000; сейчас: {}".format(background))
    try:
        spec(ctx.design(vertical=True), "band")
    except RenderError:
        raise PipelineError("В дизайн-системе формата нет video.band: возьмите его из примера chrome-graphite в tokens.json.")
    if not ctx.design().get("gradient", {}).get("chrome"):
        raise PipelineError("В дизайн-системе формата нет gradient.chrome: заголовок полей рисуется им.")
    for row in re.split(r"(?<=[?!.])\s+", str(ctx.p("cta") or "").strip(), maxsplit=1):
        if len(row) > LONGEST_ROW:
            raise PipelineError("Призыв не помещается крупно: «{}». До {} знаков в строке, строк две: первое предложение "
                                "и остальное.".format(row, LONGEST_ROW))


def lay_bands(ctx, piece: Dict, cur: Path, folder: Path) -> Path:
    """`cur` with both fields drawn for the whole clip: the headline is there on the first frame, no fade."""
    from .. import media
    from ..media.vertical import _even, shown_size
    from ..render.band import band

    headline, cta = str(piece.get("headline") or ""), str(ctx.p("cta") or "")
    if not headline.strip():
        ctx.note("{}: у отрывка нет заголовка (headline) — верхнее поле пустое".format(piece.get("id")))
    if not (headline.strip() or cta.strip()):
        return cur
    info = media.probe(cur)
    frame, source = shown_size(info), shown_size(ctx.info)
    picture = _even(frame[0] * source[1] / float(source[0]))
    png = band(headline, cta, ctx.design(vertical=True), frame_size=frame, picture_height=picture,
               out=folder / "поля.png")
    return media.overlay_png(cur, [{"png": png, "x": 0, "y": 0, "start": 0.0, "end": info["duration"], "fade": 0.0}],
                             folder / "4-поля.mp4")
