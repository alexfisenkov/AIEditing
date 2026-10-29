"""Frames with the planned blur boxes drawn on them, for the person to check before the export."""
from __future__ import annotations

from typing import Dict, List

PER_REGION = 3


def boxes_on_frames(ctx, regions: List[Dict]) -> List[str]:
    from ..media.ffmpeg import run

    folder = ctx.work / "blur-track"
    folder.mkdir(parents=True, exist_ok=True)
    shots = []
    for i, r in enumerate(regions):
        path = r["path"]
        picks = [path[int(k * (len(path) - 1) / max(1, PER_REGION - 1))] for k in range(PER_REGION)]
        for j, pt in enumerate(picks):
            out = folder / "area{}_{}_t{:.2f}s.png".format(i + 1, j + 1, pt["t"])
            box = "drawbox=x={:.0f}:y={:.0f}:w={}:h={}:color=red@0.9:t=4".format(
                pt["x"], pt["y"], int(r["w"]), int(r["h"]))
            run(["-ss", "{:.3f}".format(pt["t"]), "-i", ctx.src, "-frames:v", "1", "-vf", box, "-an", out])
            shots.append(str(out))
    return shots
