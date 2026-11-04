"""SKILL.md of a format skill from `templates/format-skill/SKILL.md.tmpl` — only the chosen steps and tools."""
from __future__ import annotations

from .paths import FORMAT_TEMPLATE

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
             "takes.md": lambda p: bool((p.get("params") or {}).get("clean_speech"))}
ASR = {"whispercpp": "none — local whisper.cpp", "scribe": "ElevenLabs Scribe",
       "openai_compat": "the OpenAI-compatible address in profile.json", "command": "whatever your own command does"}


def _description(profile: dict) -> str:
    word = profile["format"]
    text = ("Edits a video as «{w}» by a profile tuned with its owner, and puts the result into an issue "
            "folder. Use when the user says «смонтируй <путь>», «смонтируй как {w}» or «{n}». Never "
            "publishes, voices or generates.").format(w=word, n=profile["skill_name"])
    return text.replace('"', "'")


def _lines(items, empty: str) -> str:
    return "\n".join(items) if items else empty


def _method(profile: dict) -> str:
    """The parts of «how» only some formats have, one file per part in `templates/format-skill/method/`."""
    return "".join((FORMAT_TEMPLATE / "method" / name).read_text(encoding="utf-8")
                   for name, wanted in METHOD_IF.items() if wanted(profile))


def render(profile: dict, need: dict, steps: dict, tools: dict, version: str) -> str:
    step_lines = ["{}. `{}` — {}".format(i, s, steps["steps"][s]["what"])
                  for i, s in enumerate(profile["steps"], 1)]
    tool_lines = ["- {} — {} ({}, пин {})".format(t, tools[t]["skills_section"], tools[t]["license"], tools[t]["pin"])
                  for t in need["tools"]]
    taste = ["- {} · {}: {}".format(t["date"], t.get("video") or "—", t["note"]) for t in profile.get("taste", [])]
    values = {
        "name": profile["skill_name"], "description": _description(profile), "version": version,
        "format": profile["format"], "language": profile.get("language", "ru"),
        "steps": _lines(step_lines, "(no steps)"), "method": _method(profile),
        "approval": APPROVAL.get(profile.get("approval", "plan"), APPROVAL["plan"]),
        "taste": _lines(taste, "(none yet)"), "tools": _lines(tool_lines, "- nothing beyond Python"),
        "asr": ASR.get(profile["asr"]["provider"], profile["asr"]["provider"])
        + ("; and what «Graphics» names" if "graphics" in profile["steps"] else ""),
        "writes": ", besides the working folder «Graphics» names" if "graphics" in profile["steps"] else "",
    }
    text = (FORMAT_TEMPLATE / "SKILL.md.tmpl").read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text
