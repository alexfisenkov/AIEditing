"""Words a subtitle line may not end on, and pairs of words a line may not split (Russian speech).

A line never ends on a preposition or a conjunction that opens what follows, and rarely on a possessive
before its noun; a compound conjunction («потому что», «для того чтобы»), a glossary phrase and a name
(«Claude Code», «Opus 4.5») stay whole.
"""
from __future__ import annotations

import re
from typing import Dict, List, Set

CLINGS = {
    # prepositions, simple and compound
    "без", "безо", "в", "во", "вне", "для", "до", "за", "из", "изо", "из-за", "из-под", "к", "ко", "кроме",
    "между", "меж", "на", "над", "надо", "о", "об", "обо", "около", "от", "ото", "перед", "передо", "по",
    "под", "подо", "после", "при", "про", "ради", "с", "со", "среди", "сквозь", "у", "через", "вокруг",
    "вместо", "возле", "вдоль", "внутри", "напротив", "против", "мимо", "насчёт", "насчет", "благодаря",
    "согласно", "вроде", "ввиду", "вследствие",
    # conjunctions and particles that open what follows
    "а", "и", "но", "да", "или", "либо", "ни", "не", "что", "чтобы", "как", "если", "когда", "пока", "хотя",
    "чем", "будто", "словно", "ли", "ведь", "зато", "однако", "тоже", "также",
}
_CASES = ("его", "ей", "ему", "им", "ем", "их", "ими")
POSSESSIVES = {  # forms as bare() gives them: «своё» is «свое»
    *(stem + end for stem in ("мо", "тво", "сво") for end in ("й", "я", "е", "ю", "и") + _CASES),
    *(stem + end for stem in ("наш", "ваш") for end in ("", "а", "е", "у", "и") + _CASES),
}
OPENS = {"и", "а", "но", "или", "что", "чтобы", "потому", "поэтому", "который", "которая", "которое",
         "которые", "если", "когда", "где", "куда", "пока", "хотя", "тогда", "то", "так", "для", "после"}
COMPOUNDS = [p.split() for p in (
    "потому что", "оттого что", "для того чтобы", "для того что", "так что", "так как", "то что", "то есть",
    "после того как", "до того как", "перед тем как", "с тем чтобы", "в то время как", "несмотря на то что",
    "так же как", "как будто", "тем более что", "вместо того чтобы", "кроме того", "в том числе")]
ABBREVIATIONS = re.compile(r"(?:^|\b)(?:т\.е|т\.д|т\.п|т\.к|т\.н|др|см|напр|рис|стр|гл)\.$", re.IGNORECASE)
_END = re.compile(r"[.!?…]$")
_ELLIPSIS = re.compile(r"(?:\.\.\.|…)$")
_LATIN_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9.+#-]*$")
_VERSION = re.compile(r"^v?\d+(?:\.\d+)*[a-z]?$", re.IGNORECASE)
_TRAIL = ".,!?…:;»)"


def bare(text: str) -> str:
    """A word without punctuation, lower case, ё as е — for comparing."""
    return re.sub(r"[^\w-]+", "", text.lower().replace("ё", "е")).strip("-")


def bare_phrase(text: str) -> List[str]:
    return [bare(w) for w in text.split() if bare(w)]


def sentence_end(text: str) -> bool:
    """A word that ends a sentence: «.», «!», «?», «…» — not «т.е.» or «и т.д.»."""
    return bool(_END.search(text)) and not ABBREVIATIONS.search(text)


def capital_after(previous: str, text: str) -> bool:
    """Should `text` get a capital letter after `previous` («» at the very start)?

    Not after an ellipsis (a pause inside a sentence), and never in a word that keeps its own case
    («iCloud», «macOS», «n8n»)."""
    if previous and (not sentence_end(previous) or _ELLIPSIS.search(previous)):
        return False
    return text[:1].islower() and not any(c.isupper() or c.isdigit() for c in text[1:])


def _phrases(glossary: Dict[str, str]) -> List[List[str]]:
    found = [bare_phrase(t) for pair in glossary.items() for t in pair]
    return [p for p in found if len(p) > 1] + COMPOUNDS


def glued(texts: List[str], glossary: Dict[str, str]) -> Set[int]:
    """Indexes i where words i and i+1 must stay on one line."""
    words = [bare(t) for t in texts]
    out: Set[int] = set()
    for phrase in _phrases(glossary):
        for i in range(len(words) - len(phrase) + 1):
            if words[i:i + len(phrase)] == phrase and not any(texts[k][-1:] in _TRAIL for k in range(i, i + len(phrase) - 1)):
                out.update(range(i, i + len(phrase) - 1))
    for i, (a, b) in enumerate(zip(texts, texts[1:])):  # a name runs on: «Gemini 2.5 Pro», «iPhone 17 Pro»
        b = b.rstrip(_TRAIL)
        head = _name(a) or (_VERSION.match(a) and i - 1 in out)
        if head and a[-1:] not in _TRAIL and (_name(b) or _VERSION.match(b)):
            out.add(i)
    return out


def _name(word: str) -> bool:
    """A Latin name: a capital or a digit somewhere in it («Claude», «iPhone», «n8n»), not «npm»."""
    return bool(_LATIN_NAME.match(word)) and any(c.isupper() or c.isdigit() for c in word)
