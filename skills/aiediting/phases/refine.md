# Refine an existing format skill

Read instead of `formats.md` and `sources.md` when the person chose «доработать». The same workshop,
starting from the installed skill instead of a preset.

## 1. Open it

```bash
python "<skillDir>/tools/ae.py" profile open <skill>
```

The installed profile and design come into `.aiediting-work/<skill>/`. Say in two or three lines what the
skill does now: its steps, its approval way, the last taste notes. Ask whether there is a recent issue
folder of this skill — its `отчёт.md` may hold «Замечания для доработки» the skill collected; read them
first, they are the person's own words.

## 2. The refinement interview

`ae.py stage interview`, then one message:

```
Что не нравится в том, как монтирует <skill>?
— покажите, как надо и как не надо: время в ролике, кадр, отрезок или пример;
— что добавить, что убрать — и в каких местах.
```

Each answer becomes a question round of `phases/interview.md` where it opens a theme, a parameter
(`ae.py profile set`) and a taste line (`ae.py profile taste`). Here — and only here — heavy layers
(graphics on HyperFrames, effects «за головой») may come in, when the person asks for them: they go into
`steps`, and `phases/build.md` installs them on «да».

Design changes → `phases/design.md` for the elements they named. Need a source to show on → ask for one
(`phases/sources.md`, `ae.py frames`).

## 3. Trial, build, install

`phases/trial.md` on one of their sources until «да», then `phases/build.md`. Installing over the
existing skill moves the current version to the reserve automatically.

## Undo

The person wants the previous version back — now or in any later session:

```bash
python "<skillDir>/tools/ae.py" restore-skill <skill> --list     # the reserve, newest first
python "<skillDir>/tools/ae.py" restore-skill <skill>            # the newest; --backup <id> for another
```

The version it replaces goes to the reserve too, so nothing is lost. `backup-skill <skill>` makes a reserve
copy without changing anything. Say which version is now installed and that a new session sees it.
