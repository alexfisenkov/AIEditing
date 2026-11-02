# Without questions

Read instead of the other phases when the person asked to get the result and not to be asked: «без
вопросов», «не спрашивай», «сам всё сделай», «как я сказал, так и делай». **Only such words switch it
on**, or `approval: auto` of a skill being refined. A wish for speed or a short request is not this signal,
and «сам реши» in answer to one question is an answer to that question. Their one message is the brief. They
see the finished video and one list: what you decided and what you could not know.

Not one question until then, in the chat or on the dashboard: no `ae.py ask`. A real blocker is said once
and the run stops: no video when a new format was asked for, an unreadable video, no Python, no ffmpeg, no
recogniser that can run here, or a disk too full for what the format needs.

## Stays closed in this mode

Nothing is published, uploaded, sent, voiced or generated. Nothing paid runs, and speech goes to no outside
service: a paid or remote recogniser only when the person named it, or named a format skill that uses it.
A key found on the disk does not choose one; it goes into the list. A key is never asked for, echoed or
written; a key or password in their message is left out of everything you write down. Passwords are not
typed, and nothing is written into a site you read. A fact about the person is not invented: it is found,
or it is a visible gap.

## 1. Open

`ae.py list-skills` first, and `.aiediting-work/state.js` if it is there. One of four:

- **They want a video from a format they have, and no change to it** («смонтируй как урок, без вопросов»): no
  workshop. Run that skill as its `SKILL.md` says, with `--no-questions`. Stop reading here.
- **They want an installed format changed:** `init --mode refine --no-questions --fresh`, `ae.py profile open
  <skill>`. Its `approval` stays as it is unless they ask.
- **An unfinished workshop here, on the same format and source:** `ae.py no-questions`, keep the draft.
  On anything else: `init --mode new --no-questions --fresh`.
- **A new format:** `python "<skillDir>/tools/ae.py" init --mode new --no-questions --title "<their words>"`.

The format's name is their word. They gave none → a short word from their message or the file's name, and
not one an installed skill already has. Open the dashboard as `phases/start.md`, §2, says; it asks nothing.
With a video: `ae.py frames "<video>" --n 3`, and look at them.

Keep `.aiediting-work/<skill>/решения.md` from now on. Its first lines are their message, without keys or
passwords, and the path to the video. Then a line at a time: the issue folder, the working folder, every
decision, tool, gap and page you opened. It is your memory and your last message.

## 2. Gather what is known

From their message and the disk, before deciding anything; write what you find into `решения.md`. Materials
the speech names come later, by the kit's order of work, because the speech is not known yet.

| What | Where to look | Nothing found |
|---|---|---|
| Design system, when they mentioned a style | the system they named, or for «в нашем стиле» the current project (`design-system/`, `tokens.*`, its `CLAUDE.md`, `AGENTS.md`), then the skills of this session. Several → the one the project's instructions name. The name Chrome & Graphite with no such system in the project: the bundled example | the bundled example, and say so |
| Design system, when they mentioned none | not looked for: the format's own design, or the bundled example. A format with no visual layer needs none | |
| The mark in the corner | a file they named, or the logo of the design system they mentioned | no mark; a line in the list |
| Real materials | a site, product or file they named: only note it here, it is captured later by `overlay-kit/tools/capture-guide.md`, read only. No place for it in the speech: where it fits best, stated in the list | scenes without it; a line in the list |
| Remarks on a skill being refined | «Замечания для доработки» in `отчёт.md` of its latest issue folder | |
| Output folder | a sibling of another installed format skill's `output_dir` | `Монтаж/<слово>` beside the source |
| Speech recogniser | what they named; otherwise local whisper | |
| Whisper's model file | `asr.model` and `params.verify_asr.model` of other format skills; `~/.aiediting/models/`. Two models → the larger for `asr` | `ae.py doctor --install whisper-model --yes` (≈3 GB, in the background), then `asr.model` |
| Brand names, terms | the project's texts; what they said | what is heard, marked in the list |
| What they mean by the style | a video or frame they pointed to; earlier work they named | your judgement, stated in the list |

## 3. Their words become the format

A new format: `ae.py formats "<word>"`, with `--preset overlay` when the first row below holds; then `ae.py profile
set <skill> approval=auto`. `phases/interview.md`, «Themes», is your reference for steps and parameters; you do not
ask its questions. Set them: `ae.py profile set <skill> steps=[...] params.x=...`. Take the rows from the top:

| They said or the frames show | The format |
|---|---|
| no cuts, and graphics, overlays, «красиво», «вау» | `--preset overlay` |
| no cuts, or a silent stretch that shows something («молча показываю»), and nothing about graphics | no `cut_spans`, no `graphics`: `steps=["loudnorm","write_srt"]` |
| anything else | that format or `custom`; `graphics` added when they asked for graphics |

Then, for every format:

| When | Add |
|---|---|
| `cut_spans` is in the steps | `verify_words`: the second listening stands in for the person's ear, with a local `params.verify_asr` when the main recogniser is paid or a second local model is at hand: the same model does not catch its own mishearings. Cuts of pauses are safe on any recogniser; cuts inside speech need exact word times, so on local whisper leave `params.wordless` out, keep `params.editor` to what you check by hearing the result again, and say so in the list |
| a screen is visible | `find_secrets`, `blur_regions`. Local and free; a secret left open cannot be taken back |
| the frame is not 16:9 and they asked for graphics | no `graphics`; a line in the list |

The design: the system you found goes into `.aiediting-work/<skill>/design/tokens.json`, in the shape of
`<skillDir>/design/chrome-graphite/tokens.json`, with its fonts when their licence allows copying and its logo or the
named file as `logo.svg` or `logo.png`; the bundled example is `ae.py design-example <skill>`. What holds for the
format goes into the taste, in their words: `ae.py profile taste <skill> "…"`. What concerns this one video stays in
`решения.md`. So the next video comes out the same way without you deciding again.

## 4. Tools

`ae.py doctor --steps <steps> --asr <provider>`. Asking for no questions is the «да» to the tools of the
chosen steps, by their pins: `doctor --install <id> --yes`, each one written down, with its licence and its size
when the catalog has one. A tool of an optional step that cannot be installed → the step goes out of the profile
and into the list; the core is a blocker, above. Remotion has no `--install`: the kit's `prepare` installs it from
its lockfile, with the renderer's browser (≈700 MB per working folder).

## 5. Make the video through the skill itself

```bash
python "<skillDir>/tools/ae.py" stage build
python "<skillDir>/tools/ae.py" build-skill .aiediting-work/<skill>/profile.json .aiediting-work/build --replace
python .aiediting-work/build/<skill>/tools/run.py edit "<video>" --topic "<тема из их сообщения или имени файла>"
```

Add `--no-questions` when the profile's `approval` is not `auto`. A refinement with no video: skip the run, and say the
change has not been tried. Exit code 3 is for you: the built `SKILL.md`, «Without questions», says how to decide, and
what it says to look at after a run holds at any exit code. A failed check of the cut is fixed in the profile, and
the skill is built and run again.

A format with `graphics`: go on by `.aiediting-work/build/<skill>/SKILL.md`, «Graphics». Take the time the method
takes, with parallel executors for scenes where your environment has them. On a metered account this is the one real
cost of the mode: say so at the end.

## 6. Install and hand over

The call was the request for the skill, so no separate «да». A check you could not fix: the video is not called
finished, it goes first in the list, and the skill is not installed: its draft stays in the workshop.

```bash
python "<skillDir>/tools/ae.py" install-skill .aiediting-work/build/<skill>
python "<skillDir>/tools/ae.py" finish --result "<what is installed, one line>"
```

Then one message, in their language, from `решения.md`:

- where the video is;
- what you decided for them: the format, the design system and where it came from, what was cut, the folders;
- what was checked by frames and by measurement, and that nobody watched it end to end with sound unless you did;
- secrets: whether they were looked for and that only the recording was searched, in sampled frames, for typical
  patterns, so a search can miss them; which stretches you closed and looked at; what was said aloud stays in the sound
  and in the text files beside the video;
- the pages you opened and the seconds of the video that show them, and that their address stays in that browser's
  history; logos added, with «check the brand's rules before publishing»;
- tools installed; Remotion's licence when used: free for individuals and teams up to three, paid beyond that, check
  before commercial use; the working folder with its size, kept until they accept;
- what is missing, as one numbered list;
- how to repeat it («смонтируй как <слово> <путь>» in a new session). With `approval: auto`: this format now runs
  without questions, and «доработка» can turn that off. Otherwise: the next run asks again unless they say «без
  вопросов». For a replaced skill: `ae.py restore-skill <name>` brings the old one back.

## After their remark

Still without questions, unless they ask for them. What holds for the format: `ae.py profile taste`, change what it
changes. What concerns this video only: `решения.md`. Build and run again, install, show.
