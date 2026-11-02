"""The editor's pass (`params.editor`): the whole speech read as an editor reads it, before the cut is final.

Code finds what rules can find, filler words where the seam is safe. Sentences repeated in other words, a thought that
goes nowhere, a slip and its correction take reading: the agent adds them to the items from the text files written here,
the person decides on each. Only the items left in the answer are cut.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence

from .words import norm, quote

SINGLE = {"соответственно", "получается", "собственно", "ну", "короче", "типа", "да"}
PAIRS = {("как", "бы"), ("так", "сказать"), ("в", "общем"), ("в", "принципе"), ("по", "сути"), ("то", "есть")}
MIN_SEAM = 0.04  # seconds of air next to the word: without any, cutting it clips its neighbours
_ENDS = (".", "!", "?", "…")


def _closed(text: str) -> bool:
    return str(text).rstrip().endswith((",",) + _ENDS)


def _safe(words: Sequence[Dict], i: int, j: int) -> bool:
    """Words i..j can go: set off by punctuation on both sides, with air on at least one."""
    if not str(words[j - 1]["text"]).rstrip().endswith(","):
        return False
    if i > 0 and not _closed(words[i - 1]["text"]):
        return False
    before = words[i]["start"] - words[i - 1]["end"] if i > 0 else 1.0
    after = words[j]["start"] - words[j - 1]["end"] if j < len(words) else 1.0
    return max(before, after) >= MIN_SEAM


def find_parasites(words: Sequence[Dict], takes: Sequence[Dict] = ()) -> List[Dict]:
    """[{drop, said, why}]: filler words that can go, outside what is cut already."""
    keys = [norm(w["text"]) for w in words]
    found: List[Dict] = []
    i = 0
    while i < len(words):
        size = 2 if tuple(keys[i:i + 2]) in PAIRS else 1 if keys[i] in SINGLE else 0
        if size and _safe(words, i, i + size):
            a, b = words[i]["start"], words[i + size - 1]["end"]
            if not any(a < t["drop"][1] and t["drop"][0] < b for t in takes):
                found.append({"drop": [a, b], "said": quote(words[i:i + size]), "why": "слово-паразит",
                              "around": quote(words[max(0, i - 4):i + size + 4])})
        i += max(size, 1)
    return found


def write_text(ctx, words: Sequence[Dict], takes: Sequence[Dict]) -> Dict[str, str]:
    """The speech for reading: phrases with their times, and every word with its times to mark a cut exactly."""
    from .words import phrases

    folder = Path(ctx.work)
    folder.mkdir(parents=True, exist_ok=True)
    def cut(w) -> bool:
        return any(t["drop"][0] <= (w["start"] + w["end"]) / 2.0 < t["drop"][1] for t in takes)

    left = [w for w in words if not cut(w)]
    text, table = folder / "текст.txt", folder / "слова.tsv"
    text.write_text("\n".join("{:.2f}–{:.2f} {}".format(p["start"], p["end"], p["text"]) for p in phrases(left)), encoding="utf-8")
    table.write_text("\n".join("{:.3f}\t{:.3f}\t{}".format(w["start"], w["end"], w["text"]) for w in left), encoding="utf-8")
    return {"text": str(text), "words": str(table)}


def plan_editing(ctx, words: Sequence[Dict], takes: Sequence[Dict]) -> List[Dict]:
    """Cuts the person agreed to on top of `takes`; an item without a readable `drop` is left out with a note."""
    if not ctx.p("editor") or not words:
        return []
    payload = dict(write_text(ctx, words, takes), items=find_parasites(words, takes))
    ok, data = ctx.ask("editing", "Редакторский проход: прочитайте text целиком, добавьте в items повторы другими словами, "
                       "оговорки с поправкой и пустые фразы (drop по времени из words). Останется только то, что в items.", payload)
    if not ok:
        return []
    chosen = []
    for it in data.get("items", []):
        drop = it.get("drop") if isinstance(it, dict) else None
        if isinstance(drop, (list, tuple)) and len(drop) == 2 and all(isinstance(x, (int, float)) for x in drop) and drop[0] < drop[1]:
            chosen.append(dict(it, said=str(it.get("said", "")), why=str(it.get("why", "редактор"))))
        else:
            ctx.note("Пункт редакторского прохода пропущен, не понял время: {}".format(it))
    return chosen
