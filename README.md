# AIEditing

**English** · [Русский](README.ru.md)

A workshop that builds **your own video-editing skills** for AI agents. You go through an interview
once — which formats you shoot (stream, lesson, vertical or your own), how each should be cut, what the
captions and chapter plates look like — watch a trial edit on **your** footage, say what you don't like
until it is right, and get a format skill named after your word, such as `монтаж-урок` ("lesson
edit"). After that you just say "edit this like a lesson".

> Status: early version. The speech-recognition and editing core is in place; the interview workshop
> and the format-skill builder are being built.

## Installation

```bash
npx skills add alexfisenkov/AIEditing -g
```

Needs Node.js (for `npx`), Python 3.9+ and ffmpeg in `PATH`.

| System | State |
|---|---|
| macOS | supported, checked in CI |
| Windows | supported, checked in CI |
| Linux | not tested |

## Updating and removing

```bash
npx skills update aiediting -g
npx skills remove aiediting -g
```

Format skills built by AIEditing are separate folders: updating or removing AIEditing does not touch them.

## Speech recognition — your choice

| Provider | Cost | Privacy | Word boundaries |
|---|---|---|---|
| Local whisper (whisper.cpp) | free | the recording stays on your computer | good; short words and "uh" are sometimes lost |
| ElevenLabs Scribe | paid | the recording goes to ElevenLabs | the most precise |
| Any OpenAI-compatible service (OpenAI, OpenRouter, your own server) | depends | goes to the address you set | depends on the model |
| Your own command | yours | yours | yours |

## Keys

Keys live only in your environment or in a `.env` file (see `.env.example`); AIEditing reads them
by variable name and never prints them. Never paste a key into the chat.

## What's in the repository

```
skills/aiediting/        the skill itself (what gets installed)
├── SKILL.md
├── runtime/             editing mechanics copied into every format skill
│   ├── asr/             speech recognition: four providers, one word format
│   └── media/           ffmpeg: passport, speech spans, cuts, drift, loudness, .srt
├── schema/              format profile schema
└── phases/ prompts/ tools/ templates/ design/ catalog/
tests/                   python -m unittest discover -s tests -v
.github/workflows/       CI on macOS and Windows, monthly install check
```

## Development

```bash
python -m unittest discover -s tests -v
```

Tests make their own synthetic media with ffmpeg and never use the network.

## License

MIT — see [LICENSE](LICENSE).
