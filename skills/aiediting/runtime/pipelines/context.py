"""Everything one run knows: the source, the profile, the decisions so far, and what goes into the report."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional

from ..media import probe
from .errors import PipelineError
from .words import recognise

WORK = ".aiediting-run"  # inside the issue folder: nothing is ever written anywhere else


class Context:
    def __init__(self, src, profile: Dict, outdir, approve: Callable[[str, dict], bool], screen=None):
        self.src = Path(src).resolve()
        if not self.src.is_file():
            raise PipelineError("Нет исходника: {}".format(self.src))
        self.profile, self.approve = profile, approve
        self.params: Dict = dict(profile.get("params") or {})
        self.steps: List[str] = list(profile.get("steps") or [])
        self.outdir = Path(outdir).resolve()
        if not self.steps:
            raise PipelineError("В профиле нет ни одного шага.")
        self.work = self.outdir / WORK
        self.screen = Path(screen).resolve() if screen else None
        self.info = probe(self.src)
        self.keep = [(0.0, self.info["duration"])]
        self.layout: Optional[Dict] = None
        self.candidates: List[Dict] = []   # secret-looking places found (source time)
        self.regions: List[Dict] = []      # areas the person ticked for blur (source time)
        self.motion: List[Dict] = []       # approved zoom / side-by-side places (source time)
        self.overlays: List[Dict] = []     # chapters, cards (source time); captions are per piece
        self.pieces: Optional[List[Dict]] = None  # vertical clips; None = one video of the whole source
        self.music: Dict = {}
        self.chapters: List[Dict] = []
        self.srt_glossary: Dict[str, str] = {}
        self.decisions: List[Dict] = []
        self.notes: List[str] = []
        self.report: Dict = {"cuts": [], "blurred": [], "fixes": [], "drift_ms": 0.0, "chapters": [],
                             "motion": [], "clips": [], "words_lost": [], "outputs": [], "exports": []}
        self.loud: Optional[List] = None   # loud stretches of the source, once `speech_spans` has measured them
        self._words: Optional[Dict] = None
        self._timed = False

    def has(self, step: str) -> bool:
        return step in self.steps

    def p(self, name: str, default=None):
        value = self.params.get(name)
        return default if value is None else value

    def transcript(self) -> Dict:
        if self._words is None:
            self._words = recognise(self)
        if self.loud is not None and not self._timed:
            self._check_times()
        return self._words

    def _check_times(self) -> None:
        from .cutplan import _fillers
        from .word_times import repaired

        self._timed = True
        self._words, moved = repaired(self._words, self.loud, float(self.p("pad", 0.12)),
                                      lambda w: w.get("type") == "filler" or bool(_fillers(self, [w])))
        if moved:
            self.note("Время слов поправлено по звуку, распознавание поставило их мимо речи ({}): {}".format(
                len(moved), "; ".join(moved[:10]) + (" …" if len(moved) > 10 else "")))

    def note(self, text: str) -> None:
        if text not in self.notes:
            self.notes.append(text)

    def design(self, vertical: bool = False) -> Dict:
        from ..render import load_design
        from ..render.design import default_design

        own = self.profile.get("design")
        root = Path(own) if own else None
        if root is not None and not root.is_absolute():
            root = Path(__file__).resolve().parent.parent.parent / root
        d = dict(load_design(root if root is not None and (root / "tokens.json").is_file() else default_design()))
        if vertical:
            from ..media.export import safe_zone

            mine, shared = d.get("video", {}).get("safe_zone_vertical", {}), safe_zone()
            video = dict(d["video"])
            video["safe_zone_vertical"] = {k: max(float(mine.get(k, 0)), v) for k, v in shared.items()}
            d["video"] = video
        return d

    def ask(self, key: str, question: str, payload: Dict):
        from .asking import ask

        return ask(self, key, question, payload)
