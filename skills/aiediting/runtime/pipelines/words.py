"""The words of the source: recognised once per run folder, then split into phrases and mapped through cuts."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Dict, List, Sequence

from .kept import alive
from .timeline import Span, to_out

PHRASE_PAUSE = 0.7  # a pause this long ends a phrase even without a full stop
KEPT = ".расшифровка"  # inside the issue folder, stays after the run folder is removed
_END = re.compile(r"[.!?…]$")
_SPACE = re.compile(r"\s+")


def norm(text: str) -> str:
    return re.sub(r"[^\w-]", "", text.lower().replace("ё", "е")).strip("-")


def spoken(transcript: Dict) -> List[Dict]:
    """Words and hesitations with text, in time order (spacing dropped)."""
    return [w for w in (transcript or {}).get("words", []) if w.get("type") != "spacing"
            and str(w.get("text", "")).strip()]


def phrases(words: Sequence[Dict], pause: float = PHRASE_PAUSE) -> List[Dict]:
    """[{start, end, text, words}] split at sentence ends and long pauses."""
    out: List[Dict] = []
    for w in words:
        cur = out[-1] if out else None
        if cur is None or _END.search(cur["words"][-1]["text"]) or w["start"] - cur["end"] >= pause:
            cur = {"start": w["start"], "end": w["end"], "words": []}
            out.append(cur)
        cur["words"].append(w)
        cur["end"] = w["end"]
    for p in out:
        p["text"] = quote(p["words"], 1000)
    return out


def quote(words: Sequence[Dict], n: int = 12) -> str:
    text = " ".join(str(w["text"]).strip() for w in words[:n])
    return _SPACE.sub(" ", text).strip() + (" …" if len(words) > n else "")


def mapped(words: Sequence[Dict], keep: Sequence[Span]) -> List[Dict]:
    """Words whose middle survived the cut (see `kept.alive`), with output times."""
    out = []
    for w in words:
        t = (w["start"] + w["end"]) / 2.0
        if not alive(t, keep):
            continue
        mid, a, b = to_out(t, keep), to_out(w["start"], keep), to_out(w["end"], keep)
        a = mid if a is None else a
        b = mid if b is None else b
        out.append(dict(w, start=a, end=max(a, b)))
    return out


def cache_key(src, cfg: Dict) -> str:
    st = src.stat()
    raw = json.dumps([str(src.resolve()), st.st_size, int(st.st_mtime), cfg], sort_keys=True, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def recognise(ctx, media=None, config=None) -> Dict:
    """Transcript of `media` (the source by default), kept in the run folder so a resumed run reuses it.

    `config` is another recogniser than the profile's `asr`, for a second listening that costs nothing."""
    from .. import asr

    media = media or ctx.src
    cfg = dict(config or ctx.profile.get("asr") or {})
    cfg.setdefault("language", ctx.profile.get("language") or "")
    if not ctx.info["has_audio"]:
        return {"words": [], "language": cfg["language"], "provider": cfg.get("provider", "")}
    folder = ctx.outdir / KEPT if media == ctx.src else ctx.work  # the source's speech outlives the run: it is paid for
    path = folder / "words-{}.json".format(cache_key(media, cfg))
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    result = asr.transcribe(media, cfg)
    folder.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result
