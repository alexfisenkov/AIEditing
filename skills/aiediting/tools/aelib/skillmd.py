"""SKILL.md of a format skill from `templates/format-skill/SKILL.md.tmpl` — only the chosen steps and tools."""
from __future__ import annotations

import re

from .paths import FORMAT_TEMPLATE

GUARD = re.compile(r"<!-- (if|unless) (\w+) -->\n(.*?)<!-- end -->\n", re.S)
APPROVAL = {
    "plan": "«План → готовый ролик»: the pipeline shows the plan (cuts, regions, places) for one approval, "
            "then edits the whole video.",
    "parts": "«По частям» was chosen, but part-by-part editing is not built yet: the pipeline works as "
             "«план → готовый ролик» — every question of the plan first, then the whole video. Say so to the "
             "person before the first run.",
    "auto": "«Без вопросов»: the person asked to see the finished video and nothing before it. See «Without questions».",
}
METHOD_IF = {"editor.md": lambda p: "cut_spans" in p["steps"], "no-questions.md": lambda p: True,
             "graphics.md": lambda p: "graphics" in p["steps"],
             "clips.md": lambda p: {"bands", "teaser", "reedit"} & set(p["steps"]),
             "clips-headline.md": lambda p: "bands" in p["steps"],
             "clips-teaser.md": lambda p: "teaser" in p["steps"],
             "reedit.md": lambda p: "reedit" in p["steps"],
             "takes.md": lambda p: bool((p.get("params") or {}).get("clean_speech")),
             # what is new: each method only for the step the person chose (`prep` has no step: the interview sets `params.prep`)
             "library.md": lambda p: "broll" in p["steps"],
             "broll.md": lambda p: "broll" in p["steps"],
             "sound.md": lambda p: bool({"voice_clean", "music"} & set(p["steps"])),
             "publish.md": lambda p: "publish_pack" in p["steps"],
             "timeline.md": lambda p: "timeline" in p["steps"],
             "angles.md": lambda p: "angles" in p["steps"],
             "prep.md": lambda p: bool((p.get("params") or {}).get("prep")),
             "help.md": lambda p: True}
KIT_SECTIONS = (("graphics", "Graphics"), ("reedit", "Re-edit"))  # the steps that go on outside the pipeline, by their section
KIT_APPROVAL = {
    "Graphics": "«План → готовый ролик»: the pipeline shows the plan for one approval and makes the base video; the graphics then go on "
                "top of it by «Graphics», with no further approval until the result is shown.",
    "Re-edit": "«План → готовые ролики»: the pipeline shows the clips for one approval and makes no video; the clips are then made one "
               "by one by «Re-edit», and each is shown only after its checks.",
}
LATER_WORDS = {"Graphics": ", besides the working folder «Graphics» names",
               "Re-edit": ", besides the working folder «Re-edit» names, which may be the long video's own"}
SHORTS = {"vertical", "bands", "teaser", "reedit", "export_platforms"}
RECORDING = {"takes": "«takes»: the best takes, pauses out", "trim": "«trim»: the recording whole, only its edges go"}
ASR = {"whispercpp": "none — local whisper.cpp", "scribe": "ElevenLabs Scribe",
       "openai_compat": "the OpenAI-compatible address in profile.json", "command": "whatever your own command does"}


def _description(profile: dict) -> str:
    word = profile["format"]
    # What it does and when to call it come first: with many skills installed an agent may keep only the start of a description.
    text = ("Edits a video in the format «{w}»: use when the user says «смонтируй как {w}» or «{n}». Puts the result into "
            "an issue folder, by a profile tuned with its owner. A bare «смонтируй <путь>» names no "
            "format: with several монтаж-* skills installed, ask which format first, do not assume this one. Never "
            "publishes, voices or generates.").format(w=word, n=profile["skill_name"])
    if "reedit" in profile.get("steps", ()):
        text += (" Turns a finished horizontal video into vertical clips rebuilt for 9:16, not shot that way: «из горизонтального "
                 "в вертикальное», «перемонтаж под вертикаль», «нарезка под Reels».")
    return text.replace('"', "'")


def _lines(items, empty: str) -> str:
    return "\n".join(items) if items else empty


def _for_steps(text: str, profile: dict) -> str:
    """A method file may hold lines for some steps only: `<!-- if step -->…<!-- end -->`, `<!-- unless step -->…<!-- end -->`."""
    steps = set(profile["steps"])
    if (profile.get("params") or {}).get("prep"):
        steps.add("prep")
    if not {"blur_regions", "reedit"} & steps:  # not a step: `reedit` keeps secrets out in its own way, and says so
        steps.add("no_blur")
    if SHORTS & steps:  # not a step: the pace of Reels, Shorts and TikTok, for formats that make vertical or short clips
        steps.add("shorts")

    def keep(found):
        wanted = (found.group(2) in steps) == (found.group(1) == "if")
        return found.group(3) if wanted else ""

    return GUARD.sub(keep, text)


def _method(profile: dict) -> str:
    """The parts of «how» only some formats have, one file per part in `templates/format-skill/method/`."""
    return "".join(_for_steps((FORMAT_TEMPLATE / "method" / name).read_text(encoding="utf-8"), profile)
                   for name, wanted in METHOD_IF.items() if wanted(profile))


def _kit_section(profile: dict) -> str:
    return next((name for step, name in KIT_SECTIONS if step in profile["steps"]), "")


def _clean_speech(profile: dict) -> bool:
    return bool((profile.get("params") or {}).get("clean_speech"))


def _approval(profile: dict, section: str) -> str:
    way = profile.get("approval", "plan")
    if not section or way == "auto":
        return APPROVAL.get(way, APPROVAL["plan"])
    if (profile.get("params") or {}).get("recording") == "takes":
        first = "First the person reads the text of the speech from the chosen takes, by «Clean speech». Then: "
        return first + (KIT_APPROVAL[section] if way != "parts" else "«По частям» is not built yet, say so. " + KIT_APPROVAL[section])
    if way == "parts":
        return "«По частям» was chosen, but part-by-part approval is not built yet. Say so to the person before the first run. " + KIT_APPROVAL[section]
    return KIT_APPROVAL[section]


def render(profile: dict, need: dict, steps: dict, tools: dict, version: str, own_method: str = "") -> str:
    """`own_method`: `design/method.md` of a format that has a method no profile describes; it stays in the skill."""
    section = _kit_section(profile)
    step_lines = ["{}. `{}` — {}".format(i, s, steps["steps"][s]["what"])
                  for i, s in enumerate(profile["steps"], 1)]
    tool_lines = ["- {} — {} ({}, пин {})".format(t, tools[t]["skills_section"], tools[t]["license"], tools[t]["pin"])
                  for t in need["tools"]]
    taste = ["- {} · {}: {}".format(t["date"], t.get("video") or "—", t["note"]) for t in profile.get("taste", [])]
    values = {
        "name": profile["skill_name"], "description": _description(profile), "version": version,
        "format": profile["format"], "language": profile.get("language", "ru"),
        "steps": _lines(step_lines, "(no steps)"), "method": _method(profile) + (own_method.rstrip() + "\n\n" if own_method.strip() else ""),
        "approval": _approval(profile, section),
        "taste": _lines(taste, "(none yet)"), "tools": _lines(tool_lines, "- nothing beyond Python"),
        "asr": ASR.get(profile["asr"]["provider"], profile["asr"]["provider"])
        + ("; and what «{}» names".format(section) if section else "")
        + ("; the person's own Auphonic account for the voice (the audio goes there, by their key)" if "voice_clean" in profile["steps"] else ""),
        "writes": LATER_WORDS.get(section, "") + (" and the folder of its clean speech" if _clean_speech(profile) else ""),
        "video_first": ("**First make the clean speech: see «Clean speech». `<video>` here is its `clean-speech.mov`.** "
                        if _clean_speech(profile) else ""),
        "recording": RECORDING.get((profile.get("params") or {}).get("recording"), RECORDING["takes"]),  # after `method`, which holds it
    }
    text = _for_steps((FORMAT_TEMPLATE / "SKILL.md.tmpl").read_text(encoding="utf-8"), profile)
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text
