# What's new in AIEditing

## Unreleased

- A format skill says to use `python3` where there is no `python`, as the workshop already does.

## 0.1.0 — 2026-11-04

The first public version.

- «Без вопросов»: one message and a recording give the finished video and the installed skill; `phases/no-questions.md`, `ae.py init --no-questions`, `approval: auto`, `run.py edit --no-questions`. Confirmations are accepted, judgements are the agent's, a found secret is closed, every decision goes into the report.
- The `graphics` step: scenes written by the model on top of the finished video, with or without cuts; `overlay-kit/`, the `overlay` preset and a format «Наложения», `ae.py formats --preset`.
- A format skill's `SKILL.md` carries only the method it needs: `templates/format-skill/method/`.
- Overlay kit: the camera follows the face without steps (median, Gaussian, spline instead of the nearest point of the track); `time-map.json` lets a finished video take cuts by markers while scenes keep their seconds; the README holds the lessons of a 73-marker review.
- A format «YouTube с графикой»: clean speech from takes (`tools/takes.py`, a word's edge follows the sound), graphics on top, edits by markers (`tools/markers.py`, `tools/recut.py`, `takes-and-markers.md`). `phases/refine.md` says where a remark goes.
- Foundation: repository layout, one test command, CI on macOS and Windows, a monthly install check.
- Speech recognition with four providers and one word format: local whisper.cpp, ElevenLabs Scribe, any OpenAI-compatible endpoint (OpenRouter included), or your own command. Keys are read by variable name: from the environment, a `.env` file or `asr.key_file`.
- Editing mechanics on ffmpeg: file passport, speech detection, pause removal with a margin around speech in one pass, A/V drift check, loudness normalisation, `.srt` with a brand glossary.
- Format profile schema and a dependency-free profile check.
