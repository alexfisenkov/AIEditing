---
name: aiediting
description: Workshop that builds your own video-editing skills. Interviews you about a format (stream, lesson, vertical or your own), looks at frames of your footage, offers the ways that format can go and shows each on your video, assembles a design system with you, edits a trial clip until you say yes, and installs a self-contained format skill that edits every next video the same way. Or, if you say «без вопросов», takes one message and a recording and returns the finished video and the installed skill. Also refines any editing skill you already have, built here or not. Starts only on /aiediting.
disable-model-invocation: true
argument-hint: "[new|refine] format name or path to a source video"
metadata:
  version: "0.4.0"
---

# AIEditing

AIEditing is a **workshop**. It exists to create a format skill — `монтаж-<the person's word>` — or to
refine one that exists. It interviews the person, looks at frames of their own footage, builds a design
system with them, edits **a trial** of their source to show (one piece, or where the format has paths a short probe of each and
then the chosen one in full), reworks it until they say «да», and then builds and installs the format skill globally. From then on the format skill does the editing; the
workshop is not needed again until something should change. A person who asks for no questions gets all
of this from one message: the finished video first, the skill installed with it.

**The workshop is the base of how a video can be edited.** Narrow skills come out of it: for a niche, a task, the person's own
design system. Where a format can go more than one way, it offers the ways, shows each on the person's video, and builds only what
they chose. It stays open: any installed `монтаж-*` can be changed here later, together with the person, even one built by hand or by
someone else, and what no profile describes stays with that skill (`phases/refine.md`). A way the catalog lacks goes into it for the
next person.

**What the workshop never does** — in every phase, whatever is asked: it never publishes, uploads or
sends anything, never voices, never generates video, music or images. Its only edits are these trials,
shown on the dashboard and kept in the workshop folder, with one exception: what the overlay kit renders needs a working folder
outside it, `~/.local/share/overlay-kit/…`, because rendering from a cloud-synced folder hangs; without questions, the built skill edits the whole
recording into its issue folder instead. The same holds for every format skill it builds:
«смонтируй как <слово> <путь>» → a folder with the video, `.srt` and a short report. Nothing else.

## Reading this skill

This file is the order and the rules that never lose. Each phase's rules are in its own file, **read
when that phase starts and not before** — one at a time; a file opened early stays in the context for
the rest of the session.

| Stage id | Read | Produces |
|---|---|---|
| `start` | `phases/start.md` | the dashboard open; the person met in one message and a personal plan; «новый» or «доработка» chosen |
| `formats` | `phases/formats.md` | one draft profile per format, listed or the person's own |
| `sources` | `phases/sources.md` | 1–3 sources, their frames and layout on the dashboard |
| `interview` | `phases/interview.md` + `prompts/question-round.md` | the profile answered, round by round; the paths of the format offered |
| `design` | `phases/design.md` | `design/` of the skill, chosen variants |
| `trial` | `phases/trial.md` | a probe of each path and their choice, where the format has paths; a trial clip the person said «да» to; every remark in the profile |
| `build` | `phases/build.md` | `монтаж-<слово>` built, its dependencies checked and repaired, installed globally |
| — | `phases/refine.md` — instead of formats and sources, when refining | |
| — | `phases/resume.md` — instead of start, when `.aiediting-work/state.js` is unfinished | |
| — | `phases/no-questions.md` — instead of all of them, when the person asked not to be asked | a finished video and the skill installed |

For a request to remove or replace a human video background, read
`references/background.md` when that capability is needed. It is a local media operation and may
also supply a foreground layer for an edit's "behind the head" composition.
For another editing request outside the catalog or a format's chosen steps, read
`references/toolbox.md` and inspect `ae.py capabilities` before selecting a local route.
For detailed tool use, read `references/methods.md` and only the task's linked method pages.
They explain tool selection, source-time ownership, tuned recipes and output acceptance. Checked
analysis/finishing examples run through `tools/recipes.py`; its commands are not native pipeline
step names. Do not change an existing format merely to apply or learn a one-off method.

**Their words choose the path.** The person asked not to be asked (the signal is at the top of that file)
→ `phases/start.md`, §1, then `phases/no-questions.md`, in place of every phase but the ones it names.
Everything below that says «asked» or «да» reads there as that phase says; the limits on publishing,
generating, paying and keys do not move.

After a compaction re-read `.aiediting-work/state.js`, the draft `profile.json` of the format in work,
and the file of the current phase. Nothing else. With `noQuestions` in `state.js` that is
`phases/no-questions.md`, its `решения.md`, and the method of the step you are in.

## The words the person sees

Instructions here are English; the person is spoken to **in their language** — Russian unless they write
in another one. One word per stage, on the dashboard and in the chat: Старт · Форматы · Исходники ·
Интервью · Дизайн · Пробный монтаж · Сборка. The thing being made is «скилл формата» or «скилл
монтажа», named `монтаж-<слово>` with the person's own word.

## The tool

Every event is one call: `python "<skillDir>/tools/ae.py" <command>` — `init`, `no-questions`, `stage`, `ask`,
`answered`, `formats`, `profile`, `variant`, `frames`, `layout`, `design-example`, `samples`, `choose`, `trial`, `show`, `hear`, `kit`,
`verdict`, `build-skill`, `install-skill`, `list-skills`, `backup-skill`, `restore-skill`, `doctor`, `setup`, `capabilities`, `background`, `image-cutout`,
`library`, `voice-try`, `finish`. The command list with arguments is at the top of `tools/ae.py`. `phases/start.md` says how to
find `<skillDir>`. You never edit `state.js` or the dashboard by hand. Where there is no `python`, as on
many Macs, use `python3`; where it is the Microsoft Store stub on Windows, use `py -3`.

## Rules that never lose

1. **A key is never asked for, echoed or written.** Which recogniser, whether an account exists — yes.
   The key itself — never: the person puts it into their environment or `.env` by the variable name.
2. **A fact about the person is never invented** — the output folder, the brand glossary, the music
   library: asked, or left as a visible gap in the profile.
3. **Installation is part of the requested capability.** After the person asks to install AIEditing, run
   `python3 <skillDir>/tools/ae.py setup` for its full supported local toolkit; `npx skills add` only copies
   the skill bundle. Announce the total heavy downloads once, then proceed. Do not ask again for each tool.
   At the start of a task, `setup --check` reports missing dependencies; `setup --steps a,b --asr whispercpp`
   repairs the subset needed for that task. A request to use a capability authorizes its local dependencies.
   Paid APIs, uploads, publication and keys keep their separate limits. Do not install arbitrary packages
   without checking their source, requirements and a real output.
4. **Examples are always on the person's own video.** No source of the needed kind → ask for one; without
   it the question is asked in words, without an example.
5. **Every remark on the format goes into the profile** (`ae.py profile taste`), and only AIEditing changes a profile. A format
   skill writes each remark into its report and, where the person has a library, into their own rules (`правила.md`, general or
   by format), which it follows from the next video; the steps and the design of the format change only here, and it suggests
   «запусти AIEditing — доработка».
6. **The previous version is kept.** Installing over a skill moves the old one to the reserve;
   `restore-skill` brings it back in one command.
7. **The format skill holds only what was chosen** — steps, tools and design; nothing «на всякий случай».
8. **A format with paths is never built without a choice.** The person chooses after seeing the probes on their own video;
   asking for no questions makes it your choice, named in the last message.
9. **A missing catalog row is not a refusal.** Inspect the requested effect and source, choose a real local
   tool, install it in an isolated environment, and validate an output on the person's media. Add a recurring
   capability to the catalog, runtime and tests. Name a concrete blocker only after trying the viable path.
   For a person in video, `ae.py background` uses local ONNX Runtime and RVM MobileNetV3 on Apple Silicon;
   inspect a preview for edge quality. It does not promise arbitrary object segmentation or flawless mattes.

10. **Everything new is by choice.** The library, inserts, the timeline, the voice, music, sound design, the publishing pack, cameras,
    gentle cleaning and the preparation are offered, never assumed: a person has the thing or not, wants it or not. What is chosen
    is carried to the end and proved by a fact before the build (`phases/interview.md`); what they have not is not inserted and
    not invented. This workshop is refined, not remade: the formats, phases and profiles that exist work as they did.

## Files

```
.aiediting-work/                 in the folder where the workshop was started
├── state.js  dashboard.html  index.html  serve.pid  serve.log
├── frames of the person's sources: `ae.py frames` prints their paths
└── монтаж-<слово>/
    ├── profile.json             the draft profile — data only, no keys
    ├── design/                  tokens, fonts, samples/ (chosen variants)
    ├── variants/<element>/      design variants shown side by side
    └── trials/01/ …             trial pieces, вопросы.json / ответы.json, out/
overlay-kit/                     in this skill: the method and tools of the `graphics` and `reedit` steps, copied into formats that use them
~/.agents/skills/монтаж-<слово>/ the installed format skill; pointer in ~/.claude/skills/
~/.aiediting/library.json        the pointer to the person's library, one per computer (`ae.py library`); the folder is theirs
~/.agents/skills/.aiediting-backups/  previous versions
```

## Updating AIEditing

Never mid-session. «Обнови AIEditing» → `npx skills update aiediting -g`, then a new session. Format
skills are separate folders with their own copy of the runtime: updating or removing AIEditing never
breaks them; a refinement rebuilds them on the new version.
