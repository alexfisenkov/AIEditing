# Start

Read when `/aiediting` is called and `.aiediting-work/state.js` in the current folder is absent or
finished. An unfinished one → `phases/resume.md` instead. The person asked for no questions → §1 here,
then `phases/no-questions.md`. Said in the middle of a workshop → `phases/no-questions.md`, §1.

## 1. Find the skill and the tool

```bash
AE=$(find -L ~/.agents/skills ~/.claude/skills ~/.codex/skills ~/.cursor/skills ~/.gemini/skills \
        .agents/skills .claude/skills -maxdepth 4 -path '*/aiediting/tools/ae.py' 2>/dev/null | head -1)
echo "$AE"
```

`<skillDir>` is the folder two levels above `ae.py`. Keep the full path in mind for the whole session;
on Windows (Git Bash) pass it through `cygpath -m`. If Python 3.9+ is missing, install a supported
version through the system's normal package manager, then retry. If installation fails, name the
actual platform or permission error.

## 2. Open the workshop

```bash
python "<skillDir>/tools/ae.py" init --mode new --title "<what the person asked, in their words>"
```

It creates `.aiediting-work/` in the current folder, copies the dashboard, raises a server on
127.0.0.1 and prints the address. Renders are large and a synced folder (iCloud, Dropbox) slows them down
and copies them everywhere; there, set `AIEDITING_WORK=<folder outside it>` on this and every later `ae.py`
call, because a shell may go back to its first folder between calls. Check where it printed. Open it **once,
yourself**, before the first question:

- Claude Code: `preview_start({url: "http://localhost:PORT"})`, then navigate to `/dashboard.html`.
- No pane: `open` / `start` / `xdg-open` on `.aiediting-work/dashboard.html`.
- Say the address in the chat too. Over SSH or in CI no server is raised — give the file path.
- «Дашборд пропал» → a bare `python "<skillDir>/tools/ae.py"` raises it again on the same port.

## 3. The first question: create or refine

`python "<skillDir>/tools/ae.py" list-skills` lists the `монтаж-*` skills on this computer: the ones AIEditing has built, and
the ones written by hand or by someone else, marked so. Any of them can be refined.
Then `ae.py ask choice --note "новый скилл или доработка"` and one message:

```
Что делаем?
1. Новый скилл монтажа — под формат, который выберете.
2. Доработать существующий: монтаж-урок, монтаж-эфир.   ← only the names list-skills printed
```

No skills yet → say so and go straight to a new one. The call already named it («/aiediting refine
монтаж-урок», «доработай урок») → do not ask again.

A call that names a format with paths («/aiediting нарезка») has named the format, not the path: the path is still offered and
probed (`phases/formats.md`, «A format with paths»). A call that comes with a finished video goes to the same format, and the
first thing to find out about it is where it came from (`phases/sources.md`, «A finished video»).

- **New** → `ae.py stage formats`, read `phases/formats.md`.
- **Refine** → `ae.py init --mode refine --fresh --title "Доработка <name>"`, read `phases/refine.md`.

## 4. Check the environment

`python3 "<skillDir>/tools/ae.py" setup --check` verifies the full supported toolkit. If the person
already asked to install AIEditing, finish installation with `setup` before the workshop; copying the
skill with `npx skills add` did not install its dependencies. For a requested capability with a missing
dependency, use `setup --steps <steps> --asr <provider>` to repair that subset and verify again.
Announce total heavy downloads once. The request to install or use the capability is enough for its
local dependencies; no separate question per tool.
