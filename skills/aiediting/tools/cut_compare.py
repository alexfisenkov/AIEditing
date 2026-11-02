#!/usr/bin/env python3
"""A person's cut against a format skill's cut of the same source, in numbers.

    python cut_compare.py <Info.fcpxml or .fcpxmld> <отчёт.md> [--min 0.25]

The person's cut comes from the Final Cut timeline, the skill's from «Вырезано» in its report, which gives times to
0.1 s: the totals carry that noise, so judge margins by the timeline, not by these numbers.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fcpx_timeline import TimelineError, read  # noqa: E402

Span = Tuple[float, float]


def _seconds(stamp: str) -> float:
    h, m, s = stamp.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def report_cuts(path) -> List[Span]:
    parts = Path(path).read_text(encoding="utf-8").split("## Вырезано")
    if len(parts) < 2:
        raise ValueError("В отчёте нет раздела «Вырезано»: {}".format(path))
    return [(_seconds(a), _seconds(b)) for a, b in re.findall(r"- (\d+:\d+:[\d.]+)–(\d+:\d+:[\d.]+):", parts[1].split("\n## ")[0])]


def invert(spans: List[Span], total: float) -> List[Span]:
    out, at = [], 0.0
    for a, b in sorted(spans):
        if a > at:
            out.append((at, a))
        at = max(at, b)
    if at < total:
        out.append((at, total))
    return out


def only_in(a: List[Span], b: List[Span], least: float = 0.0) -> List[Span]:
    """Parts of `a` that `b` does not cover, at least `least` s long."""
    out = []
    for x, y in a:
        for p, q in invert([s for s in b if s[0] < y and x < s[1]], y):
            p = max(p, x)
            if q - p >= max(least, 1e-6):
                out.append((p, q))
    return out


def seconds(spans: List[Span]) -> float:
    return sum(b - a for a, b in spans)


def stamp(t: float) -> str:
    return "{}:{:04.1f}".format(int(t // 60), t % 60)


def summary(person: List[Span], skill: List[Span], least: float = 0.25) -> str:
    own, its = only_in(person, skill), only_in(skill, person)
    lines = ["человек: кусков {}, оставлено {:.1f} с".format(len(person), seconds(person)),
             "скилл:   кусков {}, оставлено {:.1f} с".format(len(skill), seconds(skill)),
             "оставил только человек {:.1f} с, только скилл {:.1f} с".format(seconds(own), seconds(its)),
             "", "только человек (от {} с):".format(least)]
    lines += ["  {} {:.2f} с".format(stamp(a), b - a) for a, b in own if b - a >= least]
    lines += ["", "только скилл (от {} с):".format(least)]
    lines += ["  {} {:.2f} с".format(stamp(a), b - a) for a, b in its if b - a >= least]
    return "\n".join(lines)


def main() -> int:
    args = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    args.add_argument("timeline")
    args.add_argument("report")
    args.add_argument("--min", type=float, default=0.25)
    a = args.parse_args()
    try:
        timeline = read(a.timeline)
        cuts = report_cuts(a.report)
    except (TimelineError, ValueError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 1
    print("скорость в таймлайне: {:.3f}".format(timeline["rate"]))
    print(summary(timeline["kept"], invert(cuts, timeline["total"]), a.min))
    return 0


if __name__ == "__main__":
    sys.exit(main())
