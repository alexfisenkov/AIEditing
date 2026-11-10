<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/aiediting-logo-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/aiediting-logo-light.png">
    <img src="assets/aiediting-logo-light.png" alt="AIEditing" width="440">
  </picture>
</p>

<p align="center"><strong>Show it once how you edit — your agent edits that way from then on.</strong></p>

<p align="center"><b>English</b> · <a href="README.ru.md">Русский</a></p>

A workshop that builds **your own video-editing skills** for AI agents. You go through an interview
once — which formats you shoot (stream, lesson, vertical or your own), how each should be cut, what the
captions and chapter plates look like — watch a trial edit on **your** footage, say what you don't like
until it is right, and get a format skill named after your word, such as `монтаж-урок` ("lesson
edit"). After that, in any folder, you just say "edit this like a lesson".

> Status: early version (0.3.1).

<p align="center">
  <a href="assets/aiediting-dashboard.png"><img src="assets/dash-now.png" width="380" alt="The dashboard: the current stage, what it is waiting for, your formats and the frames of your source"></a>
  <a href="assets/aiediting-dashboard.png"><img src="assets/dash-design.png" width="380" alt="Design variants side by side on a frame of your source"></a>
  <a href="assets/aiediting-dashboard.png"><img src="assets/dash-trial.png" width="380" alt="A trial edit waiting for your answer"></a>
</p>

<p align="center"><sub>Stages · design variants · a trial edit, on demo data — <a href="assets/aiediting-dashboard.png">open the full dashboard</a></sub></p>

**And you can always see what's going on.** The dashboard opens beside the chat by itself and runs on your own computer: the current stage and what it is waiting for, frames of your footage, design variants side by side, trial clips with your verdicts, the skills already built. Two themes, Russian and English.

---

## Installation

### If you'd rather not open a terminal

Open your AI agent — Claude Code, Cursor, Codex — and paste this:

```
Install the AIEditing skill for me. Run in the terminal:

npx skills add alexfisenkov/AIEditing --skill aiediting -g -y -a <put yourself here: claude-code, cursor, codex>

Find the installed aiediting folder (the one containing tools/ae.py). Then run:
python3 "<installed aiediting folder>/tools/ae.py" setup
Run the same command with setup --check and report its result. npx only copies the skill files.
Tell me the combined size of heavy downloads once and continue without asking per tool.
If npx, Python or a system package manager is missing, install it where supported and
report the exact blocker if that fails. Do not upload media or use a paid API.
When setup --check passes, tell me that installation is ready and the session needs a restart.
```

The agent does the rest. Then restart it — skills are loaded at startup.

### From the terminal

```bash
npx skills add alexfisenkov/AIEditing -g
```

The installer asks for which agents to install — confirm, locate the installed `aiediting`
folder, and then run `python3 "<skillDir>/tools/ae.py" setup`. Verify with
`python3 "<skillDir>/tools/ae.py" setup --check`. `npx skills add` alone does not install
the editing dependencies.

<details>
<summary>Unattended install and setup</summary>

```bash
npx skills add alexfisenkov/AIEditing --skill aiediting -a claude-code -g -y
# Then locate the installed aiediting folder:
python3 "<skillDir>/tools/ae.py" setup
python3 "<skillDir>/tools/ae.py" setup --check
```

| Flag | What it does |
|------|--------------|
| `--skill aiediting` | Installs only AIEditing |
| `-a claude-code` | Installs for Claude Code |
| `-g` | Globally — the workshop and every format skill it builds work in any folder |
| `-y` | Don't ask questions |

</details>

**Bootstrap requirements:** [Node.js](https://nodejs.org) 22.20+ for `npx` and Python
3.9+ to start `ae.py`. The maintained toolkit pins Node.js 26.13.0 or newer.
`setup` prepares a private Python 3.12–3.14 environment when the host Python is older,
then installs and checks the complete maintained local toolbox (19 catalog tools on
supported systems), including models and render browsers. It reports a concrete failure
if a required component cannot be installed. `setup --steps a,b --asr whispercpp`
repairs only the dependencies of a requested format. `ae.py capabilities [--json]`
inspects the available tools and FFmpeg filters on this machine; availability alone
does not prove an effect works on a given recording.

| System | State |
|---|---|
| macOS | locally checked on Apple Silicon; CI workflow provided |
| Windows | installation path and CI workflow provided; setup installs the checksum-verified official whisper.cpp CPU archive for x64 or ARM64 |
| Linux | not tested |

CI is configured to run unit tests and install the pinned Python packages. The new 0.3.x changes have not yet completed hosted CI or physical Windows acceptance. Rendering of animated inserts and graphics is checked locally on macOS. Editing by markers needs a timeline exported from Final Cut, which runs only on a Mac.

---

## How to use it

1. Type `/aiediting`. A dashboard opens beside the chat (or in your browser): stages, your answers,
   frames of your footage, design variants side by side, trial clips.
2. Choose: **a new format skill** or **refine** one you already have.
3. New: pick formats from the list and add your own through commas («урок, вертикаль, подкаст»). Give
   1–3 source videos. Answer the questions in rounds of 3–4 — each with a recommended option and an
   example on your video. Pick the design: your own style or the Chrome & Graphite example.
4. Watch the trial edit. «Нет» → say what is wrong, show how it should and should not be, what to add or
   remove and where — the workshop reworks it until you say «да».
5. The skill `монтаж-<your word>` is built and installed globally. In a new session, anywhere:
   «смонтируй ~/Videos/lesson.mp4» or «смонтируй как урок».

The list offers seven formats, under these words; anything else you name becomes your own format:

| In the list | What it does |
|---|---|
| эфир (stream) | barely touches it: blur over secrets, loudness, `.srt` beside the video |
| урок (lesson) | cuts pauses and "uh", chapter plates, `.srt` beside the video |
| youtube | an episode with chapters; you approve the plan once, part-by-part approval is not built yet |
| вертикаль (vertical) | 9:16, speech without pauses, burned-in captions, export for three platforms, clips up to 60 s from a long recording |
| наложения (overlays) | the speech stays whole, without a single cut; graphics and real screens on top |
| ютуб (YouTube with graphics) | clean speech from your takes, or one whole take with only its edges trimmed; graphics and real screens on top, remarks by Final Cut markers |
| нарезка (clips from a finished video) | from an edited horizontal video: 9:16 clips, two ways to choose from after a probe (below) |

For a lesson (and any format that shows a screen) you can choose **animated inserts**: where you list
files, steps or points, or name a number, a short animation in your design system plays beside the
screen, in the corner opposite your face, at most once every 30–60 s (`params.animations.every`, 45 by default).

- You approve the moments, the template («файлы», «шаги», «список», «число») and the text before anything is rendered. An empty answer means no animations.
- The first setup includes Node.js 26.13.0+, HyperFrames 0.9.28 and its browser (roughly 400 MB for Node and HyperFrames together); an insert takes about 5 seconds to render.
- The full supported toolkit is prepared by `ae.py setup` at installation. If needed later,
  `ae.py setup --steps animations` repairs these dependencies.
- HyperFrames comes from a checked lockfile (`npm ci --ignore-scripts`) into `~/.aiediting/node` (Windows: `%LOCALAPPDATA%\AIEditing\node`). Its telemetry is off, and its project history is written into the issue's work folder and goes with it.

**Clips from a finished video** go one of two ways, and you choose after seeing both on one stretch of your own video: the
picture whole in the centre, with a headline and a call to action on the fields and a short teaser; or a real re-edit for 9:16,
where the speaker moves between bottom, top and a circle, the same graphics are rebuilt, and text keeps to the platform's safe
zones. The re-edit is made by the model with the Remotion kit; the initial shared renderer and browser download is about 700 MB, plus the render
time. As a way of editing it has been accepted on one real video; the built skill has passed its tests but has not yet made a
video end to end.

**An open workshop.** AIEditing is a base of ways to edit: narrow skills come out of it for a niche, a task, your own design system,
under your word and with the paths of the format they start from. A
way the catalog lacks is investigated against the source, built and validated on a real output before
it becomes a catalog step with runtime and tests. Any installed `монтаж-*` can be refined later, even one written by
hand: what a profile does not describe stays with the skill and is changed together with you.

**Without questions.** Say «без вопросов» in your first message and give a recording:

```
/aiediting новый формат «обращение», без склеек, в нашем стиле, без вопросов, вот запись
```

The workshop takes what it can find out — the
design system you mentioned, real screens of what you named, the output folder of your other skills — and decides the
rest itself. You get the finished video, the installed skill, and one list: what it decided, what it installed, what it
opened and what it could not know. The limits do not change: nothing is published, generated or paid for, your speech
goes to no outside service unless you named one, and no key is asked for. The format then keeps running without
questions until a refinement turns that off.

**Graphics over the video.** For anyone talking to the camera in 16:9: the model reads the whole speech and writes
scenes on the words, with real screens and materials you named; the speaker's frame moves between layouts. The speech
stays as it is, and with cuts the scenes go on the finished video. Scenes are checked by contact sheets, a search for
empty stretches and a sound check against the base video. The shared toolkit includes Node.js 26.13.0+ and Remotion
4.0.542 with its browser (about 700 MB for initial setup; see its licence below); rendering takes about as long as the video.

**YouTube with graphics.** The speech is assembled from your best takes, or a whole take keeps everything but its edges; the speed you set goes on once, graphics go on top. You mark
remarks with Final Cut markers: cuts land on the finished video and the scenes keep their places. So far this format has
been proven on one real video.

A format skill puts the result into `<your issues folder>/<date-topic>/`: the video, a `.srt` when the
format makes one, and a short report. A remark after watching goes into that report, and the skill
suggests running AIEditing to refine the format.

---

## Tool methods

The parent includes a [task-based handbook](skills/aiediting/references/methods.md), with source
selection, tuned recipes, failure signs and output checks for the maintained toolbox. It adapts the
supplied editing skills to the local runtime and distinguishes measurements from editorial decisions.
`python3 <skillDir>/tools/recipes.py --help` lists seven checked scene/audio/subtitle/stabilization/quality
examples. These do not change an installed format profile or add native pipeline step names.

## What it does and what it never does

| Does | Never does |
|---|---|
| interviews you and builds a format skill from your answers, or takes one message if you ask for no questions | publishes, uploads or sends anything |
| edits **a trial piece** of your source to show you; where a format has several paths, a short probe of each and then the chosen one in full; without questions, the whole recording | voices, generates video, music or images |
| installs its full supported local toolkit with `ae.py setup`; repairs a task's subset on demand without per-tool questions | asks for a key or prints one |
| keeps the previous version of a skill and restores it in one command | puts into a skill anything you did not choose |

---

## Speech recognition — what is best where

| Provider | Cost | Privacy | Word boundaries | Best for |
|---|---|---|---|---|
| Local whisper (whisper.cpp) | free | the recording stays on your computer | good for captions; short words and "uh" are sometimes lost, and when cutting inside speech it can clip a word or invent one in silence, so listen to the joins | private recordings, no budget |
| ElevenLabs Scribe | paid | the recording goes to ElevenLabs | the most precise | lessons where every pause and "uh" is cut |
| Any OpenAI-compatible service (OpenAI, OpenRouter, your own server) | depends | goes to the address you set | depends on the model | when you already pay for one |
| Your own command | yours | yours | yours | anything else |

Changing the provider is one answer in the interview or a refinement.

---

## Tools and licences

The maintained toolkit is defined by `skills/aiediting/catalog/tools.json` and
`catalog/extra-tools.json`. Each entry has a pinned version or verified minimum,
source and licence. `ae.py setup` installs the complete supported set after an
installation request and announces heavy download sizes together. Its packages and
models are reusable across formats; a working folder still holds each video's media
and render outputs. Format skills remain limited to their chosen steps and dependencies.
The maintained set is finite: inspect `ae.py capabilities` and validate a real local
route for an effect outside the catalog. No command guarantees every conceivable edit.

| Tool | What for | Licence | Weight |
|---|---|---|---|
| FFmpeg Full 9.0.2+ | cuts, joining, audio, ASS subtitles, stabilization, Rubber Band, VMAF and export | GPL-3.0-or-later for the selected full builds | build and shared dependencies |
| whisper.cpp 1.9.5+ + large-v3 model | local speech recognition | MIT | the model is ≈3 GB |
| Pillow 13.0.0, numpy 2.5.4, OpenCV 5.0.0.93 | plates and captions as images, face and layout | MIT-CMU, BSD-3-Clause, Apache-2.0 | Python packages |
| YuNet model | finding the face for layouts, verticals and graphics | MIT | light |
| Tesseract 5.5.4+ | text on frames when looking for secrets (Apple Vision on macOS) | Apache-2.0 | light |
| Node.js 26.13.0+ + HyperFrames 0.9.28 | animated inserts in a lesson: files, steps, a list, a number | MIT, Apache-2.0 | Node ≈100 MB; HyperFrames with its browser ≈300 MB |
| Remotion 4.0.542 + renderer browser | graphics over video from a lockfile; reusable toolkit installation | Remotion License | ≈700 MB for the initial shared renderer and browser |
| Playwright 1.65.0 | capture reference screens through an available local Chrome | Apache-2.0 | no separate Playwright browser download |
| ONNX Runtime 1.31.1 + RVM MobileNetV3 | local human foreground matte for removing or replacing a video background, including "behind the head" compositing | MIT, GPL-3.0 model project | model and runtime download |
| PySceneDetect 0.7.3, SoundFile 0.14.0, librosa 1.0.0, pysubs2 1.9.1 | local scene, audio and subtitle analysis; these libraries do not edit a complete video by themselves | BSD-3-Clause, BSD-3-Clause, ISC, MIT | librosa has larger Python dependencies |
| rembg 2.0.87 + BiRefNet General Lite | local still-image background removal with an explicitly selected model; separate from human video matting | MIT code and MIT model | pinned model: 213.63 MiB; no default BRIA model |

The current private Python set includes Pillow 13.0.0, numpy 2.5.4, OpenCV
5.0.0.93 and ONNX Runtime 1.31.1 on a compatible Python. An older host Python
can start the installer; AIEditing selects or bootstraps a private Python 3.12–3.14
without replacing the system interpreter. The catalog records compatible older
pins for legacy environments.

> **Remotion is not open source.** It is free for individuals, companies of up to three employees and non-profits;
> larger companies need a paid licence. Check the terms at remotion.pro before choosing graphics over the video.
> `setup` downloads the supported local toolkit after an installation request. It does
> not install arbitrary third-party packages; a specialist request is checked against
> its source and requirements and validated on an actual output.

For a person in video:

```bash
python3 "<skillDir>/tools/ae.py" background input.mp4 output.mov --mode remove
```

This produces transparent ProRes 4444 by default. `--mode solid|image|video|blur`
replaces the background; `--value` supplies a colour or image/video path where needed.
The matting runs locally on Apple Silicon, including M1, without an upload or paid inference.
Inspect a short preview and edges before a full export. It is designed for humans, not arbitrary
objects, and a difficult shot may need cleanup.

For a **still image** containing a person or object, use the separate local route:

```bash
python3 "<skillDir>/tools/ae.py" image-cutout input.png cutout.png
```

It uses rembg with the explicitly pinned MIT BiRefNet General Lite model and writes a
transparent PNG. It does not select rembg's default BRIA model or turn a still-image
segmenter into a video tracker. Inspect the alpha edge on the actual image.

[OpenMontage](https://github.com/calesthio/OpenMontage) (AGPL-3.0) is a full production pipeline from
script to generation; AIEditing does not include it — only this link.

---

## Keys

Keys live only in your environment or in a `.env` file (see `.env.example`); AIEditing reads them
by variable name and never prints them. Never paste a key into the chat.

The key already lies in another place — say, the `.env` of another tool? Give that file's path as
`asr.key_file` in the interview (`~` works). The key is read from it at every run and copied nowhere:
not into the profile, the format skill, the report or the log. Lookup order: the environment, then
`key_file` if it is set (and only it: no file or no variable in it is an error naming both);
without `key_file` — `.env` in the working folder, then `~/.aiediting/.env`
(Windows: `%LOCALAPPDATA%\AIEditing\.env`).

---

## Updating and removing

```bash
npx skills update aiediting -g      # or just tell your agent: «обнови AIEditing»
npx skills remove aiediting -g
```

Start a new session after updating. Format skills built by AIEditing are separate folders with their
own copy of the editing runtime: updating or removing AIEditing does not touch them. A refinement
rebuilds a skill on the current version and keeps the previous one in
`~/.agents/skills/.aiediting-backups/`; the workshop brings it back on request.

If you installed animated inserts: the Node packages live in `~/.aiediting/node` (Windows:
`%LOCALAPPDATA%\AIEditing\node`) and the render browser in `~/.cache/hyperframes/chrome` (≈200 MB). The
browser is shared with other HyperFrames installs and is not removed with the `node` folder: delete that
folder yourself if nothing else needs it.

---

## What's in the repository

```
skills/aiediting/        the skill itself (what gets installed)
├── SKILL.md             the workshop's order and rules
├── phases/  prompts/    one file per stage, read when the stage starts
├── tools/ae.py          one command per event: dashboard, profiles, build, install, doctor
├── tools/state/         the dashboard page, state and local server
├── templates/           the format-skill template and starting profiles
├── catalog/             formats, steps, tools with licences and pins
├── runtime/             editing mechanics copied into every format skill
├── overlay-kit/         graphics over the video: scenes, the camera, cuts by markers
├── schema/  design/     profile schema, example design system
assets/                  the logo and dashboard screenshots for this page
tests/                   python3 -m unittest discover -s tests -v
.github/workflows/       CI on macOS and Windows, monthly install check
```

---

## Development

```bash
python3 -m unittest discover -s tests -v
```

Tests make their own synthetic media with ffmpeg, install skills only into a temporary home folder and
never use the network.

---

## License

[MIT](LICENSE) © Alexander Fisenkov — you may use, modify and distribute it, including in commercial projects. The
dashboard and its server are adapted from [AISpa](https://github.com/alexfisenkov/aispa); the MIT notices are kept in
`skills/aiediting/tools/state/NOTICE.md`.
