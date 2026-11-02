# Interview

`ae.py stage interview`. The interview turns the draft profile into the person's format. It ends when
every theme below that applies to this format has an answer — not after a number of questions. How a
round is written: `prompts/question-round.md`.

## Rounds

**A round is 3–4 questions of one theme**, numbered; each with a recommended variant and why in half a
line, and — where the answer changes what the video looks like — **an example on the person's source**.
Before it goes out: `ae.py ask question --note "<тема>: <вопросы через запятую>"`. The answer closes it:
`ae.py answered --note "<their answer, short>"`. «Ок» accepts every recommendation.

Each answer goes into the draft at once: `python "<skillDir>/tools/ae.py" profile set <skill> <key>=<value>`
(values are JSON when they parse: `params.gap=0.4`, `steps=["speech_spans","cut_spans"]`,
`approval="parts"`). After each round `ae.py profile check <skill>`.

## Examples on their footage

- A still is enough for a layout or a plate: frames already on the dashboard, or `ae.py frames <path> --n 3`
  for a new moment; variants of a plate — `ae.py samples` (`phases/design.md`).
- A cut (pauses, fillers, retakes, zoom) needs motion: a short trial piece of 10–20 s with the variant in
  the profile — `ae.py trial <skill> <path> --start S --duration 15` — and the clip is on the dashboard.
- No source of the needed kind → `phases/sources.md`, «Missing kinds».

## Themes — the ones this format's steps touch

| Theme | Questions | Profile |
|---|---|---|
| How it is approved | «план → готовый ролик»: every question of the plan first, then the whole video. «По частям» (parts approved one by one, then joined) is not built yet — say «пока нет» if asked | `approval` = `plan`; `auto` when they want the finished video and no questions on every next run |
| Pauses and cuts | cut or not; pause threshold (0.5 s) and margin (0.12 s); «э-э», «м-м» out, «ну», «вот» stay?; retakes — the last good take, the list to approve; vertical — continuous speech: a stretch with no word longer than 0.25 s is cut, words keep 0.1 s before and 0.12 s after | `steps`, `params.gap`, `params.pad`, `params.fillers_cut`, `params.fillers_keep`, `params.retakes`, `params.word_gap`, `params.word_lead`, `params.word_tail`; «плотно» on a lesson: `params.gap` 0.3, `params.pad` 0.05, `params.editor` true (the agent's pass over the speech), `params.wordless` `cut` (needs a recogniser with exact word times; on local whisper it eats words) |
| Layout and zoom | per layout from `sources`: zoom on a full face; none on «экран + лицо в окне»; «камера в бок, экран в бок» on separate tracks at moments to show; screen zoom on or off (only a note so far) | `steps` (`detect_layout`, `motion`), `params.layout`, `params.face`, `params.zoom_face`, `params.moves`, `params.zoom_screen` |
| Secrets | what is secret on their screen (mail, phones, cards, keys, chat names); the blur is always soft; nothing is closed without their mark | `steps` (`find_secrets`, `blur_regions`), `params.secret_frames` |
| Subtitles | a `.srt` beside or burned in; the brand and term glossary; language of the subtitles | `steps` (`write_srt` / `overlay_png`), `params.glossary`, `params.captions` |
| Chapters and graphics | timecodes in text; short dark plates at the bottom; cards over a face — by profile; over a screen — none, or small in the corner opposite the face, top or centre | `params.chapters`, `params.cards` (`on_screen`: `corner` · `top` · `center` · `none`), `params.graphics_per_15s` |
| Animated inserts (a lesson, or any format that shows a screen) | offer them as a choice: where they list files, steps or points, or name a number, a short animation in their design plays beside the screen — in the corner opposite the face, instead of a card at that moment, never on a chapter plate, at most once per 30–60 s (45 recommended); the moments, template («файлы», «шаги», «список», «число») and text are approved before rendering. Say the price plainly: Node.js 22+ and HyperFrames with its own browser on disk (≈400 MB together), about 5 s of rendering per insert. On «да» → `ae.py doctor --steps animations`, then `doctor --install node` / `--install hyperframes` with their own «да» | `steps` (`animations`), `params.animations.every`, `params.animations.seconds` |
| Graphics over the video (a format where someone talks to the camera, 16:9) | offer them as a choice: the model writes scenes from the speech (cards, schemes, real screens they name), the speaker's frame moves between layouts, the speech stays as it is. Works with cuts too: scenes go on the finished video. Say the price plainly: Node.js 22+, Remotion and its browser in the working folder (≈700 MB), its licence is not open (free for individuals and teams up to 3), and rendering takes as long as the video or more | `steps` (`graphics`) |
| Sound | target loudness (−16 LUFS; −14 for vertical); noise reduction off (not built: `true` only puts a note in the report); music only from their own library folder | `params.lufs`, `params.denoise`, `params.music` |
| Speed | play the finished video faster? (1.05 — on 5%; the voice keeps its pitch, subtitles and timecodes follow) | `params.speed` |
| Vertical | source: shot vertically → the whole recording is cut (pauses and bad takes out), as long as it is, no clip pick and no limit; a long horizontal recording → 5–10 scored clips for approval, each up to 60 s; the mode follows the layout of the source (`auto`) unless they say «целиком» (`native`) or «нарезать» (`clips`); stack or face with inserts; burned-in captions; Reels/Shorts/TikTok | `params.vertical_source`, `params.max_seconds`, `params.clips`, `params.layout`, `params.vertical_layout`, `params.captions`, `steps` (`vertical`, `export_platforms`) |
| Speech recognition | local whisper (free, private), ElevenLabs Scribe (precise, paid), any OpenAI-compatible address and model (OpenRouter too), their own command — from `runtime.asr.providers_help()`; where the key is: they put it into their environment or `.env`, or it already lies in another `.env` and they give its path | `asr.provider`, `asr.model`, `asr.base_url`, `asr.api_key_env`, `asr.key_file` |
| Where results go | the issue folder base; the language of the format | `output_dir`, `language` |

The recogniser question names the **variable** the key lives in (`ELEVENLABS_API_KEY`,
`OPENROUTER_API_KEY`, …) and offers two ways, the person picks and does it themselves: put the value
into their environment or `.env`, or — when the key already lies in another `.env` (say, of another
tool) — give that file's path for `asr.key_file` (`~` is fine). The key is then read from that file at
each run and copied nowhere: not into the profile, the format skill, the report or the log. Never ask
for the value, never open or print the file.

Steps marked `not_built` in `catalog/steps.json` are never offered: the runtime does not do them yet,
and a profile that names one gets only a note in the report. Nothing is put in «на всякий случай».

## Steps

`steps` holds only what the answers chose, in the order the video goes through them; the names are the
step ids of `catalog/steps.json`. A step the person turned down is removed, not left switched off.

Next: `ae.py stage design`, read `phases/design.md`. A format with no visual layer (no plates,
captions or graphics) → `ae.py stage design skip --note "без оформления"`.
