# Build and install

`ae.py stage build`. The draft the person said «да» to becomes `монтаж-<слово>`.

## 1. Build

```bash
python "<skillDir>/tools/ae.py" build-skill .aiediting-work/<skill>/profile.json .aiediting-work/build --replace
```

It checks the profile against the schema and the step list, copies this version's `runtime/` (only the
packages the chosen steps need), the schema, `design/`, writes `pins.json` (only the chosen tools, by
their pins) and `SKILL.md` from `templates/format-skill/`, and checks that the copy imports by itself.
A refusal names the problem → fix the draft, build again.

## 2. Tools — only the chosen ones, only on «да»

`python "<skillDir>/tools/ae.py" doctor --steps <steps of the profile, comma-separated> --asr <provider>`
shows what this format needs and what is missing. For each missing tool: one line of what it is, its
licence, its size when heavy, the warning when it has one — and `ae.py ask action --note "поставить <id>"`.
Only on «да»: `doctor --install <id> --yes`. «Ручная» installs (a model file, Windows releases) → give the
link and wait. A refused tool → the step that needs it goes out of the profile, and the skill is built
again; never leave a step whose tool is not there.

## 3. Install globally

`ae.py ask action --note "установить <skill>"`, and on «да»:

```bash
python "<skillDir>/tools/ae.py" install-skill .aiediting-work/build/<skill>
```

It writes `~/.agents/skills/<skill>/` and a pointer in `~/.claude/skills/` (a copy on Windows without
symlink rights); a previous version goes to `~/.agents/skills/.aiediting-backups/` first. Then tell the
person, in one message:

- the skill is installed and is seen **in a new session**, in any folder;
- how to use it: «смонтируй <путь>» or «смонтируй как <слово>»; results go to `<output_dir>/<дата-тема>/`;
- it only edits — publishing, voice-over and generation are theirs;
- a remark after a video → the skill writes it into the report; to change the format for good —
  «запусти AIEditing — доработка <skill>».

## 4. Next format or finish

More formats in this session → back to `phases/sources.md` for the next one. All done →

```bash
python "<skillDir>/tools/ae.py" finish --result "<what is installed now, one line>"
```
