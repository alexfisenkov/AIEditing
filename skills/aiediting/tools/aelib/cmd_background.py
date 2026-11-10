"""A direct editing request: prepare its local tools, process, then report the real file."""
from __future__ import annotations

from pathlib import Path

from .session import CliError


def run(opt) -> str:
    from runtime.media.background import edit_background
    from runtime.media.chromakey import chromakey
    from .setup import ensure_tools

    video, output = Path(opt.video).expanduser().resolve(), Path(opt.output).expanduser().resolve()
    if not video.is_file() or video == output:
        raise CliError("Нужен существующий исходник и отдельный путь результата")
    transparent = opt.mode in {"remove", "chromakey"}
    if output.suffix.lower() != (".mov" if transparent else ".mp4"):
        raise CliError("Для прозрачности укажите .mov, для заменённого фона — .mp4")
    tools = ["ffmpeg"] if opt.mode == "chromakey" else ["ffmpeg", "numpy", "onnxruntime", "rvm-model"]
    if opt.mode != "chromakey" and opt.model:
        if not Path(opt.model).expanduser().is_file():
            raise CliError("Не найдена указанная модель: {}".format(opt.model))
        tools.remove("rvm-model")
    print(ensure_tools(tools), flush=True)
    if opt.mode == "chromakey":
        final = chromakey(video, output, key_color=opt.key_color, similarity=opt.similarity, blend=opt.blend)
    else:
        final = edit_background(video, output, mode=opt.mode, background=opt.value,
                                model_path=opt.model, downsample_ratio=opt.downsample_ratio)
    return "Файл создан, проверены наличие звука и длительность: {}. Края маски проверьте на кадрах перед выдачей.".format(final)


def image_cutout(opt) -> str:
    from .setup import ensure_tools
    from .toolbox import ToolboxError, image_cutout as cutout

    source, output = Path(opt.source).expanduser().resolve(), Path(opt.output).expanduser().resolve()
    if not source.is_file() or source == output or output.suffix.lower() != ".png":
        raise CliError("Нужно существующее изображение и отдельный путь результата .png")
    print(ensure_tools(["rembg", "birefnet-lite-model"]), flush=True)
    try:
        result = cutout(source, output)
    except ToolboxError as exc:
        raise CliError(str(exc)) from exc
    return "Прозрачное изображение создано: {}. Маску проверьте на превью.".format(result)
