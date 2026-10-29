"""The approval point of a pipeline, answered by a person through the agent.

`pipelines.run(..., approve)` calls `approve(kind, payload)`. A question without an answer is written to
`вопросы.json` and the run stops (NeedsApproval, exit code 3); the agent asks the person, writes
`ответы.json` as {"<key>": true | false | {"ok": bool, "payload": {...}}} and runs again.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

QUESTIONS = "вопросы.json"
ANSWERS = "ответы.json"


class NeedsApproval(Exception):
    """The person has to decide before the edit goes on; see вопросы.json."""


class FileApprover:
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
        raise NeedsApproval("Нужно решение человека: {} — {}".format(kind, self.folder / QUESTIONS))
