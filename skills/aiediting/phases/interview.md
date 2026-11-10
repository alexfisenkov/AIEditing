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
`approval="plan"`). After each round `ae.py profile check <skill>`.

## Examples on their footage

- A still is enough for a layout or a plate: frames already on the dashboard, or `ae.py frames <path> --n 3`
  for a new moment; variants of a plate — `ae.py samples` (`phases/design.md`).
- A cut (pauses, fillers, retakes, zoom) needs motion: a short trial piece of 10–20 s with the variant in
  the profile — `ae.py trial <skill> <path> --start S --duration 15` — and the clip is on the dashboard.
- No source of the needed kind → `phases/sources.md`, «Missing kinds».

## A format with paths: the first question

Before the rounds, one message of your own, built on what you saw in their video and what they have seen elsewhere; not the
catalog's text read out. Name the paths and what each costs. Offer another where you see one. It ends with the probes, not with
a decision on words:

```
Из такого ролика вертикаль можно сделать двумя способами:
1. Картинка целиком: ваш кадр как есть, с заголовком и призывом сверху и снизу. Быстро, но мелкий текст на экране станет мельче,
   а звук берётся из готового файла: если под речью подложка, она останется.
2. Перемонтаж: как в роликах, где спикер то снизу, то сверху, то кружком, а графика пересобрана под вертикаль. Дольше: нужен
   Remotion (≈700 МБ) и проверка каждого ролика по кадрам.
Покажу оба на одном вашем отрывке, а вы выберете. Или вам сразу ясно, какой не нужен?
```

`ae.py ask choice --note "какой путь: пробы или сразу"`. A path they turn down in words is not probed: their word is enough.
None is chosen here: `ae.py variant` waits for `phases/trial.md`.

**What a probe needs is asked now, before `phases/trial.md`, for every path not turned down.** A probe is a real edit on their
video and has nothing to guess from:

- `bands`: how much the source is already sped up and the speed wanted; the call to action as one text, or none; in whose words the
  headline is; the colour of the fields; the design. When they lean to this path, say again that its sound comes from the finished
  file: a bed under the speech stays in every clip and nothing here takes it out.
- `reedit`: the call to action in parts, or «без призыва», which is `params.cta_parts=null`, not an empty one; where the working folder
  of the long video lies, with its scenes, assets and clean speech, and if there is none, whether a bed lies under the speech; how
  much the source is already sped up and the speed wanted; the design.

Everything else of a path, such as the number of covers or the teaser, is asked once that path is chosen.

## The first round: the recording

For a format where someone talks to the camera, after the one question about the niche and before every other theme, in this order: the first answer decides which themes are
asked at all. Not for a format made from a finished video: the edit has already decided these. One round, with a recommendation in each, as any
round. `ae.py profile check` and `build-skill` refuse a format with clean speech and no answer to the first.

```
1. Что делаем с записью?
   а) паузы и «э-э» убирает монтаж, по порогу: так обычно для урока, если дублей нет;
   б) вы пишете дублями и молчите, пока что-то работает: я собираю чистую речь из лучших дублей;
   в) один дубль, ничего внутри не режем, подрезаю только края;
      б и в идут только с графикой поверх: Remotion ≈700 МБ на ролик, рендер не короче самого ролика, лицензия не открытая;
   г) файл как есть, без единой склейки.
2. Ускоряем? Я бы оставил как есть, если вы не просите. Голос не меняется, субтитры и сцены идут следом.
3. Откуда текст речи и кто его читает? Я бы взял локальный whisper: бесплатно и приватно. Слова для экрана проверяю на слух.
```

1. **Do we cut the recording, or does it stay whole?**
   - а) The pipeline cuts pauses: no `params.recording` and no `params.clean_speech`, `cut_spans` in the steps, the theme «Pauses and cuts» follows.
   - б) Takes and silences while something runs: `params.recording` `takes`, `params.clean_speech` true, `graphics` in the steps. «Pauses and cuts» is not
     asked: this speech has no pipeline cuts, and `cut_spans` would cut twice.
   - в) One take they do not want touched, only the edges: `trim`, the same.
   - г) The file exactly as it is: `whole`, no clean speech and no cuts.

   б and в need the kit, so they go with `graphics` and a 16:9 frame, and the theme «Graphics over the video» is then already answered. Graphics turned down or another frame: б becomes а; в becomes г, and say that the edges are then not trimmed. A built skill switches between б and в, and to «как есть», by their word for a video;
   the answer here is its default. A format on а or г changes its way only through a refinement.
2. **Do we speed it up, by how much?** `params.speed`, or none. It is applied once, to the finished video, however the speech was made.
3. **Where does the text of the speech come from, and who reads it?** The recogniser (the theme below). It hears the speech before the speed-up, and on local whisper
   a word that goes on screen is worth checking by ear: `run.py hear --from --to`. On б and в choosing takes always hears by local whisper, whatever writes the `.srt`, so with
   another recogniser its model goes into `params.verify_asr.model`. They read the `.srt` themselves: `approval` `plan`. They want the finished video and no questions: `auto`, and you read it.

`catalog/params.json` holds who applies what, and it is what a new step or a new way reads first.

## Themes — the ones this format's steps touch

| Theme | Questions | Profile |
|---|---|---|
| Niche and audience | one question, early, for every format: what the niche is and who watches. It decides the tone of whatever goes on screen, how long a piece may be, what is worth showing and which terms stay as they are. Their answer in their words is a taste line, and what it changes goes into the parameters | `ae.py profile taste`, `params.max_seconds`, `params.glossary` |
| How it is approved | «план → готовый ролик»: every question of the plan first, then the whole video. «По частям» (parts approved one by one, then joined) is not built yet — say «пока нет» if asked | `approval` = `plan`; `auto` when they want the finished video and no questions on every next run |
| Pauses and cuts | cut or not; pause threshold (0.5 s) and margin (0.12 s); «э-э», «м-м» out, «ну», «вот» stay?; retakes — the last good take, the list to approve; vertical — continuous speech: a stretch with no word longer than 0.25 s is cut, words keep 0.1 s before and 0.12 s after | `steps`, `params.gap`, `params.pad`, `params.fillers_cut`, `params.fillers_keep`, `params.retakes`, `params.word_gap`, `params.word_lead`, `params.word_tail`; «плотно» on a lesson: `params.gap` 0.3, `params.pad` 0.05, `params.editor` true (the agent's pass over the speech), `params.wordless` `cut` (needs a recogniser with exact word times; on local whisper it eats words) |
| Layout and zoom | per layout from `sources`: zoom on a full face; none on «экран + лицо в окне»; «камера в бок, экран в бок» on separate tracks at moments to show; screen zoom on or off (only a note so far) | `steps` (`detect_layout`, `motion`), `params.layout`, `params.face`, `params.zoom_face`, `params.moves`, `params.zoom_screen` |
| Secrets | what is secret on their screen (mail, phones, cards, keys, chat names); the blur is always soft; nothing is closed without their mark | `steps` (`find_secrets`, `blur_regions`), `params.secret_frames` |
| Subtitles | a `.srt` beside or burned in; the brand and term glossary (a brand everywhere, whatever its case); language of the subtitles. A correction for one video is not the glossary: it goes through `ответы.json` | `steps` (`write_srt` / `overlay_png`), `params.glossary`, `params.captions` |
| Chapters and graphics | timecodes in text; short dark plates at the bottom; cards over a face — by profile; over a screen — none, or small in the corner opposite the face, top or centre | `params.chapters`, `params.cards` (`on_screen`: `corner` · `top` · `center` · `none`), `params.graphics_per_15s` |
| Animated inserts (a lesson, or any format that shows a screen) | offer them as a choice: where they list files, steps or points, or name a number, a short animation in their design plays beside the screen — in the corner opposite the face, instead of a card at that moment, never on a chapter plate, at most once per 30–60 s (45 recommended); the moments, template («файлы», «шаги», «список», «число») and text are approved before rendering. State the disk use: Node.js and HyperFrames with its browser (≈400 MB together), about 5 s of rendering per insert. Once requested, `ae.py setup --steps animations` repairs local dependencies without another per-tool question | `steps` (`animations`), `params.animations.every`, `params.animations.seconds` |
| Graphics over the video (a format where someone talks to the camera, 16:9) | offer them as a choice: the model writes scenes from the speech (cards, schemes, real screens they name), the speaker's frame moves between layouts, the speech stays as it is. Works with cuts too: scenes go on the finished video. Say the price plainly: Node.js 22.12+, Remotion and its browser in the working folder (≈700 MB), its licence is not open (free for individuals, companies of up to three employees and non-profits), and rendering takes as long as the video or more | `steps` (`graphics`) |
| Sound | target loudness (−16 LUFS; −14 for vertical); whether the source has steady noise to reduce, checked on a representative stretch; music only from their own library folder | `params.lufs`, `params.denoise`, `params.music` |
| Speed | asked in the first round: play the finished video faster? (1.05 — on 5%; the voice keeps its pitch, subtitles and timecodes follow) | `params.speed` |
| Vertical | source: shot vertically → the whole recording is cut (pauses and bad takes out), as long as it is, no clip pick and no limit; a long horizontal recording → 5–10 scored clips for approval, each up to 60 s; the mode follows the layout of the source (`auto`) unless they say «целиком» (`native`) or «нарезать» (`clips`); stack or face with inserts; burned-in captions; Reels/Shorts/TikTok | `params.vertical_source`, `params.max_seconds`, `params.clips`, `params.layout`, `params.vertical_layout`, `params.captions`, `steps` (`vertical`, `export_platforms`) |
| Human background and effects behind the head | ask whether to leave the scene, remove the background to transparent MOV, use a solid colour, image, video or blur. For image/video, ask for the actual local file; for solid, the colour. If selected graphics or a plate should pass behind the person, use `behind_head` with the corresponding overlay step, then show a preview on their footage. The local RVM model produces a human matte on Apple Silicon including M1; edges, hair and motion blur need visual inspection. Do not promise arbitrary object segmentation | `params.background` with `mode`, `value`, optional `model` and `downsample_ratio`; `steps` (`behind_head` plus the chosen `plate`, `overlay_png` or `animations` step) |
| From a finished video | **what goes out:** how many clips, how long each, a teaser or not (it keeps the frame of the source; a vertical teaser is not built); **frame:** the picture whole in the centre with fields around it, so nothing of the edit is lost and its small text gets smaller; a crop has no fields, so it has no `bands`; the colour of the fields, dark, because the headline is chrome; **speed:** the rate the person wants is for the speech, so ask how much the source was already sped up: `speed` = wanted ÷ already (1.2 on a source at 1.07 is 1.12); **pauses:** only real silence goes (`gap`): the speech of an edited video is already tight, the picture keeps moving, and a gap between words on local whisper can be the end of a word, so `word_gap` stays large and is only there for the margins of a clip; **headline:** in whose words, how long, an example; **call to action:** the exact text and the word the viewer writes; **who is in it:** names of third parties, what may be shown. Not asked here, the edit has already decided them: layout and face, captions and glossary, chapter plates, cards, graphics, secrets (ask only whether the long video was checked). **sound:** on the path `bands` it comes from the finished file, so ask whether a bed lies under the speech and say it stays. Clips are not taken from the rubric: `templates/format-skill/method/clips.md` | `params.clips`, `params.max_seconds` (the whole finished clip, after `speed`, with the tail of the call where there is one), `steps` (`teaser`), `params.teaser_seconds`, `params.teaser_name`, `params.layout`, `params.speed`, `params.word_gap`, `params.gap`, `params.cta`, `steps` (`bands`) |
| A re-edit under 9:16 (the path `reedit`) | **the source:** is there a working folder of the long video, with scenes, assets and clean speech; only a finished file with a bed under the speech → say before any editing that the hum cannot be taken out, and go on only on their word; **speed:** wanted ÷ already, as above; **how many clips, how long each:** the whole finished clip, speech ÷ speed plus the tail of the call; **safe zones:** where it will be posted: text keeps clear of what Reels, Shorts and TikTok cover (`reels`, the one zone built so far), and elsewhere is said to be unchecked; **call to action:** the exact text in parts: a lead line, the words before and after, the word the viewer writes; it comes 2 s before the end of the speech and stands 4 s after it; or «без призыва», and then the clip ends with the speech; **covers:** needed or not, how many; **design:** the one the long video was made in, so the graphics stay the same. A bed under the speech by request is not built on this path: «пока нет», and a taste line | `params.source_speed`, `params.speed`, `params.max_seconds`, `params.clips`, `params.safe`, `params.cta`, `params.cta_parts`, `params.cta_lead`, `params.cta_tail`, `params.covers` |
| Speech recognition | local whisper (free, private), ElevenLabs Scribe (precise, paid), any OpenAI-compatible address and model (OpenRouter too), their own command — from `runtime.asr.providers_help()`; where the key is: they put it into their environment or `.env`, or it already lies in another `.env` and they give its path | `asr.provider`, `asr.model`, `asr.base_url`, `asr.api_key_env`, `asr.key_file` |
| Where results go | the issue folder base; the language of the format | `output_dir`, `language` |

The recogniser question names the **variable** the key lives in (`ELEVENLABS_API_KEY`,
`OPENROUTER_API_KEY`, …) and offers two ways, the person picks and does it themselves: put the value
into their environment or `.env`, or — when the key already lies in another `.env` (say, of another
tool) — give that file's path for `asr.key_file` (`~` is fine). The key is then read from that file at
each run and copied nowhere: not into the profile, the format skill, the report or the log. Never ask
for the value, never open or print the file.

The catalog describes known repeatable steps; an absent row or old `not_built` marker does not settle
whether the person's requested effect is possible. Inspect the footage and the effect, find a real local
tool, install its checked requirements in an isolated environment, and prove a trial output. If it
becomes a repeatable format step, extend the catalog, runtime and tests. Name a blocker only when
the viable route has actually failed. The profile still holds only the steps chosen for this format.

## Steps

`steps` holds only what the answers chose, in the order the video goes through them; the names are the
step ids of `catalog/steps.json`. A step the person turned down is removed, not left switched off.

Next: `ae.py stage design`, read `phases/design.md`. A format with no visual layer (no plates,
captions or graphics) → `ae.py stage design skip --note "без оформления"`.
