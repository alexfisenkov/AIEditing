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

from overlaylib import commands, facecmd, final, peaks, prepare, sfxcat, vertical  # noqa: E402
from overlaylib.common import ToolError, say, stdout_utf8  # noqa: E402


def _sfxcat(args) -> int:
    path = sfxcat.write(Path(args.folder))
    rows = sfxcat.read(path.parent)
    count: dict = {}
    for r in rows:
        count[r["role"]] = count.get(r["role"], 0) + 1
    say("Каталог: {} — звуков {}: {}".format(path, len(rows), ", ".join("{} {}".format(k, v) for k, v in count.items()) or "нет"))
    skipped = sfxcat.left_out(path.parent)
    if skipped:
        say("Без роли, в каталог не вошли ({}): {}. Роль — это подпапка: {}".format(
            len(skipped), ", ".join(skipped[:10]), ", ".join(sfxcat.ROLES)))
    return 0


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
    sp.add_argument("--speech", help="чистая речь WAV той же длины, что видео: она станет public/clips/speech.wav вместо звука видео")
    sp.add_argument("--keep-face", action="store_true", help="после правок маркерами: трек лица остаётся в секундах принятого ролика, в них живут сцены")
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
    sp.add_argument("--face-accepted", metavar="ОСНОВАНИЕ", help="находки или «не проверено» проверки лица в рамке не останавливают выпуск, основание печатается (решение человека)")
    add("sync", commands.cmd_sync, "сверка: речь итога против исходника", "base", "final")
    add("index", commands.cmd_index, "пересобрать списки сцен и раскладок (делают сами frame/draft/final)", "work")
    sp = add("example", commands.cmd_example, "положить нейтральный образец из examples/ как сегмент A", "work")
    sp.add_argument("--force", action="store_true", help="заменить уже заполненный сегмент A")
    sp = add("face", facecmd.run_face, "трек лица: его склейки, что в папке читает его по-старому, пересборка, кадры после склеек", "work")
    sp.add_argument("--rebuild", action="store_true", help="построить трек заново; прежний остаётся в raw/face-before-rebuild.json")
    sp.add_argument("--video", help="с --rebuild в папке с картой времени: первый принятый ролик (в его секундах живут сцены)")
    sp.add_argument("--frames", action="store_true", help="отрисовать кадр через 0,2 с после каждой склейки трека: out/cuts/<секунда>.jpg")
    sp.add_argument("--check", action="store_true", help="проверить детектором, что лицо целиком в рамке спикера через 0,2 и 1 с после каждой склейки; код 1 при находках")

    add("peaks", peaks.cmd_peaks, "звуки сцен против пиков движения черновика: сдвиг в кадрах", "work", "draft")
    add("sfxcat", _sfxcat, "каталог папки звуков: роль, длина, пик (catalog.json рядом со звуками)", "folder")

    sp = add("vertical-init", vertical.run_init, "положить набор для вертикальных клипов (src/vertical) в рабочую папку", "work")
    sp.add_argument("--spans", help="свой spans.json (отрезки, скорость, призыв)")
    sp.add_argument("--renew", action="store_true", help="обновить файлы набора; сцены c<N>.tsx не трогаются никогда")
    sp = add("vertical-check", vertical.run_check, "вертикаль: типы, сборка, покадровая проверка в браузере, листы кадров", "work")
    sp.add_argument("ids", nargs="*", help="клипы (c1 c2 ...); без них все")
    sp.add_argument("--step", type=float, default=1 / 6, help="шаг проверки, секунд (по умолчанию 0.1667)")
    sp = add("vertical-final", vertical.run_final, "вертикаль: рендер, звук из чистой речи, проверка готового файла", "work", "dest")
    sp.add_argument("ids", nargs="*", help="клипы (c1 c2 ...); без них все")
    sp.add_argument("--lufs", type=float, default=-14.0, help="целевая громкость (по умолчанию -14)")
    sp.add_argument("--hum-accepted", metavar="ОСНОВАНИЕ", help="находка про гул становится предупреждением, основание печатается в итоге (решение человека)")
    sp.add_argument("--face-accepted", metavar="ОСНОВАНИЕ", help="находки или «не проверено» проверки лица в рамке не останавливают выпуск, основание печатается (решение человека)")
    sp = add("vertical-words", vertical.run_words, "вертикаль: слова клипа в секундах файла, сцены и ролика (для папки с картой времени)", "work")
    sp.add_argument("ids", nargs="*", help="клипы (c1 c2 ...); без них все")
    sp.add_argument("--words", help="файл слов «секунда слово» в секундах файла public/clips/source.mp4 (по умолчанию raw/words.txt)")
    sp = add("vertical-sheets", vertical.run_sheets, "вертикаль: листы из самих готовых файлов и хвост каждого ролика", "dest")
    sp.add_argument("--step", type=float, default=2.0, help="шаг между кадрами листа всего ролика, секунд (по умолчанию 2)")
    return p


def main(argv=None) -> int:
    stdout_utf8()
    parser = build_parser()
    try:
        ns, extra = parser.parse_known_args(argv)
        if extra:  # seconds written after an option: argparse leaves them over
            if ns.command in ("frame", "frames") and all(re.fullmatch(r"\d+(?:\.\d+)?", x) for x in extra):
                ns.seconds = list(ns.seconds) + extra
            elif ns.command in ("vertical-check", "vertical-final", "vertical-words") and all(re.fullmatch(r"c\d+", x) for x in extra):
                ns.ids = list(ns.ids) + extra
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
