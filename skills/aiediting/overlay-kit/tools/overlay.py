#!/usr/bin/env python3
"""overlay.py: prepare a working folder, render stills/draft/final, check the result. Python 3.9+, standard library.

Seconds everywhere are seconds of the video passed to `prepare` (not of the original recording if it was cut).
Exit codes: 0 done, 1 a check found a problem (sync, final), 2 an error with a stated reason.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


def _private_python() -> Path:
    """AIEditing's own venv holds OpenCV and numpy, which the face track and the sound check need."""
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "AIEditing" / "venv" / "Scripts" / "python.exe"
    return Path.home() / ".aiediting" / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


if (__name__ == "__main__" and not os.environ.get("AIEDITING_IN_VENV") and sys.prefix == sys.base_prefix
        and _private_python().is_file()):
    sys.exit(subprocess.call([str(_private_python()), str(Path(__file__).resolve()), *sys.argv[1:]],
                             env=dict(os.environ, AIEDITING_IN_VENV="1")))

sys.path.insert(0, str(Path(__file__).resolve().parent))

from overlaylib import commands, final, prepare  # noqa: E402
from overlaylib.common import ToolError, stdout_utf8  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="overlay.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="command", metavar="команда", required=True)

    def add(name, func, help_, *positional):
        sp = sub.add_parser(name, help=help_, description=help_)
        for pos in positional:
            sp.add_argument(pos)
        sp.set_defaults(func=func)
        return sp

    sp = add("prepare", prepare.run_prepare, "развернуть рабочую папку: шаблон, копии, слова, лицо, дизайн, звук, пакеты", "video", "work")
    sp.add_argument("--words", required=True, help="файл слов: строки «секунда слово», секунды этого видео")
    sp.add_argument("--design", required=True, help="папка с tokens.json")
    sp.add_argument("--logo", help="логотип SVG или PNG для углового знака")
    sp.add_argument("--sfx", help="папка со своими звуками (имена как в src/kit/Sound.tsx)")
    sp.add_argument("--music", help="файл тихой музыки-подложки; без него фона нет")
    sp.add_argument("--no-install", action="store_true", help="не ставить npm-пакеты (тесты)")

    sp = add("frame", commands.cmd_frame, "контрольные кадры: out/frames/<секунда>.jpg", "work")
    sp.add_argument("seconds", nargs="*", help="секунды видео")
    add("draft", commands.cmd_draft, "черновой рендер в половинном размере: out/draft.mp4", "work")
    sp = add("sheets", commands.cmd_sheets, "листы приёмки: по 30 кадров на лист", "video", "folder")
    sp.add_argument("--step", type=float, default=4.0, help="шаг между кадрами, секунд (по умолчанию 4)")
    sp = add("empties", commands.cmd_empties, "где сцена пуста дольше порога (нужен numpy)", "video")
    sp.add_argument("--min", type=float, default=1.0, help="порог, секунд (по умолчанию 1)")
    add("texts", commands.cmd_texts, "весь текст сцен на экране в файл — для критиков", "work", "file")
    sp = add("frames", commands.cmd_frames, "обзорный лист и нужные секунды кадров из любого видео", "video", "work")
    sp.add_argument("seconds", nargs="*", help="секунды нужных кадров")
    sp.add_argument("--overview", nargs="?", const="-", help="обзорный лист из 36 кадров (путь файла; без пути — out/overview.jpg)")
    sp.add_argument("--label", help="метка в имени кадров (по умолчанию имя видео)")
    sp.add_argument("--crop", help="обрезка долями кадра «x,y,ширина,высота»")
    sp.add_argument("--width", type=int, default=1280, help="ширина кадра, px (по умолчанию 1280)")
    sp = add("final", final.run_final, "финальный рендер, сдвиг AAC, громкость, атомарная запись, сверка", "work", "release", "name")
    sp.add_argument("--lufs", type=float, default=-14.0, help="целевая громкость (по умолчанию -14)")
    sp.add_argument("--reuse-render", action="store_true", help="не рендерить заново, если out/render.mp4 уже есть")
    add("sync", commands.cmd_sync, "сверка: речь итога против исходника", "base", "final")
    add("index", commands.cmd_index, "пересобрать списки сцен и раскладок (делают сами frame/draft/final)", "work")
    sp = add("example", commands.cmd_example, "положить нейтральный образец из examples/ как сегмент A", "work")
    sp.add_argument("--force", action="store_true", help="заменить уже заполненный сегмент A")
    return p


def main(argv=None) -> int:
    stdout_utf8()
    parser = build_parser()
    try:
        ns, extra = parser.parse_known_args(argv)
        if extra:  # seconds written after an option: argparse leaves them over
            if ns.command in ("frame", "frames") and all(re.fullmatch(r"\d+(?:\.\d+)?", x) for x in extra):
                ns.seconds = list(ns.seconds) + extra
            else:
                parser.error("неизвестные аргументы: " + " ".join(extra))
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else (0 if code is None else 2)
    try:
        return int(ns.func(ns) or 0)
    except ToolError as exc:
        print("Стоп: {}".format(exc), file=sys.stderr, flush=True)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
