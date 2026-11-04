# Refine an existing format skill

Read instead of `formats.md` and `sources.md` when the person chose «доработать». The same workshop,
starting from the installed skill instead of a preset. A skill with `approval: auto`, or a person asking for
no questions now → `phases/no-questions.md`, unless they ask to be asked.

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
(`ae.py profile set`) and a taste line (`ae.py profile taste`). A wish the runtime does not do yet (a step
marked `not_built` in `catalog/steps.json`) is answered «пока нет» and written as a taste line, not as a step.

Design changes → `phases/design.md` for the elements they named. Need a source to show on → ask for one
(`phases/sources.md`, `ae.py frames`).

## 3. Where a remark goes

A remark teaches the skills only if it lands in the right place. Decide for each one:

| The remark is about | It goes to | And then |
|---|---|---|
| a technical or tool defect: a bug, a wrong measure, a step that breaks | the workshop itself, the same day | fix it in every skill that has the code and in this workshop, its installed copy included, without asking; a kit copied by the workshop renews at build, a kit a format made its own takes the same fix by hand |
| something true of every video with graphics | `overlay-kit/README.md`, «Rules of the frame» | every format renews at its next build |
| cutting, takes, markers | `overlay-kit/takes-and-markers.md` | formats that do not cut do not read it |
| the taste of this one format | its `profile.json`, `ae.py profile taste`, in the person's own words | |
| only this one video | its report | nowhere else |

A rule that names the person's own paths, accounts or materials goes to `design/sources.md` of their format, never to this workshop.

## 4. Trial, build, install

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
