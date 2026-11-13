"""`vertical-check`: types, a bundle, the audit of every frame in the browser, sheets with the real second on each frame."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import List

from . import facecheck, facejudge, remotion, vplan, vsheets, vspans
from .common import ToolError, run, say

DEFAULT_STEP = 1 / 6  # seconds between audited frames
SHEET_EVERY = 0.5  # seconds between frames on a sheet
SHOW = 60  # findings printed in full


def bundle(work: Path, entry: str = "src/vertical/index.ts") -> Path:
    """A folder of its own for each run, so that two checks at the same time do not take each other's bundle away.
    `entry`: the vertical set, or src/index.ts for the long video (the face check)."""
    root = work / "out" / ("vertical" if "vertical" in entry else "face-check")
    root.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="bundle-", dir=str(root))) / "site"
    run([remotion._npx(), "remotion", "bundle", entry, "--out-dir=" + str(out), "--log=error"], "Сборка " + entry, cwd=work, capture=False)
    return out


def audit_clip(work: Path, site: Path, cid: str, step: float, zone) -> List[str]:
    root = work / "out" / "vertical"
    run(["node", "tools-local/vertical-frames.mjs", str(site), str(root), cid, "{:.4f}".format(step)], "Покадровая проверка " + cid, cwd=work)  # the browser's console is not shown
    clip = root / cid
    meta = json.loads((clip / "frames.json").read_text(encoding="utf-8"))
    have = {vsheets.frame_of(p.name) for p in (clip / "frames").iterdir() if vsheets.FRAME_FILE.match(p.name)}
    lost = sorted(set(meta["frames"]) - have)
    if lost:
        raise ToolError("Клип {}: не отрисованы кадры {}. Проверка неполная, листы не собраны.".format(cid, ", ".join(map(str, lost[:8]))))
    try:
        sheets = vsheets.frame_sheets(clip / "frames", clip / "sheets", meta["fps"], SHEET_EVERY, zone)
    except OSError as exc:
        raise ToolError("Клип {}: листы не записались ({}). Не запущена ли вторая проверка того же клипа? Её кадры и листы лежат там же.".format(cid, exc))
    say("{}: листов {}, шаг проверки {:.4f} с, кадров {}: {}".format(cid, len(sheets), meta["step"], len(meta["frames"]), clip / "sheets"))
    return [r for r in (clip / "findings.txt").read_text(encoding="utf-8").splitlines() if r.strip()]


def face_rows(work: Path, site: Path, data, cid: str, detector) -> List[str]:
    """The findings of the face check of a clip, written into its findings.txt as well; an unchecked clip is a finding too."""
    found, unchecked = facecheck.check_clip(work, site, data, cid, detector)
    rows = found + (["лицо в рамке не проверено: {}".format(unchecked)] if unchecked else [])
    if rows:
        with (work / "out" / "vertical" / cid / "findings.txt").open("a", encoding="utf-8") as out:
            out.write("".join(row + "\n" for row in rows))
    return rows


def run_check(args) -> int:
    if args.step <= 0 or args.step > 1:
        raise ToolError("--step: шаг проверки от 0 до 1 секунды, обычно 0.1667 (6 кадров в секунду).")
    work, data, ids = vplan.load_plan(args.work, args.ids)
    zone = vspans.SAFE_ZONES[data.get("safe", "reels")]
    vplan.typecheck(work)
    site = bundle(work)
    total = 0
    detector = facejudge.detector()  # (the detector, or None and why)
    try:
        for cid in ids:
            rows = audit_clip(work, site, cid, args.step, zone)
            rows += face_rows(work, site, data, cid, detector)  # the face whole in its band or circle after every joint and cut
            total += len(rows)
            say("{}: найдено {}, файл {}".format(cid, len(rows), work / "out" / "vertical" / cid / "findings.txt"))
            for row in rows[:SHOW]:
                say("  " + row)
            if len(rows) > SHOW:
                say("  ... ещё {}".format(len(rows) - SHOW))
    finally:
        shutil.rmtree(str(site.parent), ignore_errors=True)
    say("Итого находок: {}. Цель — ноль; потом листы глазами и два круга независимых проверяющих.".format(total))
    return 1 if total else 0
