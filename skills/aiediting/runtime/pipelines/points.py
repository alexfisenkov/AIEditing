"""What counts as a point of a list: not filler, not a service word, not a word cut off mid-way."""
from __future__ import annotations

from typing import List

AND = ("и", "а", "или", "and", "or")
ITEM_WORDS, MAX_ITEMS = 4, 6  # words in a point, points in an insert
STOP = {"ну", "короче", "да", "вот", "там", "например", "значит", "это", "я", "типа", "как", "такие", "такой",
        "так", "в", "на", "с", "и", "а", "но", "же", "ли", "бы", "то", "естественно", "кстати", "собственно",
        "вообще", "просто", "уже", "еще", "ещё", "мы", "вы", "он", "она", "они", "все", "всё", "у", "нас",
        "что", "эти", "этот", "м", "э", "ээ", "мм", "э-э", "м-м", "что-то", "чтобы", "который", "которые",
        "которое", "когда", "если", "потому", "даже"}


def clean(text: str) -> str:
    return str(text).strip().strip(".,;:!?…«»\"'()—")


def split_and(chunk: List[str]) -> List[List[str]]:
    """«spec и plan» → spec, plan: the last point of a list often comes with «и»."""
    parts: List[List[str]] = [[]]
    for w in chunk:
        if w.lower() in AND:
            parts.append([])
        else:
            parts[-1].append(w)
    return [p for p in parts if p]


def content(part: List[str]) -> List[str]:
    """The point without filler and service words at its ends; [] when nothing meaningful is left."""
    words = list(part)
    while words and words[0].lower() in STOP:
        words.pop(0)
    while words and (words[-1].lower() in STOP or len(words[-1]) < 2):
        words.pop()
    if any(w.endswith("-") for w in words):  # a word cut off mid-way («чело--»): not a point
        return []
    return words if any(len(w) > 2 and w.lower() not in STOP for w in words) else []
