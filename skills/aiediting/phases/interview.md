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
| How it is approved | «план → готовый ролик»: every question of the plan first, then the whole video. «По частям» (parts approved one by one, then joined) is not built yet — say «пока нет» if asked | `approval` = `plan` |
| Pauses and cuts | cut or not; pause threshold (0.5 s) and margin (0.12 s); «э-э», «м-м» out, «ну», «вот» stay?; retakes — the last good take, the list to approve | `steps`, `params.gap`, `params.pad`, `params.fillers_cut`, `params.fillers_keep`, `params.retakes` |
| Layout and zoom | per layout from `sources`: zoom on a full face; none on «экран + лицо в окне»; «камера в бок, экран в бок» on separate tracks at moments to show; screen zoom on or off (only a note so far) | `steps` (`detect_layout`, `motion`), `params.layout`, `params.face`, `params.zoom_face`, `params.moves`, `params.zoom_screen` |
| Secrets | what is secret on their screen (mail, phones, cards, keys, chat names); the blur is always soft; nothing is closed without their mark | `steps` (`find_secrets`, `blur_regions`), `params.secret_frames` |
| Subtitles | a `.srt` beside or burned in; the brand and term glossary; language of the subtitles | `steps` (`write_srt` / `overlay_png`), `params.glossary`, `params.captions` |
| Chapters and graphics | timecodes in text; short dark plates at the bottom; cards over a face — by profile; over a screen — none, or small in the corner opposite the face, top or centre | `params.chapters`, `params.cards` (`on_screen`: `corner` · `top` · `center` · `none`), `params.graphics_per_15s` |
| Sound | target loudness (−16 LUFS; −14 for vertical); noise reduction off (not built: `true` only puts a note in the report); music only from their own library folder | `params.lufs`, `params.denoise`, `params.music` |
| Vertical | source: shot vertical, remade from horizontal, clips from a long one; 5–10 clips scored for approval; stack or face with inserts; burned-in captions; up to 60 s; Reels/Shorts/TikTok | `params.max_seconds`, `params.clips`, `params.layout`, `params.vertical_layout`, `params.captions`, `steps` (`vertical`, `export_platforms`) |
| Speech recognition | local whisper (free, private), ElevenLabs Scribe (precise, paid), any OpenAI-compatible address and model (OpenRouter too), their own command — from `runtime.asr.providers_help()` | `asr.provider`, `asr.model`, `asr.base_url`, `asr.api_key_env` |
| Where results go | the issue folder base; the language of the format | `output_dir`, `language` |

The recogniser question names the **variable** the key lives in (`ELEVENLABS_API_KEY`,
`OPENROUTER_API_KEY`, …): the person puts the value into their environment or `.env` themselves. Never
ask for the value, never print it.

Steps marked `not_built` in `catalog/steps.json` are never offered: the runtime does not do them yet,
and a profile that names one gets only a note in the report. Nothing is put in «на всякий случай».

## Steps

`steps` holds only what the answers chose, in the order the video goes through them; the names are the
step ids of `catalog/steps.json`. A step the person turned down is removed, not left switched off.

Next: `ae.py stage design`, read `phases/design.md`. A format with no visual layer (no plates,
captions or graphics) → `ae.py stage design skip --note "без оформления"`.
