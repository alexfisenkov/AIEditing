# Refine an existing format skill

Read instead of `formats.md` and `sources.md` when the person chose «доработать». The same workshop,
starting from the installed skill instead of a preset. A skill with `approval: auto`, or a person asking for
no questions now → `phases/no-questions.md`, unless they ask to be asked.

**Any `монтаж-*` can be changed here, by anyone's hand:** built by this workshop or not, written by the person or someone else.
What no profile describes is never thrown away; it stays with the skill and is changed together with the person.

## 1. Open it

```bash
python "<skillDir>/tools/ae.py" profile open <skill>
```

The installed profile and design come into `.aiediting-work/<skill>/`. Say in two or three lines what the
skill does now: its steps, its approval way, the last taste notes. Ask whether there is a recent issue
folder of this skill — its `отчёт.md` may hold «Замечания для доработки» the skill collected; read them
first, they are the person's own words.

What the command prints beyond that is what no profile describes:

- **Its own files** go to `own/` of the draft, and the build puts them back as they were.
- **Its own kit,** a `design/overlay-kit` without the workshop's mark, stays in `design/` and is not renewed at build. Change it
  with the person; a defect of the workshop's kit reaches it by hand (the table below).
- **A kit changed after its build.** A copied kit carries a mark with the hash of each of its files, and it renews at each build only
  while they match. When they do not, the command names the files, and the build stops rather than wiping them. Ask the person: keep
  those changes, and the kit is the format's own from now on (`ae.py kit <skill> own`, the mark goes); or drop them for the
  workshop's current kit (`ae.py kit <skill> renew`). A kit copied before these hashes has nothing to compare with: it is renewed
  and the build says so; the old one stays in the draft and in the reserve of the installed version.
- **Its own method** is `design/method.md`, which goes into the built `SKILL.md` as it is. A `SKILL.md` edited after its build is
  rewritten by the build, so the command puts the edited one beside the draft: read it, carry what is theirs into `design/method.md`
  with the person, and only then build.

**A skill with no profile,** written by hand or by someone else, is not rebuilt at all. The command gives a working copy of the
whole folder: read its `SKILL.md`, its method and its kit, and change those files with the person, by section 2 below. A wish that
one of the workshop's steps would do: copy the idea or say what it would take, not a silent rewrite. Try it on one of their
sources, by what its own `SKILL.md` says. On «да» `ae.py install-skill <the copy>` puts it back where it lives, the replaced
version in the reserve. To move it to a profile instead, that is a new format, and its own parts go along as above; ask first.

## 2. The refinement interview

`ae.py stage interview`, then one message:

```
Что не нравится в том, как монтирует <skill>?
— покажите, как надо и как не надо: время в ролике, кадр, отрезок или пример;
— что добавить, что убрать — и в каких местах.
```

Each answer becomes a question round of `phases/interview.md` where it opens a theme, a parameter
(`ae.py profile set`) and a taste line (`ae.py profile taste`). A wish the runtime does not do yet,
including a missing catalog row or a legacy `not_built` marker, calls for investigation: inspect the source, choose a viable
local tool, install checked requirements in an isolated environment and validate actual output. Add a
repeatable capability to the catalog, runtime and tests. Only a concrete failed route is a blocker.

Design changes → `phases/design.md` for the elements they named. Need a source to show on → ask for one
(`phases/sources.md`, `ae.py frames`).

## 3. Where a remark goes

A remark teaches the skills only if it lands in the right place. Decide for each one:

| The remark is about | It goes to | And then |
|---|---|---|
| a technical or tool defect: a bug, a wrong measure, a step that breaks | the workshop itself, the same day | fix it in every skill that has the code and in this workshop, its installed copy included, without asking; a kit copied by the workshop renews at build, a kit a format made its own takes the same fix by hand |
| two steps that do not fit: a parameter applied twice, a method that says what the pipeline already does | `catalog/params.json` and the owner in code, `tools/aelib/coherence.py` when a profile can name the pair, and, with the repository at hand, a test of the whole path in `tests/test_recording_ways.py` | «One parameter, one place» below; a rule in a method file alone does not hold |
| something true of every video with graphics | `overlay-kit/README.md`, «Rules of the frame» | every format renews at its next build |
| something true of every re-edit under 9:16 | `overlay-kit/vertical.md` | every format with `reedit` renews at its next build |
| clean speech, takes, trimming, markers | `overlay-kit/takes-and-markers.md` | only formats with `params.clean_speech` read it |
| a way to edit the catalog does not have | `catalog/formats.json` and a preset, «A new way» below | the next person is offered it |
| the taste of this one format | its `profile.json`, `ae.py profile taste`, in the person's own words | |
| only this one video | its report | nowhere else |

A rule that names the person's own paths, accounts or materials goes to `design/sources.md` of their format, never to this workshop.

## One parameter, one place

A format is steps from the pipeline, methods the model follows and a kit it runs, written at different times. They agree only when
someone checks. So before a new step, method or kit tool: read `catalog/params.json`, and walk the path of one video from the recording
to the finished file, asking of each number who applies it and in whose seconds it is. A method never says to apply what the pipeline
applies. Whoever cannot name the owner has found the defect. The first such defect was `params.speed`: a method set it on the clean
speech, the pipeline applied it again, and the video ran at 1.145 instead of 1.07 with every check green, because each part was right
by itself. Only a test of the whole path shows it.

## A new way

This workshop is the base of how a video can be edited, so a way found while working with one person belongs to the next one too.
When it works and the catalog does not have it: a row in `catalog/formats.json`, under `variants` of the format it belongs to, or a
new format; a preset in `templates/profiles/`; a method in `templates/format-skill/method/` when the model does part of it, with its
line in `tools/aelib/skillmd.py`. A row and a preset are enough for a path: no code. The catalog holds the way, never this person's
paths, materials or design. A new step is more work: its row in `catalog/steps.json`, its function in `runtime/pipelines/`. A way that
takes a decision from the person gets its question in `phases/interview.md`, in the order the answers depend on each other, and a
refusal in `tools/aelib/coherence.py` while it stays open.

**Where it lives.** In the source of this workshop: `skills/aiediting/` of the repository it is installed from, or the person's fork.
Not in `~/.agents/skills/aiediting`: `npx skills update aiediting -g` overwrites that copy, so a way written only there is gone at the next
update. Try it in the installed copy if that is quicker, but it is not done until it is in the source. **How it reaches the next
person:** through that repository and their own update, and through nothing else; sending it upstream, as a pull request or to anyone,
is the person's own step on their «да». A person with no repository to write to: say so, and keep the way in their format skill
(its profile, `own/`, `design/method.md`): a format skill is a separate folder that no update touches, so it stays theirs, but nobody
else gets it.

## 4. Trial, build, install

`phases/trial.md` on one of their sources until «да», then `phases/build.md`. Installing over the
existing skill moves the current version to the reserve automatically. A format with paths that an earlier
version built has none recorded: `ae.py variant <skill> <the path it already is> --keep` records it and changes nothing else.

## Undo

The person wants the previous version back — now or in any later session:

```bash
python "<skillDir>/tools/ae.py" restore-skill <skill> --list     # the reserve, newest first
python "<skillDir>/tools/ae.py" restore-skill <skill>            # the newest; --backup <id> for another
```

The version it replaces goes to the reserve too, so nothing is lost. `backup-skill <skill>` makes a reserve
copy without changing anything. Say which version is now installed and that a new session sees it.
