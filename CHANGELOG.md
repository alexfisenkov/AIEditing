# What's new in AIEditing

## Unreleased

- «Без вопросов»: one message and a recording give the finished video and the installed skill; `phases/no-questions.md`, `ae.py init --no-questions`, `approval: auto`, `run.py edit --no-questions`. Confirmations are accepted, judgements are the agent's, a found secret is closed, every decision goes into the report.
- The `graphics` step: scenes written by the model on top of the finished video, with or without cuts; `overlay-kit/`, the `overlay` preset and a format «Наложения», `ae.py formats --preset`.
- A format skill's `SKILL.md` carries only the method it needs: `templates/format-skill/method/`.

## 0.1.0 — 2026-10-29

- Foundation: repository layout, one test command, CI on macOS and Windows, a monthly install check.
- Speech recognition with four providers and one word format: local whisper.cpp, ElevenLabs Scribe, any OpenAI-compatible endpoint (OpenRouter included), or your own command. Keys are read from the environment by name only.
- Editing mechanics on ffmpeg: file passport, speech detection, pause removal with a margin around speech in one pass, A/V drift check, loudness normalisation, `.srt` with a brand glossary.
- Format profile schema and a dependency-free profile check.
