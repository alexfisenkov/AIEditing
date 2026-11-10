# Build and install

`ae.py stage build`. The draft the person said «да» to becomes `монтаж-<слово>`.

## 1. Build

```bash
python "<skillDir>/tools/ae.py" build-skill .aiediting-work/<skill>/profile.json .aiediting-work/build --replace
```

It checks the profile against the schema and the step list, copies this version's `runtime/` (only the
packages the chosen steps need), the schema, `design/`, writes `pins.json` (only the chosen tools, by
their pins) and `SKILL.md` from `templates/format-skill/`, and checks that the copy imports by itself.
A refusal names the problem → fix the draft, build again. A format with paths and none chosen is refused: go back to
`phases/trial.md`, «A format with paths», rather than setting `variant` to get past it.

## 2. Tools — verify and repair

`python3 "<skillDir>/tools/ae.py" setup --check` checks the installed toolkit. For this format, run
`setup --steps <steps of the profile, comma-separated> --asr <provider>`; with `params.clean_speech`,
also repair local `whispercpp`, because choosing takes hears by it. The requested format authorizes
its local dependencies: announce total heavy downloads once and proceed without per-tool approval.
Check the resulting tools and a trial render. Remotion's licence and render-browser size still need to
be stated; its kit prepares the working folder from the lockfile. If setup cannot satisfy a dependency,
name the concrete failure and investigate the source and requirements before dropping the capability.
Do not silently leave a step whose dependency is absent.

## 3. Install globally

`ae.py ask action --note "установить <skill>"`, and on «да»:

```bash
python "<skillDir>/tools/ae.py" install-skill .aiediting-work/build/<skill>
```

It writes `~/.agents/skills/<skill>/` and a pointer in `~/.claude/skills/` (a copy on Windows without
symlink rights); a previous version goes to `~/.agents/skills/.aiediting-backups/` first. Then tell the
person, in one message:

- the skill is installed and is seen **in a new session**, in any folder;
- how to use it: «смонтируй как <слово> <путь>»; a bare «смонтируй <путь>» works while this is their only format, with
  several the agent asks which first; results go to `<output_dir>/<дата-тема>/`;
- it only edits — publishing, voice-over and generation are theirs;
- a remark after a video → the skill writes it into the report; to change the format for good —
  «запусти AIEditing — доработка <skill>».

## 4. Next format or finish

More formats in this session → back to `phases/sources.md` for the next one. All done →

```bash
python "<skillDir>/tools/ae.py" finish --result "<what is installed now, one line>"
```
