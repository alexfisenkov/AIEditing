"""The approval point of a pipeline, answered by a person through the agent.

`pipelines.run(..., approve)` calls `approve(kind, payload)`. A question without an answer is written to
`вопросы.json` and the run stops (NeedsApproval, exit code 3); the agent asks the person, writes
`ответы.json` as {"<key>": true | false | {"ok": bool, "payload": {...}}} and runs again.

A person who asked for no questions gets `AutoApprover`: what only confirms a proposal is accepted, and what
needs a judgement still stops the run, but for the agent to decide. Every decision goes into the report.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

QUESTIONS = "вопросы.json"
ANSWERS = "ответы.json"
CONFIRMS = {"srt", "layout", "motion", "vertical"}  # the proposal stands as it is


class NeedsApproval(Exception):
    """The person has to decide before the edit goes on; see вопросы.json."""


class FileApprover:
    auto = False
    wants = "Нужно решение человека"

    def __init__(self, folder: Path, answers: Optional[Path] = None):
        self.folder = Path(folder)
        path = Path(answers) if answers else self.folder / ANSWERS
        self.answers = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def __call__(self, kind: str, payload: dict) -> bool:
        key = str((payload or {}).get("key") or kind)
        if key in self.answers:
            answer = self.answers[key]
            if isinstance(answer, dict):
                if isinstance(payload, dict) and isinstance(answer.get("payload"), dict):
                    payload.update(answer["payload"])
                return bool(answer.get("ok", True))
            return bool(answer)
        self.folder.mkdir(parents=True, exist_ok=True)
        question = {"key": key, "kind": kind, "payload": payload}
        (self.folder / QUESTIONS).write_text(
            json.dumps(question, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        raise NeedsApproval("{}: {} — {}".format(self.wants, kind, self.folder / QUESTIONS))


class AutoApprover(FileApprover):
    """No questions to the person. A secret with a place on the frame is closed, because an open one cannot be taken
    back; one without a place (said aloud) and a layout nothing could tell are for the agent to look at."""
    auto = True
    wants = "Режим без вопросов, решите сами и запишите ответ"

    def __call__(self, kind: str, payload: dict) -> bool:
        key = str((payload or {}).get("key") or kind)
        if key == "secrets":  # first, so an answer that only adds areas in `extra` closes what was found too
            for candidate in payload.get("candidates", []):
                candidate["blur"] = bool(candidate.get("rect"))
        if key not in self.answers:
            if key == "secrets" and all(c.get("rect") for c in payload.get("candidates", [])):
                return True
            if key in CONFIRMS and not (key == "layout" and not payload.get("kind")):
                return True
        return super().__call__(kind, payload)


def approver_for(profile: dict, folder: Path, answers: Optional[Path] = None, no_questions: bool = False):
    auto = no_questions or (profile or {}).get("approval") == "auto"
    return (AutoApprover if auto else FileApprover)(folder, answers)
