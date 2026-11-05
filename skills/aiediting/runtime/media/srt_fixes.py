"""The glossary and the person's corrections, on the words themselves, before they are broken into subtitles.

So a correction does not depend on where a subtitle breaks, and the `.srt` and the words file say the same. A correction is
matched against the text as the person sees it, after the glossary. `replace` is exact: whole words, the case as it stands,
everywhere it occurs. `at` is one place, near a second of the finished video. An empty `to` takes the words out. One pass over the
words: what a correction wrote is not corrected again. What found no words is returned, never dropped in silence.
"""
from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .srt_words import sentence_end

HEAD = "«([\"'"
TRAIL = ".,!?…:;»)]\"'"
EDGE = HEAD + TRAIL + "—–"
NEAR = 6.0  # seconds: how far from `t` an `at` correction looks


def checked(corrections: Optional[Dict]) -> Dict:
    """The corrections in their one shape; a wrong one says so before a long render, not after it. ValueError."""
    corrections = corrections or {}
    replace, rows = corrections.get("replace") or {}, corrections.get("at") or []
    if not isinstance(replace, dict) or not isinstance(rows, list):
        raise ValueError("Правки субтитров: replace — словарь {\"как услышано\": \"как надо\"}, at — список")
    out = []
    for row in rows:
        if not isinstance(row, dict) or isinstance(row.get("t"), bool) or not isinstance(row.get("t"), (int, float)) \
                or not str(row.get("from") or "").split():
            raise ValueError("Правка at: нужны t (секунда числом), from и to: {}".format(row))
        out.append({"t": float(row["t"]), "from": str(row["from"]), "to": str(row.get("to") or "")})
    return {"replace": {str(k): str("" if v is None else v) for k, v in replace.items() if str(k).split()}, "at": out}


def _exact(found: str, wanted: str) -> bool:
    """A word of the correction written with its punctuation is compared with it; written bare, without."""
    return found == wanted or (wanted == wanted.strip(EDGE) and found.strip(EDGE) == wanted)


def _loose(found: str, wanted: str) -> bool:
    return found.strip(EDGE).lower() == wanted.strip(EDGE).lower()


def _here(tokens: Sequence[dict], i: int, words: Sequence[str], same: Callable[[str, str], bool]) -> bool:
    return bool(words) and i + len(words) <= len(tokens) and all(same(tokens[i + j]["text"], w) for j, w in enumerate(words))


def _places(tokens: Sequence[dict], words: Sequence[str], same: Callable[[str, str], bool]) -> List[int]:
    return [i for i in range(len(tokens)) if _here(tokens, i, words, same)]


def _head(text: str) -> str:
    return text[:len(text) - len(text.lstrip(HEAD))]


def _tail(text: str) -> str:
    return text[len(text.rstrip(TRAIL)):]


def _renewed(found: Sequence[dict], to: str) -> List[dict]:
    """The found words become the words of `to`, over the same time, shared by their length. Their punctuation stays."""
    new = to.split()
    if not new:
        return []
    head, tail = _head(found[0]["text"]), _tail(found[-1]["text"])
    if head and not _head(new[0]):
        new[0] = head + new[0]
    if tail and not _tail(new[-1]):
        new[-1] += tail
    a, b = float(found[0]["start"]), float(found[-1]["end"])
    total, at, made = sum(len(w) for w in new), a, []
    for word in new:
        end = at + (b - a) * len(word) / total
        made.append(dict(found[0], text=word, start=at, end=end))
        at = end
    return made


def _marked(tokens: Sequence[dict], rows: Sequence[dict], missed: List[dict]) -> Dict[int, Tuple[int, str, str]]:
    """`at`: the one place of each, on the words as they are."""
    marks: Dict[int, Tuple[int, str, str]] = {}
    for row in rows:
        words = row["from"].split()
        places = sorted(_places(tokens, words, _exact), key=lambda i: abs(tokens[i]["start"] - row["t"]))
        if not places or abs(tokens[places[0]]["start"] - row["t"]) > NEAR:
            why = "ближайшее на {:.1f} с".format(tokens[places[0]]["start"]) if places else _hint(tokens, words)
            missed.append({"from": row["from"], "to": row["to"], "at": row["t"], "why": why})
        elif any(i <= places[0] < i + m[0] or places[0] <= i < places[0] + len(words) for i, m in marks.items()):
            missed.append({"from": row["from"], "to": row["to"], "at": row["t"], "why": "это место уже занято другой правкой at"})
        else:
            marks[places[0]] = (len(words), row["to"], row["from"])
    return marks


def _hint(tokens: Sequence[dict], words: Sequence[str]) -> str:
    near = _places(tokens, words, _loose)
    return "в тексте есть «{}» на {:.1f} с: сверяйте с .srt, регистр и слова точно".format(
        " ".join(t["text"] for t in tokens[near[0]:near[0] + len(words)]), tokens[near[0]]["start"]) if near else ""


def corrected(tokens: List[dict], corrections: Optional[Dict]) -> Tuple[List[dict], List[dict], List[dict]]:
    """(tokens as corrected, what changed [{start, from, to}], what to look at [{from, to, why}]). A row with `soft` did apply, but
    the same words in another case stayed as they are."""
    corrections = checked(corrections)
    changed: List[dict] = []
    missed: List[dict] = []
    marks = _marked(tokens, corrections["at"], missed)
    wanted = sorted(((w.split(), r, w) for w, r in corrections["replace"].items()), key=lambda row: -len(row[0]))
    hits = {w: 0 for _, _, w in wanted}
    out: List[dict] = []
    i, capital = 0, False
    while i < len(tokens):
        found = marks.get(i)
        if found is None:
            row = next((r for r in wanted if _here(tokens, i, r[0], _exact)), None)
            if row is None:
                token = tokens[i]
                if capital and token["text"][:1].islower():  # a sentence goes on from its next word
                    token = dict(token, text=token["text"][:1].upper() + token["text"][1:])
                out.append(token)
                i, capital = i + 1, False
                continue
            found = (len(row[0]), row[1], row[2])
            hits[row[2]] += 1
        n, to, label = found
        part = tokens[i:i + n]
        changed.append({"start": part[0]["start"], "from": label, "to": to})
        made = _renewed(part, to)
        if not made:
            tail = _tail(part[-1]["text"])
            if tail and out and not _tail(out[-1]["text"]):
                out[-1] = dict(out[-1], text=out[-1]["text"] + tail)
            capital = capital or (part[0]["text"][:1].isupper() and (not out or sentence_end(out[-1]["text"])))
        else:
            if capital and made[0]["text"][:1].islower():
                made[0] = dict(made[0], text=made[0]["text"][:1].upper() + made[0]["text"][1:])
            capital = False
        out += made
        i += n
    for words, right, wrong in wanted:
        if not hits[wrong]:
            missed.append({"from": wrong, "to": right, "why": _hint(tokens, words)})
        elif len(_places(tokens, words, _loose)) > hits[wrong]:
            missed.append({"from": wrong, "to": right, "soft": True,
                           "why": "сделано {} мест, в другом регистре осталось ещё".format(hits[wrong])})
    return out, sorted(changed, key=lambda c: c["start"]), missed


def glossed(tokens: List[dict], glossary: Optional[Dict[str, str]]) -> Tuple[List[dict], List[dict]]:
    """(tokens with the glossary, what it changed [{start, from, to}]). A brand everywhere, whatever its case. A longer phrase goes
    first («клод код» before «клод»), and a phrase with punctuation inside it is not that phrase."""
    tokens, changed = list(tokens), []
    for wrong in sorted(glossary or {}, key=lambda k: -len(k.split())):
        words, right = wrong.split(), glossary[wrong]
        if len(words) == 1:
            pattern = re.compile(r"(?<!\w){}(?!\w)".format(re.escape(wrong)), re.IGNORECASE)
            for k, token in enumerate(tokens):
                changed += [{"start": token["start"], "from": m.group(0), "to": right} for m in pattern.finditer(token["text"])
                            if m.group(0) != right]
                tokens[k] = dict(token, text=pattern.sub(lambda _m: right, token["text"]))
            continue
        for i in reversed(_places(tokens, words, _loose)):
            part = tokens[i:i + len(words)]
            if not any(_tail(t["text"]) for t in part[:-1]):
                text = " ".join(t["text"].strip(EDGE) for t in part)
                if text != right:
                    changed.append({"start": part[0]["start"], "from": text, "to": right})
                tokens[i:i + len(words)] = _renewed(part, right)
    return tokens, changed
