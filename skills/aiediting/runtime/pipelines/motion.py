"""Close-ups and «camera aside, screen aside» by the layout and by what is said; only approved places move.

face_full — a gentle zoom on the face; screen_face_window — nothing (screen zoom is a profile option);
separate_tracks — the camera and the screen side by side where something is shown.
Profile: params.zoom_face / params.moves = false turn the face zoom / the side-by-side off.
"""
from __future__ import annotations

from typing import Dict, List

from .words import norm, phrases, spoken

CUES = ["смотрите", "посмотрите", "вот здесь", "вот тут", "обратите внимание", "видите", "look", "see here"]
MIN_S, MAX_S = 2.0, 6.0


def _places(ctx) -> List[Dict]:
    cues = [norm_phrase(c) for c in ctx.p("motion_cues", CUES)]
    found = []
    for p in phrases(spoken(ctx.transcript())):
        keys = [norm(w["text"]) for w in p["words"]]
        for i in range(len(keys)):
            hit = next((c for c in cues if keys[i:i + len(c)] == c), None)
            if hit:
                start = p["words"][i]["start"]
                end = min(max(p["end"] + 0.3, start + MIN_S), start + MAX_S)
                found.append({"start": round(start, 3), "end": round(end, 3), "cue": " ".join(hit),
                              "said": p["text"]})
                break
    return found


def norm_phrase(text: str) -> List[str]:
    return [norm(w) for w in text.split() if norm(w)]


def plan_motion(ctx) -> None:
    kind = (ctx.layout or {}).get("kind")
    if kind == "screen_face_window":
        if ctx.p("zoom_screen"):
            ctx.note("Укрупнение экрана включено в профиле, но в этой версии не делается: не задано, куда приближать")
        return
    if kind == "separate_tracks" and ctx.screen is None and ctx.p("moves") is not False:
        ctx.note("Раздельные дорожки: файл экрана не передан — движения «камера в бок, экран в бок» нет")
        return
    if kind not in ("face_full", "separate_tracks"):
        return
    if ctx.p("zoom_face" if kind == "face_full" else "moves") is False:  # the interview said no
        return
    places = _places(ctx)
    if not places:
        return
    what = "укрупнение лица" if kind == "face_full" else "камера в бок, экран рядом"
    ok, data = ctx.ask("motion", "Места для движения ({}): оставьте в items нужные.".format(what),
                       {"layout": kind, "move": what, "items": places})
    if ok:
        ctx.motion = [dict(it, move="zoom" if kind == "face_full" else "side") for it in data.get("items", [])]
