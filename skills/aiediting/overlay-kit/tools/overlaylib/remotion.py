"""Running the Remotion project of a working folder: type check, stills, draft and full renders."""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import List

from .common import FPS, ToolError, run, say, need
from . import scaffold


def ready(work: Path) -> None:
    """Packages installed, indexes fresh. Every render command starts here."""
    if not (work / "node_modules" / "remotion").is_dir():
        raise ToolError("В {} не стоят пакеты. Выполните npm ci в этой папке (или prepare без --no-install).".format(work))
    scaffold.write_index(work)


def _npx() -> str:
    need("npx")
    return shutil.which("npx") or "npx"


def typecheck(work: Path) -> None:
    done = run([_npx(), "tsc", "-p", ".", "--noEmit"], "Проверка типов (tsc)", cwd=work, ok_codes=(0, 1, 2))
    if done.returncode != 0:
        lines = (done.stdout or "").strip().splitlines()
        raise ToolError("Типы не сошлись, рендер не начат:\n" + "\n".join(lines[:30]))


def _browser_args() -> List[str]:
    exe = os.environ.get("OVERLAY_BROWSER")
    return ["--browser-executable=" + exe] if exe else []


def duration(work: Path) -> float:
    text = (work / "src" / "data" / "layouts.ts").read_text(encoding="utf-8")
    found = re.search(r"DURATION = ([\d.]+)", text)
    if not found:
        raise ToolError("В src/data/layouts.ts нет DURATION.")
    return float(found.group(1))


def color_args() -> List[str]:
    """Without these the file comes out with no colour tags or full range, by version: a delivery pipeline refuses it."""
    return ["--pixel-format=yuv420p", "--color-space=bt709"]


def still(work: Path, second: str, out: Path) -> None:
    frame = min(int(round(float(second) * FPS)), int(round(duration(work) * FPS)) - 1)
    out.parent.mkdir(parents=True, exist_ok=True)
    run([_npx(), "remotion", "still", "src/index.ts", "Full", str(out), "--frame={}".format(frame), "--image-format=jpeg",
         "--jpeg-quality=80", "--log=error", "--timeout=120000", *_browser_args()], "Кадр на {} с".format(second), cwd=work, capture=False)


def render(work: Path, out: Path, draft: bool) -> None:
    """Whole video. Written under a temporary name, so a half file never looks finished."""
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + ".part" + out.suffix)
    quality = ["--scale=0.5", "--crf=28", "--jpeg-quality=70"] if draft else ["--crf=19", "--jpeg-quality=92", "--audio-codec=aac", "--audio-bitrate=192k"]
    run([_npx(), "remotion", "render", "src/index.ts", "Full", str(tmp), "--image-format=jpeg", "--log=error", "--timeout=120000",
         *quality, *color_args(), *_browser_args()], "Рендер", cwd=work, capture=False)
    os.replace(str(tmp), str(out))
    say("Готово: " + str(out))
