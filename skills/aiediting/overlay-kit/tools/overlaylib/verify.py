"""`sync`: the speech of a finished file against the source. Shift per window, duration, verdict."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Tuple

from . import audiosync
from .common import say
from .media import duration_of

TOLERANCE_MS = 10.0
DURATION_TOLERANCE = 0.1


def color_problems(path: Path) -> List[str]:
    """What keeps the file from going to delivery as it is: H.264 yuv420p, limited range, BT.709 in all three tags."""
    from .common import run

    text = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt,color_range,color_space,color_primaries,color_transfer",
                "-of", "json", str(path)], "Цвет файла").stdout
    found = (json.loads(text).get("streams") or [{}])[0]
    wanted = {"pix_fmt": "yuv420p", "color_range": "tv", "color_space": "bt709", "color_primaries": "bt709", "color_transfer": "bt709"}
    return ["{} = {}, нужно {}".format(k, found.get(k, "нет"), v) for k, v in wanted.items() if found.get(k) != v]


def sync_report(base: Path, final: Path, length: Optional[float] = None) -> Tuple[bool, float]:
    """Prints the table; returns (within tolerance, worst shift in ms). `length`: the seconds the result must last,
    when `base` holds only the sound: a recording's sound can be shorter than its picture."""
    ref, test = audiosync.pcm(base), audiosync.pcm(final)
    d_base, d_final = length if length is not None else duration_of(base), duration_of(final)
    say("Длительность: исходник {:.2f} с, итог {:.2f} с".format(d_base, d_final))
    lags = audiosync.measure(ref, test)
    if not lags:
        from .common import ToolError
        raise ToolError("В звуке исходника нет участков с речью, сверять не с чем.")
    for start, lag in lags:
        say("{:7.1f} с: сдвиг {:+.1f} мс".format(start, lag * 1000))
    worst = max(abs(lag) for _, lag in lags) * 1000
    say("Наибольший сдвиг {:.1f} мс (допуск {:g} мс)".format(worst, TOLERANCE_MS))
    same = abs(d_base - d_final) <= DURATION_TOLERANCE
    if not same:
        say("Длительность расходится больше чем на {:g} с.".format(DURATION_TOLERANCE))
    return worst <= TOLERANCE_MS and same, worst
