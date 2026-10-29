# What's new in AIEditing

## 0.1.0 — 2026-10-29

- Foundation: repository layout, one test command, CI on macOS and Windows, a monthly install check.
- Speech recognition with four providers and one word format: local whisper.cpp, ElevenLabs Scribe, any OpenAI-compatible endpoint (OpenRouter included), or your own command. Keys are read from the environment by name only.
- Editing mechanics on ffmpeg: file passport, speech detection, pause removal with a margin around speech in one pass, A/V drift check, loudness normalisation, `.srt` with a brand glossary.
- Format profile schema and a dependency-free profile check.
