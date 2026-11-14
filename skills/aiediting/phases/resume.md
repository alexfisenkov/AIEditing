# Resume

Read instead of `start.md` when `.aiediting-work/state.js` exists and has no `finishedAt`. The files
are the memory: do not redo finished stages, do not ask answered questions again. `noQuestions` in
`state.js` → read `phases/no-questions.md` and `.aiediting-work/<skill>/решения.md` instead of steps 1, 4, 5 and 6, go
on from where `решения.md` stops; step 3 is the only line the person gets before the end.

1. **Read** `state.js` (`mode`, the stages, `waiting`, `formats`, `sources`, `trials`, the last lines of
   `log`), then the draft `profile.json` of the format in work — the one in the active stage's work, or
   the last in `formats` without an installed skill — then the file of the active stage's phase.
2. **Raise the dashboard**: a bare `python "<skillDir>/tools/ae.py"` brings the server back on its old
   port; re-point the pane (`phases/start.md`, §2) and say the address. A line `Новая версия: …` in what it printed → say it
   in one phrase, as `phases/start.md`, §2 says. What the person told at the start is in `ae.py intro`: not asked again.
3. **Tell the person in one line where things stand**: «Продолжаю: урок — интервью, тема «субтитры»;
   вертикаль ещё впереди».
4. **A `waiting` left in `state.js`** is the question the last session asked. Still open → ask it again;
   answered in the dialogue → `ae.py answered`.
5. **A trial with `вопросы.json` and no `ответы.json`** — the decision the pipeline was waiting for: ask it.
6. Continue from the active stage.

A person who wants to start over → `ae.py init --fresh …`; the drafts in `.aiediting-work/` stay unless
they ask to delete them.
