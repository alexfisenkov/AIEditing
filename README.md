# AIEditing

**English** · [Русский](README.ru.md)

A workshop that builds **your own video-editing skills** for AI agents. You go through an interview
once — which formats you shoot (stream, lesson, vertical or your own), how each should be cut, what the
captions and chapter plates look like — watch a trial edit on **your** footage, say what you don't like
until it is right, and get a format skill named after your word, such as `монтаж-урок` ("lesson
edit"). After that, in any folder, you just say "edit this like a lesson".

> Status: early version (0.1).

## Installation

**Without a terminal** — paste this to your agent (Claude Code, Codex, Cursor…):

> Install the AIEditing skill globally: `npx skills add alexfisenkov/AIEditing -g`. Then tell me how to start it.

**From a terminal:**

```bash
npx skills add alexfisenkov/AIEditing -g
```

Skills are installed **globally** (`-g`), so the workshop and every format skill it builds work in any
folder. Needs Node.js (for `npx`), Python 3.9+ and ffmpeg in `PATH`; everything else is installed later,
only if your formats need it, and only after you say yes.

| System | State |
|---|---|
| macOS | supported, checked in CI |
| Windows | supported, checked in CI |
| Linux | not tested |

## How to use it

1. Type `/aiediting`. A dashboard opens beside the chat (or in your browser): stages, your answers,
   frames of your footage, design variants side by side, trial clips.
2. Choose: **a new format skill** or **refine** one you already have.
3. New: pick formats from the list and add your own through commas («урок, вертикаль, подкаст»). Give
   1–3 source videos. Answer the questions in rounds of 3–4 — each with a recommended option and an
   example on your video. Pick the design: your own style or the Chrome & Graphite example.
4. Watch the trial edit. «Нет» → say what is wrong, show how it should and should not be, what to add or
   remove and where — the workshop reworks it until you say «да».
5. The skill `монтаж-<your word>` is built and installed globally. In a new session, anywhere:
   «смонтируй ~/Videos/lesson.mp4» or «смонтируй как урок».

A format skill puts the result into `<your issues folder>/<date-topic>/`: the video, a `.srt` when the
format makes one, and a short report. A remark after watching goes into that report, and the skill
suggests running AIEditing to refine the format.

## What it does and what it never does

| Does | Never does |
|---|---|
| interviews you and builds a format skill from your answers | publishes, uploads or sends anything |
| edits **one trial piece** of your source to show you | voices, generates video, music or images |
| installs only the tools your formats need, by pinned versions, after your yes | asks for a key or prints one |
| keeps the previous version of a skill and restores it in one command | puts into a skill anything you did not choose |

## Speech recognition — what is best where

| Provider | Cost | Privacy | Word boundaries | Best for |
|---|---|---|---|---|
| Local whisper (whisper.cpp) | free | the recording stays on your computer | good; short words and "uh" are sometimes lost | private recordings, no budget |
| ElevenLabs Scribe | paid | the recording goes to ElevenLabs | the most precise | lessons where every pause and "uh" is cut |
| Any OpenAI-compatible service (OpenAI, OpenRouter, your own server) | depends | goes to the address you set | depends on the model | when you already pay for one |
| Your own command | yours | yours | yours | anything else |

Changing the provider is one answer in the interview or a refinement.

## Tools and licences

Only tools with open licences are in the catalog (`skills/aiediting/catalog/tools.json`), each pinned and
installed by AIEditing's own scripts, only when chosen.

| Tool | What for | Licence | Weight |
|---|---|---|---|
| ffmpeg | cutting, joining, loudness, blur, export | LGPL-2.1+ (GPL-2.0+ for GPL builds) | light |
| whisper.cpp + model | local speech recognition | MIT | the model is ≈3 GB (large-v3) |
| Pillow, numpy, OpenCV | plates and captions as images, face and layout | MIT-CMU, BSD-3-Clause, Apache-2.0 | light |
| Tesseract | text on frames when looking for secrets (Apple Vision on macOS) | Apache-2.0 | light |
| Node.js + HyperFrames | graphics over the video | MIT, Apache-2.0 | hundreds of MB with Chrome |
| Remotion + RobustVideoMatting | effects "behind the head" in a vertical | Remotion License, GPL-3.0 | heavy |

> **Remotion is not open source.** It is free for individuals and companies of up to three people;
> larger companies need a paid licence. Check the terms at remotion.pro before choosing effects that need it.
> Nothing is installed by default; it comes in only if you choose those effects.

[OpenMontage](https://github.com/calesthio/OpenMontage) (AGPL-3.0) is a full production pipeline from
script to generation; AIEditing does not include it — only this link.

## Keys

Keys live only in your environment or in a `.env` file (see `.env.example`); AIEditing reads them
by variable name and never prints them. Never paste a key into the chat.

## Updating and removing

```bash
npx skills update aiediting -g      # or just tell your agent: «обнови AIEditing»
npx skills remove aiediting -g
```

Start a new session after updating. Format skills built by AIEditing are separate folders with their
own copy of the editing runtime: updating or removing AIEditing does not touch them. A refinement
rebuilds a skill on the current version and keeps the previous one in
`~/.agents/skills/.aiediting-backups/`; the workshop brings it back on request.

## What's in the repository

```
skills/aiediting/        the skill itself (what gets installed)
├── SKILL.md             the workshop's order and rules
├── phases/  prompts/    one file per stage, read when the stage starts
├── tools/ae.py          one command per event: dashboard, profiles, build, install, doctor
├── tools/state/         the dashboard page, state and local server
├── templates/           the format-skill template and starting profiles
├── catalog/             formats, steps, tools with licences and pins
├── runtime/             editing mechanics copied into every format skill
├── schema/  design/     profile schema, example design system
tests/                   python -m unittest discover -s tests -v
.github/workflows/       CI on macOS and Windows, monthly install check
```

## Development

```bash
python -m unittest discover -s tests -v
```

Tests make their own synthetic media with ffmpeg, install skills only into a temporary home folder and
never use the network.

## License

MIT — see [LICENSE](LICENSE). The dashboard and its server are adapted from AISpa (MIT, built on
Autopilot 2.2.0); their notices are kept in `skills/aiediting/tools/state/NOTICE.md`.
