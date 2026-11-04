"""The commands of the vertical cut: vertical-init, vertical-check, vertical-final, vertical-sheets."""
from __future__ import annotations

from pathlib import Path

from . import vfinal, vcheck, vinit, vmap, vmeasure, vsheets, vspans
from .common import ToolError, need, say, work_dir
from .media import duration_of

run_init = vinit.run_init
run_check = vcheck.run_check
run_final = vfinal.run_final


def run_sheets(args) -> int:
    need("ffmpeg", "ffprobe")
    folder = Path(args.dest).expanduser()
    files = sorted(p for p in folder.glob("*.mp4") if not p.name.startswith("."))
    if not files:
        raise ToolError("В {} нет готовых роликов (.mp4).".format(folder))
    for video in files:
        info = vmeasure.probe(video)
        lufs, peak = vmeasure.loudness(video)
        say("{}: {}x{} {:.2f} к/с, видео {:.2f} с, звук {:.2f} с, {} LUFS, пик {} dBFS".format(
            video.name, info["width"], info["height"], info["fps"], info["video"], info["audio"], lufs, peak))
        for sheet in vsheets.file_sheets(video, folder / "sheets", info["total"], args.step):
            say("  " + str(sheet))
    return 0


def run_words(args) -> int:
    """The words of each clip with the seconds of the clip, of the file and of the scenes, so that scene times are not worked out by hand.
    It needs only the set and spans.json: the scenes of the clips may not exist yet."""
    work = work_dir(args.work)
    spans_file = work / "src" / "vertical" / "spans.json"
    if not spans_file.is_file():
        raise ToolError("В {} нет набора для вертикали. Сначала: overlay.py vertical-init {}".format(work, work))
    data = vspans.load(spans_file)
    have = vspans.clip_ids(data)
    ids = list(dict.fromkeys(args.ids or have))
    unknown = [c for c in ids if c not in have]
    if unknown:
        raise ToolError("Нет клипа {}. Есть: {}.".format(", ".join(unknown), ", ".join(have)))
    words = vmap.read_words(vmap.words_file(work, args.words))
    rows = vmap.load_rows(work)
    if rows:
        vmap.check_words_fit(words, rows, duration_of(work / "public" / "clips" / "source.mp4"))
        say(vmap.explain(rows))
    for cid in ids:
        say("{}: слова в клипе (секунда клипа | файла | сцены)".format(cid))
        for c, f, o, word in vmap.clip_words(words, rows, data, cid):
            say("  {:7.2f} | {:8.2f} | {:8.2f}  {}".format(c, f, o, word))
    return 0
