# Brief for the scene executor: overlays on top of a whole recording

(Orchestrator: fill every `<…>`, the quotes and the "Segments" section, save as `<W>/scenes-brief.md`, give it to every executor unchanged except for the segment.)

The person's words: "<their request for this video, word for word>". The speech is final: its timing is not touched here; only graphics on top and the speaker's layouts.

## How it works

- Root: `<W>`. Before you start, read `src/kit/` in full and the sample in `<kit>/examples/` (the device and the level of quality).
- Time is everywhere **seconds of the video in `public/clips/source.mp4`**. `useT()` gives the current second. Words with their seconds: `raw/words.txt`. Bind every appearance to the word that causes it: check it in that file, the numbers in this brief are approximate.
- A scene is an object `{from, to, C}` in `scenes` of your `src/scenes/seg-X.tsx`. Position in the 1920x1080 frame: `<At x y w h>`; an appearance: `<Appear at out>`.
- Layouts live in `src/data/layouts-X.ts`, exported as `LAYOUTS_X`: `[second, "full"|"close"|"right"|"left"|"half"|"pip"|"pipL"|"pipTop"]`. The change takes 0.85 s. The graphite stage appears by itself for everything except `full`/`close`.
- Sound is the `cues` array: `[second, "mouse-click"]`, the language of sounds is in `src/kit/Sound.tsx`. `whoosh-soft` on a layout change; no sound on leaving or zooming. `src/data/sfx.json` lists the files that exist; a missing one falls back or is skipped, never fails.
- Your own segment is a pair `seg-X.tsx` + `layouts-X.ts`. A new segment letter is picked up by the next `overlay.py frame` (or `overlay.py index "<W>"`).

Toolbox: `Appear, At` · `Chrome, H2, Lead, Eyebrow, Mono` · `Glass, Pill, Token, Brand, TextMark` · `Screen, Cursor, Focus` · `Link, Count` · `WorkFrame` · `Logo, LogoMark`. `Brand name=` takes keys of `src/data/brands.json` (empty unless logos were added; a missing key shows two letters, use `TextMark` instead). Do not change the files in `src/kit/`: if you need a shared device, name it in your report.

Screens: `public/screens/<name>-dark.png` and `-light.png`, 1600 css px wide: <list with heights>. Look at the PNG to set `scroll`, `zoom`, `left`, `Focus` from the real coordinates. Content usually starts near x=360; to enlarge a column use `zoom` 1.3-1.7 and `left` 330-450.

Frames of real work: `public/frames/<name>.jpg`, `<WorkFrame name= w h crop=[x,y,w,h] />`: <list with descriptions>. Add no other pictures, run no generation.

## Quality rules

1. **The design system**: only the tokens of `src/kit/tokens.ts`, only the design's fonts, colour only `C.ok` for "done". No emoji, no stock icons, no coloured plates. Icons are thin SVG lines, stroke 1.6-2, silver.
2. **Density and "wow"**: a new event every 6-10 s, each one readable, not a mess. Alternate `full`/`close` with corner cards, then `right`/`left` with graphics, then `pip` with a full-screen diagram or a real screen. The speaker fills the frame at least a quarter of the segment. A layout changes at the start of a phrase. A scene never empties before the layout changes, and never starts late: on a layout other than `full`/`close` the stage holds something by the time the change ends, 0.85 s after its second. When the word that causes the graphic comes later than that, the layout change moves to the phrase of that word; a lasting element can also stand from the start and take its details on the word. The empty stage after a layout change is the commonest defect of a first draft.
   **Scale**: on a layout with a stage the graphic is the point of the frame. It takes most of the free width and most of the free height, and it stands in the middle of the free stage, not pressed to its top. A headline there is from 60 px, a block's text from 32 px; the 22 and 26 px of rule 5 are for corner cards. A small card on a big empty stage is the second commonest defect.
3. **Do not cover the face**: in `full` the face is about x=<...>, y=<...> (of the frame; read `src/data/face.json`). In `close` only the bottom strip is free.
4. **Zones**: the corner x<300, y<90 is the mark; below y=1000 is the chapter strip. Content lives in 60...1860 x 96...990.
5. **Text**: in the speaker's language, short, headline up to ~26 characters, a bullet up to ~36. A caption from 22 px, a pill from 26 px. In the first person, in their words.
6. **Facts**: only what they say in this segment or what a real screen shows. No numbers of your own. A strange word from the transcript does not go on screen. A condition stays: «в настроенном проекте», «могу», «если подключить» does not become a ready fact on screen. A short headline keeps the condition or stays out.
7. **Performance**: `filter: blur` only on short appearances and never on the whole frame.
8. Scenes of neighbouring segments do not overlap; return the last layout to `full` by the end of your segment.

## Checking your work

Work and check only in `<W>`, with absolute paths. Types: `npx --prefix "<W>" tsc -p "<W>" --noEmit`. Frames: `python "<kit>/tools/overlay.py" frame "<W>" 61 72.5` writes `<W>/out/frames/<second>.jpg`: look at two frames per scene with the Read tool (the appearance and the filled state), and one frame 1 s after every layout change: the stage must already hold the graphic, at its size. Fix overlaps, clipped text, a covered face and empty stretches at once; the draft's `empties` comes too late to be the first to find them. Someone else's unfinished file may break the build: wait a minute and repeat.

## Segments

### A. <from>-<to> s (`seg-a.tsx`, `layouts-a.ts`)

1. **<from>-<to> "<their words>"**: the layout; what appears and on which word.

## What to return

The files, the scenes with their seconds, the paths of the frames you looked at, what you did differently and why, what you did not check. Forbidden: changing `src/kit/` and other people's `seg-*`, running a full render, publishing, sending, visiting the live site, running paid generations. If the task leads to a breakage or goes out of bounds, do nothing and return an objection with the reasoning. If you see a better way inside the bounds, take it and name what you did differently and why, as a separate point.
