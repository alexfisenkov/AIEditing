"""Inspect the actual local editing toolbox; availability is not an output-quality verdict."""
from __future__ import annotations

import json
import os
import shutil
import subprocess

from . import catalog
from .checks import status
from .session import CliError

# method describes the execution path, not a promise that every request has a preset.
FAMILIES = [
    ("cuts", "Склейки, паузы, дубли, скорость", "native", ["ffmpeg", "whisper-cpp", "whisper-model"], ["trim", "concat", "atempo"]),
    ("subtitles", "Распознавание, SRT и вшитые субтитры", "native", ["ffmpeg", "whisper-cpp", "whisper-model", "pillow"], ["overlay"]),
    ("audio", "Чистка, громкость, музыка и микширование", "tool-composition", ["ffmpeg"], ["afftdn", "loudnorm", "amix", "afade"]),
    ("colour", "Цветокоррекция и LUT", "tool-composition", ["ffmpeg"], ["eq", "curves", "lut3d"]),
    ("transforms", "Кадрирование, масштаб, поворот и вертикаль", "native", ["ffmpeg", "opencv-python", "yunet-model"], ["crop", "scale", "transpose"]),
    ("stabilization", "Стабилизация", "tool-composition", ["ffmpeg"], ["deshake"]),
    ("tracking", "Поиск лица и движение кадра", "native", ["ffmpeg", "opencv-python", "numpy", "yunet-model"], ["crop"]),
    ("background", "Удаление и замена фона человека", "native", ["ffmpeg", "numpy", "onnxruntime", "rvm-model"], ["overlay"]),
    ("chromakey", "Хромакей и прозрачность", "native", ["ffmpeg"], ["chromakey", "alphaextract"]),
    ("transitions", "Переходы, наложения и маски", "tool-composition", ["ffmpeg"], ["xfade", "overlay", "alphamerge"]),
    ("multicam", "Несколько камер и синхронизация дорожек", "tool-composition", ["ffmpeg", "numpy"], ["amix", "trim", "concat"]),
    ("broll", "Перебивки и сборка истории из своих материалов", "tool-composition", ["ffmpeg"], ["overlay", "trim", "concat"]),
    ("graphics", "Плашки, анимации и графика", "kit", ["ffmpeg", "node", "hyperframes", "remotion", "pillow"], ["overlay"]),
    ("delivery", "Кодирование, платформенные копии и проверка потоков", "native", ["ffmpeg"], ["scale", "fps"]),
    ("scenes", "Автоматический поиск границ сцен", "tool-composition", ["ffmpeg", "opencv-python", "scenedetect"], []),
    ("audio-analysis", "Ритм, аудиособытия и измерение сдвига дорожек", "tool-composition", ["soundfile", "librosa"], []),
    ("subtitle-formats", "SRT, ASS, VTT и стили субтитров", "tool-composition", ["pysubs2", "ffmpeg"], ["subtitles"]),
    ("image-cutout", "Отделение объектов на изображениях", "tool-composition", ["rembg", "onnxruntime", "birefnet-lite-model"], []),
]


def filters() -> set:
    exe = os.environ.get("AIEDITING_FFMPEG") or shutil.which("ffmpeg")
    if not exe:
        return set()
    try:
        proc = subprocess.run([exe, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return set()
    if proc.returncode:
        return set()
    return {parts[1] for line in proc.stdout.splitlines() if len(parts := line.split()) >= 3
            and len(parts[0]) in (2, 3) and set(parts[0]) <= set(".TSC") and "->" in parts[2]}


def inspect_capabilities() -> dict:
    rows, available = catalog.tools(), filters()
    states = {key: status(row) for key, row in rows.items()}
    capabilities = []
    for key, title, method, needs, required_filters in FAMILIES:
        missing_tools = [tool for tool in needs if not states.get(tool, {}).get("ok")]
        missing_filters = [name for name in required_filters if name not in available]
        capabilities.append({"id": key, "title": title, "method": method, "tools": needs,
                             "filters": required_filters, "ready": not missing_tools and not missing_filters,
                             "missing_tools": missing_tools, "missing_filters": missing_filters})
    from .checks import argv_of

    executables = {name: argv_of([name])[0] for name in ("ffmpeg", "ffprobe", "node")}
    return {"verification": "tool-readiness; output must be checked separately", "executables": executables,
            "ffmpeg_filters": sorted(available),
            "tools": states, "capabilities": capabilities}


def cmd_capabilities(opt) -> str:
    data = inspect_capabilities()
    if opt.json:
        return json.dumps(data, ensure_ascii=False, indent=2)
    lines = ["Проверка инструментов; качество конкретного монтажа проверяется отдельно.",
             "FFmpeg: " + data["executables"]["ffmpeg"]]
    for row in data["capabilities"]:
        missing = row["missing_tools"] + row["missing_filters"]
        lines.append("{}: {} [{}]{}".format(row["title"], "инструменты готовы" if row["ready"] else "требуется подготовка",
                                             row["method"], "; нет: " + ", ".join(missing) if missing else ""))
    return "\n".join(lines)
