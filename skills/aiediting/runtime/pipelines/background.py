"""Validate a background choice before rendering, then apply human matting."""
from __future__ import annotations

from pathlib import Path

from ..media.background import COLOUR, edit_background, model_file
from ..media.ffmpeg import MediaError, ensure_file
from .errors import PipelineError

MODES = {"remove", "solid", "image", "video", "blur", "chromakey"}


def settings(ctx):
    value = ctx.p("background") or {}
    if not isinstance(value, dict):
        raise PipelineError("params.background должен быть объектом с mode и value")
    mode = value.get("mode", "remove")
    if mode not in MODES:
        raise PipelineError("params.background.mode: выберите remove, solid, image, video, blur или chromakey")
    background = value.get("value")
    if mode == "solid" and (not isinstance(background, str) or not COLOUR.fullmatch(background)):
        raise PipelineError("params.background.value: для solid нужен цвет #RRGGBB")
    if mode in {"image", "video"}:
        try:
            ensure_file(background)
        except (TypeError, MediaError) as exc:
            raise PipelineError("params.background.value: нужен существующий файл фона") from exc
    ratio = value.get("downsample_ratio")
    if ratio is not None:
        try:
            if not 0 < float(ratio) <= 1:
                raise ValueError
        except (TypeError, ValueError) as exc:
            raise PipelineError("params.background.downsample_ratio должен быть в (0, 1]") from exc
    if mode == "chromakey":
        colour = value.get("key_color", "#00ff00")
        if not isinstance(colour, str) or not COLOUR.fullmatch(colour):
            raise PipelineError("params.background.key_color: цвет вида #RRGGBB")
        for key in ("similarity", "blend"):
            if key in value:
                try:
                    number = float(value[key])
                    if not 0 <= number <= 1:
                        raise ValueError
                except (TypeError, ValueError) as exc:
                    raise PipelineError("params.background.{} должен быть в [0, 1]".format(key)) from exc
    return value


def plan_background(ctx):
    value = settings(ctx)
    if value.get("mode", "remove") in {"remove", "chromakey"}:
        overlays = {"plate", "overlay_png", "animations", "bands", "graphics", "reedit", "export_platforms"} & set(ctx.steps)
        if overlays:
            raise PipelineError("Прозрачный MOV сначала делается отдельным слоем; затем накладывайте графику в Remotion. "
                                "Для единого MP4 с графикой выберите solid, image, video или blur. "
                                "Иначе шаги {} потеряют прозрачность или текст.".format(", ".join(sorted(overlays))))
    if value.get("mode") == "chromakey":
        return
    try:
        model_file(value.get("model"))
    except MediaError as exc:
        raise PipelineError(str(exc)) from exc


def plan_behind_head(ctx):
    if not {"plate", "overlay_png", "animations"}.intersection(ctx.steps):
        raise PipelineError("Для behind_head нужны плашки, субтитры или анимации; без них эффект не выполняется")
    try:
        model_file((ctx.p("background") or {}).get("model"))
    except MediaError as exc:
        raise PipelineError(str(exc)) from exc


def apply_background(ctx, src, tmp, graphics=None):
    """`graphics` is a composited video: re-layer the original person above its overlays."""
    value = settings(ctx) if graphics is None else (ctx.p("background") or {})
    mode = "foreground" if graphics is not None else value.get("mode", "remove")
    background = graphics if graphics is not None else value.get("value")
    out = Path(tmp) / ("7-передний-план.mp4" if graphics is not None else
                       ("6-фон.mov" if mode in {"remove", "chromakey"} else "6-фон.mp4"))
    if mode == "chromakey":
        from ..media.chromakey import chromakey

        return chromakey(src, out, key_color=value.get("key_color", "#00ff00"),
                         similarity=float(value.get("similarity", 0.12)), blend=float(value.get("blend", 0.08)))
    return edit_background(src, out, mode=mode, background=background,
                           model_path=value.get("model"), downsample_ratio=value.get("downsample_ratio"))
