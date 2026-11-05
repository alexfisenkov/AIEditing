"""The sidecar .srt: brand fixes by the profile glossary, the person's corrections, one set of final words."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .errors import PipelineError
from .speed import rate_of, scaled_words
from .words import KEPT, mapped, spoken

QUESTION = ("Вычитайте субтитры (draft): ослышки, произношение, бренды, перевод. Исправления — в replace как "
            "{\"как услышано\": \"как надо\"}: слова и регистр точно как в черновике, правится всюду, где это есть; "
            "одно место — в at как [{\"t\": секунда, \"from\": \"как услышано\", \"to\": \"как надо\"}]; пустое to убирает слова. "
            "Они попадут в .srt, в слова-таймкоды и в отчёт; сам .srt руками не правится.")
FINAL_WORDS = "итог-слова.json"  # inside KEPT: `run.py subtitles` corrects the text again without another render
WORDS_FILE = "слова-таймкоды.txt"


def plan_srt(ctx) -> None:
    from ..media import write_srt
    from ..media.srt_fixes import checked

    ctx.srt_glossary = dict(ctx.p("glossary", {}) or {})
    words = scaled_words(mapped(ctx.transcript().get("words", []), ctx.keep), rate_of(ctx.p("speed", 1.0)))
    draft = ctx.work / "черновик.srt"
    fixes = write_srt({"words": words}, draft, ctx.srt_glossary)
    ok, data = ctx.ask("srt", QUESTION, {"draft": str(draft), "fixes": fixes, "replace": {}, "at": []})
    if ok:
        try:
            ctx.srt_corrections = checked({"replace": data.get("replace"), "at": data.get("at")})
        except ValueError as e:  # said now, not after the render
            raise PipelineError(str(e))


def write_final(ctx, words: List[Dict], out) -> List[Dict]:
    """The `.srt` of a finished video from its words in that video's seconds; a later hearing of the same video replaces them."""
    from ..media import write_srt

    ctx.__dict__.setdefault("final_words", {})[Path(out).name] = words
    return write_srt({"words": words}, out, ctx.srt_glossary, getattr(ctx, "srt_corrections", None))


def write_piece_srt(ctx, keep, out) -> Dict:
    words = scaled_words(mapped(ctx.transcript().get("words", []), keep), rate_of(ctx.p("speed", 1.0)))
    fixes = write_final(ctx, words, out)
    return {"path": out, "fixes": fixes, "words": len(spoken({"words": words}))}


def _found_nowhere(final: Dict[str, List[Dict]], glossary: Dict[str, str], corrections: Dict) -> List[Dict]:
    """Several clips: a correction is only for the clip that has those words, so it is lost only when no clip has them."""
    from ..media.srt import missed_corrections

    rows = [missed_corrections(words, glossary, corrections) for words in final.values()]
    if not rows:
        return []
    soft = [r for row in rows for r in row if r.get("soft")]
    hard = [r for r in rows[0] if not r.get("soft")
            and all(any(o["from"] == r["from"] and not o.get("soft") for o in row) for row in rows)]
    return hard + soft


def keep_final_words(ctx) -> None:
    """At the end of a run: what `run.py subtitles` starts from, and a word about each correction that found nothing."""
    final = getattr(ctx, "final_words", None)
    if not final:
        return
    folder = ctx.outdir / KEPT
    folder.mkdir(parents=True, exist_ok=True)
    (folder / FINAL_WORDS).write_text(json.dumps(final, ensure_ascii=False), encoding="utf-8")
    for row in _found_nowhere(final, getattr(ctx, "srt_glossary", {}), getattr(ctx, "srt_corrections", None)):
        head = "Правка субтитров: проверьте" if row.get("soft") else "Правка субтитров не применилась"
        ctx.note("{}: «{}» → «{}»{}".format(head, row["from"], row["to"], ": " + row["why"] if row["why"] else ""))


def rewrite(folder, glossary: Dict[str, str], corrections: Dict) -> Dict:
    """The text again from the kept words: every `.srt` of the issue folder and the words file, with no render."""
    from ..media import write_srt
    from ..media.srt_fixes import checked

    folder = Path(folder)
    kept = folder / KEPT / FINAL_WORDS
    if not kept.is_file():
        raise FileNotFoundError("В {} нет {}: сначала run.py edit на этой версии скилла".format(folder, kept.name))
    corrections = checked(corrections)
    final, done = json.loads(kept.read_text(encoding="utf-8")), {"fixes": [], "words_file": False}
    for name, words in final.items():
        done["fixes"] += write_srt({"words": words}, folder / name, glossary, corrections)
    done["missed"] = _found_nowhere(final, glossary, corrections)
    words_file = folder / WORDS_FILE
    if words_file.is_file() and len(final) == 1:
        write_words_file(words_file, next(iter(final.values())), glossary, corrections)
        done["words_file"] = True
    return done


def write_words_file(path, words: List[Dict], glossary: Dict[str, str], corrections: Dict) -> None:
    from ..media.srt import final_tokens

    tokens = final_tokens(words, glossary, corrections)
    Path(path).write_text("".join("{:7.2f} {}\n".format(t["start"], t["text"]) for t in tokens), encoding="utf-8")
