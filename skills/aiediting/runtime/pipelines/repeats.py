"""Repeats in a row: the same one, two or three words said twice («в этом в этом году»), offered for the plan.

Code finds only the exact repeat; the earlier one is the candidate to cut. The person decides on each: the rows left
in the answer are cut, «no» keeps them all. Asked with `params.cleanup = "gentle"` or `params.repeats`.
"""
from __future__ import annotations

from typing import Dict, List, Sequence

from .words import norm, quote

LONGEST = 3       # words in a repeated group
MAX_GAP = 1.0     # s between the two: further apart it is speech, not a stumble


def find(words: Sequence[Dict]) -> List[Dict]:
    """[{drop: [start of the first, start of the second], said, why: "повтор"}], longest groups first."""
    said = [w for w in words if w.get("type") != "filler" and norm(w["text"])]
    keys = [norm(w["text"]) for w in said]
    found: List[Dict] = []
    i = 0
    while i < len(said):
        for n in range(LONGEST, 0, -1):
            first, second = keys[i:i + n], keys[i + n:i + 2 * n]
            if len(second) == n and first == second and said[i + n]["start"] - said[i + n - 1]["end"] <= MAX_GAP:
                found.append({"drop": [said[i]["start"], said[i + n]["start"]], "said": quote(said[i:i + 2 * n]),
                              "why": "повтор"})
                i += n
                break
        else:
            i += 1
    return found


def plan_repeats(ctx, words: Sequence[Dict], takes: Sequence[Dict]) -> List[Dict]:
    """The repeats the person agreed to cut, outside what is cut already."""
    if not (ctx.p("cleanup") == "gentle" or ctx.p("repeats")) or not words:
        return []
    rows = [r for r in find(words) if not any(r["drop"][0] < t["drop"][1] and t["drop"][0] < r["drop"][1] for t in takes)]
    if not rows:
        return []
    ok, data = ctx.ask("repeats", "Повторы подряд: строка, оставленная в items, вырезается (первый раз из двух); "
                       "уберите строки, где повтор нужен; «нет» — оставить все.", {"items": rows})
    if not ok:
        return []
    chosen = []
    for row in data.get("items", []):
        drop = row.get("drop") if isinstance(row, dict) else None
        if isinstance(drop, (list, tuple)) and len(drop) == 2 and all(isinstance(x, (int, float)) for x in drop) and drop[0] < drop[1]:
            chosen.append({"drop": [float(drop[0]), float(drop[1])], "said": str(row.get("said", "")), "why": "повтор"})
        else:
            ctx.note("Строка повторов пропущена, не понял время: {}".format(row))
    return chosen
