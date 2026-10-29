# Start

Read when `/aiediting` is called and `.aiediting-work/state.js` in the current folder is absent or
finished. An unfinished one → `phases/resume.md` instead.

## 1. Find the skill and the tool

```bash
AE=$(find -L ~/.agents/skills ~/.claude/skills ~/.codex/skills ~/.cursor/skills ~/.gemini/skills \
        .agents/skills .claude/skills -maxdepth 4 -path '*/aiediting/tools/ae.py' 2>/dev/null | head -1)
echo "$AE"
```

`<skillDir>` is the folder two levels above `ae.py`. Keep the full path in mind for the whole session;
on Windows (Git Bash) pass it through `cygpath -m`. No Python 3.9+ → say so in one line: the workshop
cannot run without it; name how to install Python for their system and stop.

## 2. Open the workshop

```bash
python "<skillDir>/tools/ae.py" init --mode new --title "<what the person asked, in their words>"
```

It creates `.aiediting-work/` in the current folder, copies the dashboard, raises a server on
127.0.0.1 and prints the address. Open it **once, yourself**, before the first question:

- Claude Code: `preview_start({url: "http://localhost:PORT"})`, then navigate to `/dashboard.html`.
- No pane: `open` / `start` / `xdg-open` on `.aiediting-work/dashboard.html`.
- Say the address in the chat too. Over SSH or in CI no server is raised — give the file path.
- «Дашборд пропал» → a bare `python "<skillDir>/tools/ae.py"` raises it again on the same port.

## 3. The first question: create or refine

`python "<skillDir>/tools/ae.py" list-skills` lists format skills AIEditing has built on this computer.
Then `ae.py ask choice --note "новый скилл или доработка"` and one message:

```
Что делаем?
1. Новый скилл монтажа — под формат, который выберете.
2. Доработать существующий: монтаж-урок, монтаж-эфир.   ← only the names list-skills printed
```

No skills yet → say so and go straight to a new one. The call already named it («/aiediting refine
монтаж-урок», «доработай урок») → do not ask again.

- **New** → `ae.py stage formats`, read `phases/formats.md`.
- **Refine** → `ae.py init --mode refine --fresh --title "Доработка <name>"`, read `phases/refine.md`.

## 4. The environment, once

`ae.py doctor --steps speech_spans,cut_spans` — ffmpeg is the one thing every format needs. Missing →
tell the person in one line what it is and how it is installed; install only on their «да»
(`doctor --install ffmpeg --yes`). Everything else is installed later, for the steps the interview
chooses (`phases/build.md`).
