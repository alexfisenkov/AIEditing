"""The `broll` step: pictures from the person's library (or free stock) under the sense of the phrases, by an editor's rules.

Planned from the words and the cut; laid over the cut video by `media/broll.py` before the plates and the speed-up.
A place no picture fits becomes a line of `досъёмка.md`. A frame the person's list of never-shows names is never used.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from ..library import inventory, rules, search
from ..library.paths import find_library
from ..media.vertical import shown_size
from . import broll_place as place
from .broll_answer import kind_of, settle
from .broll_stock import Stock
from .timeline import to_out
from .words import phrases, quote, spoken

EVERY = 20.0   # seconds between the starts of two inserts, unless `params.broll.every` says otherwise
PLACES = 8     # how many places without a frame one run asks to shoot
QUESTION = ("Вставки: проверьте кадры под фразы. Ненужную строку уберите или поставьте ok: false; у строки без файла "
            "поле want — что снять, оно попадёт в досъёмку.")
_YEAR = re.compile(r"\b((?:19|20)\d{2})\b")


def _settings(ctx) -> Optional[Dict]:
    raw = ctx.p("broll")
    if raw is not True and not isinstance(raw, dict):
        return None
    mine = raw if isinstance(raw, dict) else {}
    return {"stock": bool(mine.get("stock")), "every": float(mine.get("every", EVERY)),
            "max_run": int(mine.get("max_run", place.MAX_RUN))}


def _usable(lib: Path, row: Dict, never: List[str]) -> bool:
    return (row.get("orient") == "гор" and not row.get("never") and not search.blocked(row, never)
            and place.piece_of(row) is not None and inventory.file_of(lib, row).is_file())


def _source_at(t: float, keep) -> float:
    """The moment of the source that plays at second `t` of the cut video (at a cut: the span that follows it)."""
    passed = 0.0
    for a, b in keep:
        if t < passed + (b - a) - 1e-9:
            return a + (t - passed)
        passed += b - a
    return keep[-1][1]


def _content(phrase: Dict) -> bool:
    """A phrase worth a picture: several words, and some of them about something."""
    return len(phrase["words"]) >= 3 and len(search.stems(phrase["text"])) >= 2


def _clear(at: float, length: float, taken: List[Dict], every: float) -> bool:
    """Starts `every` seconds apart at least, and no two inserts over each other."""
    return not any(abs(at - t["at"]) < every or (at < t["at"] + t["len"] and t["at"] < at + length) for t in taken)


def _frame(it: Dict, marks, total, used, taken, every) -> Optional[Dict]:
    for row in sorted(it["cands"], key=lambda r: r["f"] in used):  # a file not yet used goes first, the score order stays
        got = place.piece_of(row)
        spot = place.fit(it["at"], it["want"], got[1], marks, total)
        if spot and _clear(spot[0], spot[1], taken, every):
            return {"p": it["p"], "at": spot[0], "len": spot[1], "row": row, "from": got[0], "hit": None,
                    "options": [c["f"] for c in it["cands"] if c is not row][:3]}
    return None


def _bare(it: Dict, marks, total, stock, taken, every) -> Optional[Dict]:
    hit = stock.find(it["p"]["text"]) if stock else None
    spot = place.fit(it["at"], it["want"], min(place.MAX_LEN, hit["dur"]) if hit else place.MAX_LEN, marks, total)
    if spot is None and hit:
        hit, spot = None, place.fit(it["at"], it["want"], place.MAX_LEN, marks, total)
    if spot is None or not _clear(spot[0], spot[1], taken, every):
        return None
    return {"p": it["p"], "at": spot[0], "len": spot[1], "row": None, "from": 0.0, "hit": hit, "options": []}


def _slots(ctx, mine: Dict, rows: List[Dict], never: List[str], stock) -> List[Dict]:
    marks, total = place.seams(ctx.keep), sum(b - a for a, b in ctx.keep)
    found, bare = [], []
    for p in phrases(spoken(ctx.transcript())):
        at = to_out(p["start"], ctx.keep)
        if at is None:
            continue
        year = _YEAR.search(p["text"])
        it = {"p": p, "at": at, "want": p["end"] - p["start"]}
        cands = search.candidates(rows, p["text"], int(year.group(1)) if year else None, 4, never)
        if cands:
            found.append(dict(it, cands=cands, score=cands[0]["score"]))
        elif _content(p):
            bare.append(it)
    taken: List[Dict] = []
    for it in sorted(found, key=lambda x: (-x["score"], x["at"])):
        slot = _frame(it, marks, total, {t["row"]["f"] for t in taken if t["row"]}, taken, mine["every"])
        if slot:
            taken.append(slot)
    asked = 0
    for it in bare:
        slot = _bare(it, marks, total, stock, taken, mine["every"]) if asked < PLACES else None
        if slot:
            taken.append(slot)
            asked += 1
    return place.limit_run(taken, mine["max_run"])


def _line(slot: Dict, keep) -> Dict:
    """One row of the question, in the time of the source (what the person hears), with the cut-video second beside it."""
    p, row, hit = slot["p"], slot["row"], slot["hit"]
    start = _source_at(slot["at"], keep)
    out = {"start": round(start, 3), "end": round(start + slot["len"], 3), "at": slot["at"], "phrase": p["text"],
           "kind": "none", "file": "", "from": slot["from"], "who": [], "what": "", "where": "", "options": slot["options"]}
    if row:
        out.update(kind=kind_of(row), file=row["f"], who=list(row.get("who") or []), what=row.get("what") or "",
                   where=row.get("where") or "")
    elif hit:
        out.update(kind="stock", what=hit["query"], stock={"provider": hit["provider"], "id": hit["id"]})
    else:
        out["want"] = "Кадр под слова «{}»".format(quote(p["words"], 8).rstrip(" …"))
    return out


def plan_broll(ctx) -> None:
    mine = _settings(ctx)
    lib = find_library() if mine else None
    if lib is None or ctx.pieces:
        return
    w, h = shown_size(ctx.info)
    if h > w:  # only horizontal inserts go into a horizontal frame, and a vertical one gets none here
        return
    never = rules.forbidden(lib)
    rows = [r for r in inventory.load(lib) if _usable(lib, r, never)]
    stock = Stock(ctx, lib) if mine["stock"] else None
    if not rows and stock is None:
        return
    slots = _slots(ctx, mine, rows, never, stock)
    if not slots:
        return
    lines = [_line(s, ctx.keep) for s in sorted(slots, key=lambda s: s["at"])]
    payload = {"rows": lines, "rules": rules.rules_text(lib, ctx.profile.get("format")), "never": never}
    if getattr(ctx.approve, "auto", False):  # no questions: as proposed, and the decision is in the report
        ctx.decisions.append({"key": "broll", "question": QUESTION, "ok": True})
    else:
        ok, payload = ctx.ask("broll", QUESTION, payload)
        if not ok:
            return
    settle(ctx, lib, payload, stock, {r["f"]: r for r in inventory.load(lib)}, never,
            {l["start"]: l["file"] for l in lines})


def lay(ctx, piece: Dict, cur, tmp: Path):
    """Over the cut video of this piece (render.py): the inserts of the plan whose start survived the cut."""
    from .. import media
    from ..media.broll import lay_broll

    items = []
    for b in ctx.broll:
        at = to_out(b["start"], piece["keep"])
        if at is not None:
            items.append(dict(b, start=at, end=at + b["end"] - b["start"]))
    if not items:
        return cur
    out = lay_broll(cur, items, tmp / "4б-вставки.mp4", media.probe(cur))
    ctx.report["broll"] += [{"at": i["start"], "end": i["end"], "phrase": i["phrase"], "shown": i["shown"],
                             "who": i["who"], "kind": i["kind"]} for i in items]
    return out
