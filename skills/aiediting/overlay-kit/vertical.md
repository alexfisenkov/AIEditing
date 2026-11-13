# Vertical clips: a horizontal video recut into 9:16 clips with graphics

A finished 16:9 video (or a recording) becomes several short 1080x1920 clips for Reels, Shorts and TikTok. This is a **recut**, not a crop: the speaker travels between layouts (full frame, a band above or below the text, a circle) and the same graphics language as in the long video fills the rest. Each clip is a few spans of the source speech, sped up, with a call to action at the end.

The kit part: `template/src/vertical/` (put in by `vertical-init`), the commands below, a sample scene `examples/vertical/c1.tsx`. Three kinds of seconds meet here. **File seconds** are those of `public/clips/source.mp4` and `raw/words.txt`; `spans.json` holds them. **Scene seconds** are what `keys` and `at`/`out` in `c<N>.tsx` use. **Clip seconds** are those of the finished clip. In a folder without a time map (an empty `src/data/time-map.json`, which is every folder not edited by markers) file and scene seconds are the same. See "A folder with a time map". The commands never speak to the person and publish nothing.

## Commands

All take the working folder `<W>` made by `overlay.py prepare` (the long video's own folder works). Exit codes: 0 done, 1 a check found a problem, 2 an error with a reason. Messages are in Russian.

| Command | Does |
|---|---|
| `prepare ... --speech clean.wav` | the speech of the video without anything underneath becomes `public/clips/speech.wav` (same length as the video, within 0.35 s). Without it the sound of the video is used |
| `vertical-init <W> [--spans file.json] [--renew]` | puts `src/vertical/` in. Without `--renew` nothing existing is overwritten. `--renew` refreshes only the files of the set (never `c<N>.tsx`, never `spans.json`); `--spans` replaces your `spans.json` only together with `--renew`. Adds `setFrameMap` to `src/kit/time.ts` and `MARK` to `src/kit/tokens.ts` of a folder made before this set, and `src/kit/faceTrack.ts` (the face track read by pieces) and `src/kit/speakerBox.ts` (the window report of the face check) to a folder made before them. A set put in by an earlier kit keeps its own `VPresenter.tsx`, which smooths the face track through every cut: the command says so, and `--renew` replaces it. With no scenes yet it puts the sample `c1.tsx` |
| `vertical-check <W> [c1 c2 ...] [--step 0.1667]` | types, a bundle, the audit of every frame in the browser, contact sheets, `out/vertical/<clip>/findings.txt`. Then the face check: 0.2 s and 1 s after every joint of two spans and every change of the picture inside a span, the face is whole inside the speaker's band or circle (`out/vertical/<clip>/face-check/`); a frame where it is not is a finding «НЕТ ЛИЦА В РАМКЕ», «ЛИЦО СРЕЗАНО КРАЕМ РАМКИ» or «РАМКА СПИКЕРА НЕ СООБЩЕНА», written into `findings.txt` too; a clip it cannot check (no OpenCV or model, no face track, a track or a `VPresenter.tsx` of the earlier kind) is a finding with the reason. A false finding (a speaker turned away): look at the frame, then `vertical-final ... --face-accepted "reason"`. The speaker's circle of the call to action is a second layer and is not checked: look at it on the sheets. Exit 1 on any finding. It runs when there is a scene for every clip of `spans.json` (a missing scene stops it with the names). Each run bundles into a folder of its own, so two checks at once do not disturb each other |
| `vertical-final <W> <dest> [c1 ...] [--lufs -14] [--hum-accepted "reason"] [--face-accepted "reason"]` | the face check of `vertical-check` first: a finding or an unchecked clip stops it unless `--face-accepted`; then renders the picture, mixes the sound, measures the finished file against the given `--lufs`. Exit 1 if a check fails; the file then stays as `.<clip>.failed.mp4` and no earlier good file is replaced; a later success removes that leftover. The mix aims at a true peak of -1.5 dBFS, the check allows up to -1 |
| `vertical-words <W> [c1 ...] [--words file]` | the words of each clip with three seconds per word: of the clip, of the file and of the scenes. Needs only the set and `spans.json`, not the scenes. Words come from `raw/words.txt` or from `--words` (file seconds, e.g. the timecoded words of the release folder; a long-video folder may have no `raw/`). With a time map it stops if the last word lies after the end of `source.mp4`: those are old-seconds words |
| `vertical-sheets <dest> [--step 2]` | sheets made from the finished files themselves (the whole clip and its tail) with a report line per file |

### `src/vertical/spans.json`

```json
{ "rate": 1.2, "cta_lead": 2.0, "cta_tail": 4.0,
  "cta": { "lead": "", "before": "", "word": "", "after": "" },
  "safe": "reels",
  "spans": { "c1": [[0.0, 12.0]] },
  "names": { "c1": "file name of the clip" } }
```

- `spans`: file seconds, a list of `[from, to]` per clip. Cutting a phrase out is two spans.
- `rate`: speed of the speech **against the file in `public/clips/source.mp4`**. If that file is already sped up (say by 1.07) and the speech should come out at 1.2, the rate is 1.2 / 1.07 = 1.12.
- **Length of a finished clip** = speech of its spans / `rate` + `cta_tail` (the tail after the speech; the call overlaps the last `cta_lead` seconds of the speech). This is the one definition; the check compares the file with it. The call appears `cta_lead` seconds before the speech ends and stands `cta_lead + cta_tail` seconds.
- `cta`: the words of the call (an empty string hides its line). Nothing of it is in code. **The call is optional and a clip without one is the person's choice, not a default to drop**: `cta` null, `{}` or blank words, with `cta_lead` and `cta_tail` 0 or absent, gives no curtain, no card, no click, no check of the call's time, and the clip is as long as its speech.
- `source_seconds` (optional): the length of the file the spans were written for; the tool that cuts the clips writes it. `vertical-init`, `vertical-check` and `vertical-final` stop when it differs from `public/clips/source.mp4` by more than 0.35 s.
- File names: `names` must differ after NFC normalisation and case folding, as APFS and NTFS treat such names as one file; a clip without a name is named by its id.
- `safe`: the zone preset (`reels`: text x 70-940, y 270-1240 of 1080x1920), defined in `safe.ts`.
- `small_ok` (optional): texts allowed to be smaller than 34 px.

## Order of work

1. **Choose the spans by meaning.** Read the whole speech. A clip begins with a complete thought, not with a question or a connecting word, and ends on one. The length of a clip is the one definition under `spans.json`. If a phrase has to go, cut it as two spans. A pause is cut only if it is real silence.
2. **Speaker layouts per clip** (`keys` in `c<N>.tsx`, `[second, layout]`): `full`, `close` (no text at all: the face fills the frame down to y~1130), `top` (speaker y 0-880, text 905-1240), `low` (speaker y 1020-1920, text 270-995), circles `ringLow`, `ringTL`, `ringTR`, `ringBL`, `ringBR`. A change sits at the start of a phrase. Alternate: circle with a big graphic, then the speaker with a line under or above him.
3. **Scenes.** One file per clip, `export const c<N> = { keys, scenes: [{ from, to, C }] }`; see `examples/vertical/c1.tsx`. Colours and fonts only from the tokens.
4. **`vertical-check`**, fix until it finds nothing, then look at every sheet with your eyes (`out/vertical/<clip>/sheets/`). The script does not see text inside real screens or judge legibility.
5. **Two rounds of independent review of every clip, from its sheets.** The reviewers get the sheets (the yellow label is the real second of the clip) and the rules below, not your verdict. The first round of one project found blockers in all five clips, the second only minor points.
6. **`vertical-final`**, then `vertical-sheets` and **look at the finished file at full size**, at the seams of the scenes and at the tail. Plates sitting flush against a card passed both the script and two rounds of reviewers; the full-size frame showed them.
7. Keep `<W>` until the person accepts, as for the long video.

## Rules of the frame

- **Nothing on the face.** In `full` and `close` there is no text. A caption beside the speaker lives only in `top` and `low`.
- **Nothing on the speaker's video or circle.** Keep 24 px between text or plates and the band or circle. Circle rectangles: `ringLow` x 370-710 y 1275-1615; `ringTL` x 70-370 y 270-570; `ringTR` x 640-940 y 270-570; `ringBL` x 70-370 y 940-1240; `ringBR` x 640-940 y 940-1240.
- **Nothing lies on anything.** Plate on plate, plate on text, text on text, text or plate on a picture: none. Keep 24 px between neighbours; the check calls anything under 12 px «ВПЛОТНУЮ». Do not judge sizes by eye: a pill is about 1.84 times its font size high, a headline line about 1.1, long text wraps. A caption to a screenshot goes beside it. Leave room for the rotation of tilted pictures.
- **Scenes do not overlap and leave no hole.** A leaving scene fades in 0.42 s and is gone before the next arrives: its `at` is at least the old `out` plus 0.3 s. An empty stage longer than 0.7 s is a hole: the first element of a scene arrives with the change of layout. A headline and the first point come together, the rest by the words.
- **Everything is read.** A caption stays sharp for at least 1.2 s (0.1 s per character for long ones); a counter finishes and stands 0.7 s. Times `at` and `out` are scene seconds, but the clip plays faster by `rate`: count with that. Not enough time: drop the caption. Less text is better.
- **Screens.** Crop so that text is not cut in half by the window edge, the highlight frame is visible and on what is being said, the text reads on a phone. Nothing personal or internal in view. If it cannot be read, show it briefly with a big caption beside it. One highlight frame only: `MARK` from `./VKit`, which comes from `overlay.mark` of the design's tokens (a thin ring; a neutral white one without the token). No other frames.
- **The last caption stands before the call to action comes.** The call comes `cta_lead` seconds before the end of the speech: whatever must be read is on screen at least 1.5 s earlier than that. What the curtain covers does not matter.
- **Fill.** A screen empty for three quarters for long is a fault: bigger elements, nearer the middle of the free zone, a bigger speaker.
- **Text only in the safe zone** and not under 34 px. The mark sits in the top band.

## The call to action

An opaque curtain over the whole scene, a card in the zone with the words from `cta`. The speaker's circle (`ringLow`) stays above the curtain while he speaks and fades out as the speech ends; in the silence of the tail only the card stands. There is never an empty black circle. `vertical-final` measures from the finished file how long the card stands: at least `cta_lead + cta_tail` less 0.4 s for its arrival.

## Sound

Only the clean speech (`public/clips/speech.wav`) with the same spans and the same speed (`atempo`), a soft click when the call appears, a 0.2 s fade at the end of the speech, silence in the tail, -14 LUFS, peak -1 dBFS. **No pad underneath: this path has none yet.**

Why: a clip taken over a finished video carried the music pad of that video. A viewer said there was a hum in the background. The measure agreed: the quiet places were 11.8 dB below the speech, in the clean speech they are 19.9 dB below, and the peaks of the pad (110, 160, 170 Hz) were in the spectrum of the quiet places. `vertical-final` therefore measures the **hum**: the quiet places less than 16 dB below the speech, or a lasting tone between 60 and 250 Hz in them, fails the file and names which. A clip of nonstop talk has few quiet places and may trip the first sign: listen to it, and say so in the report.

**A hum finding is not the agent's to waive: the agent does not hear.** If it fired on a clean track or on nonstop speech, that is not a pad. Give the person the `.c<N>.failed.mp4` with the question, and set the flag only on their word. Without that answer the clip is not released and goes first in the list of what is open. Two cases in which the person may let the finding through: (1) a clip of nonstop speech where the sign fired falsely, after they listened; (2) a finished file with a pad mixed in by hand with their agreement.

`vertical-final <W> <dest> c3 --hum-accepted "<reason in words>"`: **name the clips** the flag is for; without a list it applies to every clip of the run. The finding becomes a warning, the file is released, and the run prints the clips where a finding was really let through, with the reason. Put that in your own report. Without the flag the finding stops the file.

Other checks of `vertical-final`: 1080x1920 at 30 fps; picture and sound tracks of equal length, equal to the length the data gives; the target `--lufs` (-14 by default) within 1, true peak not above -1 (the mix aims at -1.5); the tail after the speech silent; the call stands its time (measured on the band above the card; skipped for a clip without a call).

## Covers

A vertical cover is a 1080x1920 picture; Reels and the profile grid crop it. Two bands are safe: **3:4** keeps y 240-1680, **1:1** keeps y 420-1500 (`COVER_BANDS` in `safe.ts`). Everything that must be read lies inside 3:4 and the key line inside 1:1; nothing on the head. Side margins 70 px.

No command makes them: a tool that does not carry the materials of one video came out of the attempt too thin. The method that worked: build each cover as one HTML page of 1080x1920 from the design's own fonts and tokens; put a frame of the speaker from the source (a frame where the eyes are open and the face is turned to the camera) with the eyes at a chosen point and a gradient into the background above the head; set the title in the design's `CHROME` token (another design is not obliged to be chrome), one idea per line, shrunk by a script until the line fits 940 px; photograph the page with headless Chrome at scale 1, and write each element's box (`getBoundingClientRect`) into a JSON next to the picture. Then check the boxes against the bands above and the head rectangle (the face box enlarged to the headphones and hair), and open every picture. Offer the person several variants per clip (the speaker below and a headline above; the speaker large above and a price or number as the accent; a speaker at the side with one big picture) and let them choose.

## Moving the work into a new folder

Carry `src/data/time-map.json` and `src/data/face.json` together with the scenes: the face track is read in scene seconds. The cuts of the picture travel inside `face.json` (the fifth number of a point), and the edges of a clip's spans are cuts by themselves: where two spans meet, the speaker's frame is on the face of the second one from its first frame (`spanTime.ts` counts the second of a frame from the very frame at which the video layer starts the span). `vertical-check` checks the face right after every joint of two spans by itself; its frames are in `out/vertical/<clip>/face-check/`. A `face.json` with four numbers a point was smoothed through the scene changes: `overlay.py face <W>` says what the folder holds, and "What can go wrong" in `README.md` how to mend it. The source is `public/clips/source.mp4` of the long video's folder. `vertical-init` warns when the map has rows while the face track is as long as the file: the track then belongs to another file.

## A folder with a time map

If `src/data/time-map.json` has rows, the long video was edited by markers: its scenes live in the **old** seconds, `useT = toOld(...)`. A clip's `spans` and `raw/words.txt` stay in file seconds. So: scene second = `toOld(file second)`, file second = `toNew(scene second)` (both in `src/kit/time.ts`). A live case: the shift reached 45 s, a layout at 1462.9 in a scene file against `spans` starting at 1424.02. `vertical-init` prints this warning for such a folder. Write `keys` and `at`/`out` in scene seconds and the span borders in file seconds; `vertical-words` prints the words of a clip in all three, so nothing is converted by hand. A scene placed by file seconds in such a folder lands on the wrong word.

## A folder older than the set

A folder made before this set (no `tint` in `src/kit/tokens.ts`, no `src/data/design.json`) stops at the type check. Add those two by the sample of `template/src/kit/tokens.ts` and `template/src/data/design.json`; change nothing else there.
