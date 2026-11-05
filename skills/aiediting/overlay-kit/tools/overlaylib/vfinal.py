"""`vertical-final`: render the picture of each clip, mix the sound from the clean speech, measure the finished file."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from . import remotion, vmeasure, vplan, vsound, vspans
from .audiosync import _np
from .common import ToolError, run, say, warn

CLICK = "pop-soft.wav"


def render_silent(work: Path, cid: str) -> Path:
    out = work / "out" / "vertical" / "{}.silent.mp4".format(cid)
    tmp = out.with_name(out.stem + ".part.mp4")
    run([remotion._npx(), "remotion", "render", "src/vertical/index.ts", cid, str(tmp), "--crf=18", "--image-format=jpeg", "--jpeg-quality=92",
         "--muted", "--log=error", "--timeout=120000", *remotion.color_args(), *remotion._browser_args()], "Рендер " + cid, cwd=work, capture=False)
    os.replace(str(tmp), str(out))
    return out


def finish(work: Path, dest: Path, data: Dict, cid: str, lufs: float, hum_accepted: Optional[str], passed: Optional[List[str]] = None) -> bool:
    """`passed` collects the clips whose hum finding was really let through by --hum-accepted."""
    speech = work / "public" / "clips" / "speech.wav"
    if not speech.is_file():
        raise ToolError("Нет {}: чистая речь берётся оттуда. Её делает prepare (--speech даёт свою).".format(speech))
    silent = render_silent(work, cid)
    total = vspans.clip_seconds(data, cid)
    click = work / "public" / "sfx" / CLICK
    if not click.is_file():
        warn("нет {}: призыв появится без щелчка.".format(click))
    name = vspans.clip_name(data, cid) + ".mp4"
    tmp = dest / ".{}.part.mp4".format(cid)
    vsound.mix(speech, click, silent, data["spans"][cid], data["rate"], total, vspans.cta_start(data, cid), tmp, lufs)
    say("{}: {} ({:.2f} с, {:.1f} МБ)".format(cid, dest / name, total, tmp.stat().st_size / 1e6))
    ok, lines = vmeasure.check_clip(tmp, data, cid, lufs, hum_accepted)
    for text in lines:
        say("  " + text)
    if passed is not None and any(t.startswith("ПРЕДУПРЕЖДЕНИЕ гул") for t in lines):
        passed.append(cid)
    if not ok:  # an earlier good file keeps its name
        failed = dest / ".{}.failed.mp4".format(cid)
        os.replace(str(tmp), str(failed))
        say("  Файл не выпущен, он лежит как {}".format(failed))
        return False
    os.replace(str(tmp), str(dest / name))
    old = dest / ".{}.failed.mp4".format(cid)
    if old.is_file():  # a failure of an earlier run is behind us
        old.unlink()
    return True


def run_final(args) -> int:
    dest = Path(args.dest).expanduser()
    if not dest.is_absolute():
        raise ToolError("Папка результата должна быть абсолютным путём: {}".format(args.dest))
    reason = (args.hum_accepted or "").strip() or None
    if args.hum_accepted is not None and not reason:
        raise ToolError("--hum-accepted требует основание словами: что вы услышали и решили (например «сплошная речь, прослушал, гула нет»).")
    _np()  # the measuring needs numpy: its absence is said before a long render, not after it
    work, data, ids = vplan.load_plan(args.work, args.ids)
    vplan.typecheck(work)
    try:
        dest.mkdir(parents=True, exist_ok=True)
        passed: List[str] = []
        bad: List[str] = [cid for cid in ids if not finish(work, dest, data, cid, args.lufs, reason, passed)]
    except OSError as exc:
        raise ToolError("Не удалось записать в {}: {}".format(dest, exc))
    if reason and passed:
        say("Гул пропущен у клипов {} по основанию: «{}». Это решение человека: назовите его в своём отчёте.".format(", ".join(passed), reason))
    elif reason:
        say("--hum-accepted не понадобился: гула не найдено ни в одном клипе.")
    if bad:
        say("Не прошли проверку: {}. Это не готовые ролики: исправьте и повторите.".format(", ".join(bad)))
        return 1
    say("Готово: {} клипов в {}. Дальше: overlay.py vertical-sheets {} и взгляд на готовый файл в полный размер.".format(len(ids), dest, dest))
    return 0
