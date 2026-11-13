# overlay-kit: graphics on top of a whole recording

A speaker talks to the camera and the recording stays **whole: no cuts, the speech and its timing are untouched**. The edit is only overlays: cards, service logos, live diagrams, real screens of the product, frames of real work, and a speaker's frame that glides between layouts. The goal is "wow" at the maximum density the design system allows. The kit works on any recording where someone talks to the camera, and on an already cut video: time is always **seconds of the video you pass in**, never of the original recording.

The kit is a Remotion project (`template/`), a command line (`tools/overlay.py`), helpers for capturing real screens (`tools/capture-*`), a brief for scene executors (`brief-template.md`) and a sample (`examples/`). A format skill calls it; it does not talk to the person and publishes nothing.

## Quick start

```bash
python tools/overlay.py prepare video.mp4 /abs/work/dir --words words.txt --design <folder with tokens.json> [--logo logo.svg] [--sfx DIR] [--music pad.wav]
python tools/overlay.py example /abs/work/dir        # optional: the neutral sample as segment A
python tools/overlay.py frame /abs/work/dir 9 16 21  # stills: out/frames/<second>.jpg
python tools/overlay.py draft /abs/work/dir          # out/draft.mp4, half size
python tools/overlay.py final /abs/work/dir /abs/release/dir "name.mp4"   # 1080p, -14 LUFS, sync check
```

The command wrapper uses Python 3.9+ on macOS and Windows. OpenCV is used for the face track and numpy for the sync check and the empty-stretch finder; AIEditing `setup` prepares them in a private Python environment, selecting a compatible Python 3.12–3.14 if the host is older. Messages for the person are in Russian; every error ends with code 2 and a reason.

| Command | Does |
|---|---|
| `prepare <video> <W> --words F --design D [--logo F] [--sfx DIR] [--music F] [--speech WAV] [--no-install]` | checks, then unpacks the template, makes `public/clips/source.mp4` (H.264, no sound) and `speech.wav`, copies the words to `raw/words.txt`, builds the face track by pieces between scene changes and cuts, writes the design data, lists the sounds, sets the duration, and reuses the shared Remotion packages when the lockfile and browser match. If reuse is unavailable, installs from the pinned lockfile into this working folder. Repeat-safe: filled scenes are never overwritten. `--speech`: a clean speech of the same length replaces the sound of the video as `speech.wav` |
| `frame <W> <sec...>` | stills of any seconds |
| `draft <W>` | type check, then a half-size render, then the face check of `face --check`; exit 1 on its findings and when it could not check (the draft is written either way) |
| `sheets <video> <dir> [--step 4]` | contact sheets, 30 frames each; the first frame is half a step in, then one every step |
| `empties <video> [--min 1]` | stretches where the stage is empty longer than the threshold |
| `texts <W> <file>` | all text the scenes put on screen, for the critics |
| `frames <video> <W> [--overview] [--label L] [--crop x,y,w,h] <sec...>` | an overview sheet and chosen seconds of any video, saved as `WorkFrame` pictures named `<label>-<second>`. `--crop` is in shares of the frame (0.1,0.2,0.5,0.5) |
| `final <W> <release dir> <name> [--lufs -14] [--reuse-render] [--face-accepted "reason"]` | full render in H.264 yuv420p, limited range, BT.709 with all its tags, so the file goes to delivery as it is; AAC delay measured and removed, loudness set, atomic write, `sync`; exit 1 when the sound or the colour tags are off. Before the render the face check of `face --check`: a finding, or a render it could not check, stops it unless `--face-accepted "reason"` (the person looked at the frames and the detector was wrong, or looked at them because nothing could check them). `--reuse-render` is refused when the render is older than the scenes, layouts, kit or face track |
| `sync <base> <final>` | the speech of the result against the source; exit 1 outside 10 ms |
| `index <W>` | rebuilds the scene and layout lists (frame/draft/final do it themselves) |
| `face <W> [--rebuild [--video F]] [--frames] [--check]` | the face track of the folder: every cut it knows (scene seconds and file seconds), a track or a presenter of the earlier kind named. `--rebuild` builds the track anew and keeps the earlier one in `raw/face-before-rebuild.json`; a rebuild that fails changes nothing. `--frames` renders a still 0.2 s after every cut into `out/cuts/`. `--check` renders the frames 0.2 s and 1 s after every such cut from the composition itself, takes the speaker's window as the presenter reports it, and runs the face detector inside it: a frame where the window shows no face, cuts the face or was not reported is a finding, exit 1; the line names the second and the frame's file in `out/face-check/Full/`. Whatever keeps it from judging (no OpenCV or model, no face track, a track or a presenter of the earlier kind) stops it with that reason, exit 2: unchecked is never a pass |
| `vertical-init <W> [--spans F] [--renew]` | puts the vertical set `src/vertical/` into the folder; never overwrites scenes or your data |
| `vertical-check <W> [c1 ...] [--step 0.1667]` | vertical clips: types, bundle, the audit of every frame in the browser, sheets with the real second on each frame, then the face check after every joint of two spans and every cut (into `findings.txt` too); exit 1 on findings |
| `vertical-final <W> <dest> [c1 ...] [--face-accepted "reason"]` | vertical clips: the face check of `vertical-check` first (a finding or an unchecked clip stops it unless `--face-accepted`), then render, sound from the clean speech, measuring of the finished file (format, tracks, -14 LUFS, tail, hum, the call to action); exit 1 on failure |
| `vertical-sheets <dest> [--step 2]` | sheets from the finished vertical files themselves and the tail of each |

Exit codes: 0 done, 1 a check found a problem (`sync`, `final`, `vertical-check`, `vertical-final`, `draft` and `face --check` on a face finding, `draft` also when the face could not be checked), 2 a stop with a stated reason. A stop of `final` or `vertical-final` by the face check, and `face --check` that could not check, are code 2 too: read the line «Стоп: …», it says whether it is a finding in a frame (then look at the frame, fix it or `--face-accepted`) or a missing tool.

A horizontal video recut into 9:16 clips with graphics (the `vertical-*` commands): `vertical.md`.

`prepare` refuses to start when: the frame is not 16:9; there is no sound; less than 8 GB is free (`OVERLAY_MIN_FREE_GB` changes the limit); the folder is not absolute; on macOS the folder is inside `~/Documents`, `~/Desktop` or iCloud Drive (iCloud unloads files and the render hangs at 0 % CPU); the words reach further than the video (they belong to another recording). A 4K or 50 fps 16:9 video is converted to 1920x1080 at 30 fps in the working copy.

The words file is lines `%7.2f word`, seconds from the start of the passed video. The pipeline of the format recognises the speech and hands the file over; the kit does not recognise speech itself.

## Where things come from

| What | Where | How |
|---|---|---|
| The recording | the path the person gives | never changed, never copied into the project |
| The design system | the folder the person names (it holds `tokens.json`); none named: the bundled Chrome & Graphite example | `--design`; see "Design" |
| The speaker's mark | a file the person gives | `--logo`; none given: no corner mark |
| Fonts | the design's own, or the three OFL families in `template/public/fonts` | automatic, see "Design" |
| Sounds and the pad | 111 CC0 sounds ship in `template/public/sfx`: the four old names at the top, the rest by role in subfolders, all in `catalog.json` with the moment of their peak; a cue `{ role: "whoosh", at: 12.4 }` puts that peak on the second; the person's own folder (old names at the top, role subfolders) goes before the kit's | `--sfx DIR`, `--music FILE`; no music means no pad; `overlay.py sfxcat DIR` writes a folder's catalog; `overlay.py peaks <W> out/draft.mp4` prints every sound against the nearest peak of movement and the shift in frames |
| Real screens | the product, site or page the video talks about | `tools/capture-guide.md` |
| Names, dates, titles on screen | fresh captures only | never from memory or from an earlier release |
| What was said | `raw/words.txt` | the only source of captions and timings |
| Frames of real work | the person's other videos | `overlay.py frames`; no frame found: build the scene on screens, never draw a mock-up of the work, name it as an open point |
| Service logos | `src/data/brands.json` (empty by default) | `node tools-local/add-logos.mjs "<W>" claude telegram`; no logo: `TextMark` |
| The result folder | `output_dir` of the format skill's profile + `<date>-<topic>/` | |

A design system named for this video replaces the tokens and the mark for this release only; the order of work is the same. Not named: the format's own design. A permanent change of the format goes through the AIEditing rebuild, not through this folder.

## Order of work

`<kit>` is this folder, `<W>` the working folder: an **absolute path outside iCloud**, for example `~/.local/share/overlay-kit/<date-topic>`. Keep 8 GB free. Run long commands in the background with the output in `<W>/raw/*.log`: a draft takes minutes, a final about twice that for a 10-minute recording; a normal foreground call will cut them off. `ae.py setup` prepares the shared Remotion renderer and Chrome Headless Shell. `prepare` links that checked installation when possible; a platform without symlink rights may install a working-folder copy. Set `OVERLAY_BROWSER` to an existing compatible browser to use that instead.

1. **Prepare.** `overlay.py prepare` as above. Read what it says about the face: without OpenCV, without the model (`AIEDITING_YUNET_MODEL`, else `~/.aiediting/models/face_detection_yunet_2023mar.onnx`) or without a face the speaker's frame holds the centre. It also names the seconds where the face jumps between two adjacent frames: scene changes (camera to screen and back) and hard cuts between takes. The track is smoothed inside each such piece, so the frame is on the new face from the first frame after a cut. `overlay.py face <W>` lists these seconds again at any time.
2. **Read the speech in full** (`raw/words.txt`) and mark the chapters in `src/data/layouts.ts` (`CHAPTERS`; chapter labels in the speaker's language). Look at the end of the transcript: a recogniser can lose pieces of a long recording.
3. **Real materials.** Screens: `tools/capture-guide.md`. Work frames: `overlay.py frames <video> <W> --overview`, choose the seconds, then `frames ... --label L --crop ... <sec...>`. Logos by the table above.
4. **Script and scenes.** From `brief-template.md` the orchestrator writes `<W>/scenes-brief.md`: for each segment of 130-180 seconds, a list of scenes with seconds and the words that trigger them. Parallel executors (a general-purpose agent each, a mid-tier model is enough) write the scenes, each its own `seg-X.tsx` and `layouts-X.ts` under the **same brief**. A recording of any length gets as many segments as it needs: add `seg-e.tsx` + `layouts-e.ts` and the lists rebuild themselves. The orchestrator looks at the "wow" scenes and the first reference scene personally. The model **writes the scenes**; it does not generate pictures or video.
5. **Draft and acceptance.**
   - `overlay.py draft <W>` then `overlay.py sheets <W>/out/draft.mp4 <W>/out/sheets`: look at every sheet (30 frames, a step of 4 s).
   - `overlay.py empties <W>/out/draft.mp4`: where a scene is empty for more than a second (tuned for a graphite stage).
   - The face check runs by itself at the end of `draft` and again before `final`: 0.2 s and 1 s after every change of the picture the speaker's face is whole inside its window. A finding names the second and the frame's file in `<W>/out/face-check/Full/`. Fix the layout or the track (`overlay.py face <W>`), never the check. When it cannot judge (no OpenCV or model, no face track, a track or a presenter of the earlier kind) it says why, and that is a failure of `draft` and a stop of `final`, not a pass. What it does not see: frames between two changes of the picture, a joint of an edit by markers where the face stays in place (there may be hundreds; the track by pieces holds them by itself), and the finished file itself: the frames come from the composition, as the render does. A scene that covers the speaker on purpose (a full-screen prompt over a cut) and a speaker turned away are findings for the eye: look at the frame, then `final --face-accepted "reason"`.
   - `overlay.py face <W> --frames`, once the layouts are written: a still 0.2 s after every cut of the track, and after every joint of an edit by markers across which the face jumps, in `<W>/out/cuts/` (the folder is emptied first). Look at each one where the speaker stands in a box or a circle: the face is whole and in the middle. A warning of this command about a track or a presenter of the earlier kind is a finding, not a note. The joints of a vertical clip's spans are not among these stills: look at them on the sheets of `vertical-check`.
6. **Critics.** Facts (captions against the speech and the real screens), language, design. Their text: `overlay.py texts <W> <W>/out/texts.md`. Check each finding before fixing it.
7. **Final.** `overlay.py final <W> <release dir> "<source name> - edit.mp4"`. The AAC delay of the render is **measured** against the speech it was built from (cross-correlation over windows) and removed in the mix; the file is written under a temporary name and moved into place. Then `sheets` into `<release dir>/sheets`, and `overlay.py sync <source> <final>`: the speech within 10 ms along the whole video and the same duration as the recording. A larger shift: re-mix with `final --reuse-render`; no new render is needed.
8. **Cleanup.** Keep `<W>` until the person accepts the video: it is the way back to the edits. After acceptance delete it.

## Rules of the frame

- Captions are in the first person: it is the speaker's own address ("I take part", not "the author takes part").
- A caption says only what was said or what a real screen shows. No numbers or promises of your own. A condition in the speech stays in the caption: «в настроенном проекте», «могу» does not become a ready fact. A recogniser makes mistakes: a strange word does not go on screen. A key, a password, an address or a phone number said aloud does not go on screen either.
- A graphic on a stage takes most of the free width and height and stands in the middle of it, with a headline from 60 px and a block's text from 32 px, and the stage is filled by the time a layout change ends. `empties` finds what was missed, but only after a draft.
- The face is never covered: take its coordinates in `full` from `src/data/face.json` and from a frame.
- Meaningful text must read on a phone: a pill from 26 px, a caption from 22 px. Anything smaller is only the decoration of a real screen or the kit's chapter label. (`Pill` enforces 26.)
- A design's rules about calm and air hold inside one scene. The pace of the whole video comes from this file.
- Only the design's tokens and fonts; colour only for `C.ok` and for real work on screens and frames.
- Real frames carry the speaker and the audience's view of the product, nothing else. Switch the product to the audience's view before capturing; cut owner-only blocks (see the capture guide); never capture other people's personal data.
- Pace: a new event every 6-10 seconds, each readable. The speaker fills the whole frame at least a quarter of the time.

Lessons from a 73-marker review of a finished video. Each one is a rule now:

- Do not fan or crowd a set of cards: spread them over the whole frame with the speaker in a circle.
- What is said is what is shown. "Presentations" needs real slides, "videos" the videos themselves, a named student their real work with their name. Look for the material in the person's chats and bases first; a card with words comes last. A link in a remark is meant to be downloaded and shown; credit someone else's video with its author's name.
- Neighbouring items show different screens, never the same frame twice in a row.
- A slide or carousel frame is shown whole from afar first and only then zoomed: a close crop reads as some other element.
- What is shown fits in the frame. If a recording cuts it off, take it from its real source.
- Find a button on the screen recording, not from memory; name and highlight it from the same frame.
- Hold a full-screen prompt for as long as the speaker reads it: its end is when they look at the camera again, not the last word.
- The camera never walks in steps. Read the face track with a spline, never the nearest point; check that the frame moves less than 1 px per frame through the whole video.
- The frame never glides through a cut. A track smoothed across a scene change drags the frame from the old face to the new one for seconds, and the face is cut all that time. Read the face only through `src/kit/faceTrack.ts`: it keeps the median, the Gaussian and the spline inside one piece of the picture. The pieces end at the cuts `prepare` found (the fifth number of a point in `face.json` is the second its piece began), at the edges of the time map's rows and at the edges of a vertical clip's spans. Never smooth the track again in a scene or a layout. After every cut the face is whole inside the speaker's window: `overlay.py face <W> --check` (and `draft`, `final`, `vertical-check` by themselves) finds a frame where it is not; `--frames` renders the stills for the eye.

## Clean speech and edits by markers

A video cut from several takes, a whole recording with only its edges trimmed, and cuts by the person's markers on them: `takes-and-markers.md`. Cuts by markers need its `pieces.json`, so a format without clean speech has them only through a refinement; it can still read picture remarks with `tools/markers.py`.

## Layouts and the language of motion

Layouts: `full`, `close`, `right`, `left`, `half`, `pip`, `pipL`, `pipTop`. A change sits at the start of a phrase, with the sound `whoosh-soft`, and takes 0.85 s. Alternate: the speaker full frame with corner cards, then the speaker at the side with big graphics, then the circle with a full-screen diagram or real screen. Things appear out of blur, a shine runs along the edge, pulses run along lines; no jumps.

Sound: the speech unchanged; the pad (only if one was passed) at 0.055; service sounds in the fixed language of `src/kit/Sound.tsx`; `riser-1s` at most twice per video. One event, one sound, for the whole video. Leaving and zooming are silent.

## Design

`prepare --design <folder>` reads `<folder>/tokens.json` and writes `src/data/design.json`, which `src/kit/tokens.ts` and the font rules in `src/Root.tsx` read. Scenes import `C`, `CHROME`, `GLASS`, `SHINE`, `FONT`, `R` and `tint(colour, alpha)` from `kit/tokens` and hard-code no colour. The kit's own toolbox follows the tokens too; only white highlights, black shadows and the neutral bar of `Screen` (a browser window, not the brand) stay as they are.

**Colours and surfaces** come from the optional block `"overlay"`; whatever it omits is derived from the ordinary `color`, `gradient`, `radius` tokens. The block, with the values of the reference look (Chrome & Graphite):

```json
"overlay": {
  "color": {
    "white": "#FFFFFF", "muted": "#C7C9CC", "faint": "#8A8D92",
    "graphite": "#171717", "graphiteSoft": "#202123", "deep": "#0E0E10", "card": "#1B1C1F",
    "silver": "#C7C9CC", "silverLight": "#ECEDEF", "paper": "#F4F5F6", "ink": "#181A1C",
    "line": "rgba(255,255,255,.14)", "ok": "#1F8A5B"
  },
  "chrome": "linear-gradient(180deg,#FFFFFF 0%,#E0E2E5 40%,#A9ACB1 62%,#EEF0F2 100%)",
  "bg": "linear-gradient(165deg,#202123 0%,#0E0E10 100%)",
  "glass": "linear-gradient(165deg,rgba(32,33,35,.92),rgba(14,14,16,.94))",
  "hair": "linear-gradient(90deg,transparent,rgba(199,201,204,.55),transparent)",
  "rim": "0 0 0 1px rgba(199,201,204,.2), inset 0 1px 0 rgba(255,255,255,.08)",
  "shadow": "0 40px 90px rgba(0,0,0,.55)",
  "shine": "linear-gradient(100deg,#9A9DA2 0%,#E0E2E5 30%,#FFFFFF 42%,#E0E2E5 54%,#9A9DA2 100%)",
  "radius": { "block": 26, "card": 22, "inner": 15, "pill": 999 },
  "mark": "0 0 0 2.5px #FFFFFF, 0 0 0 4px rgba(14,14,16,.7)"
}
```

`mark` is the one frame that highlights a place on a screenshot in vertical clips (`MARK` in `src/vertical/VKit.tsx`); omitted, a thin neutral ring is used. A brand colour for it belongs in the design's tokens, not in code.

The video is a dark stage: `muted`, `faint`, `white` are light on dark (the ordinary `muted` of a light page would be unreadable, so it is not borrowed). `ok` is the only coloured token.

**Without the block** the values are derived: `white`, `graphite`, `graphite-soft` (as `graphiteSoft`), `night` or `deep` (as `deep`), `silver`, `silver-light`, `paper`, `ink`, `ok`, `faint` are taken from `color`; `muted` = `silver`; `card` = the middle of `graphite` and `graphite-soft`; `line` is fixed; `chrome` from `gradient.chrome` (four stops at 0/40/62/100 %); `bg` and `glass` from `gradient.dark-surface`; `hair` and `rim` from `silver`; `shine` from `silver`, `silver-light` and `white`; `radius` from `radius`. A missing value stops `prepare` and names it. A design written otherwise (CSS variables, a brand book) is first put into this shape by you. The kit is built for a dark stage: a light design's own `graphite` and `deep` must still be dark enough to carry `white` text.

**Fonts** come from the ordinary `font` block (`display`, `text`, `mono`, each with `family`, optional `file`, optional `fallback`). A family the template carries as woff2 (Unbounded, Onest, JetBrains Mono) uses those files. Any other family uses its `file` (`.woff2`, `.woff`, `.ttf`, `.otf`, relative to the design folder), copied to `public/fonts/`. No file: the `fallback` role's family, else a system font and a warning. The mark and logo: `public/logos/logo.svg|png`, only if `--logo` was given.

## What can go wrong

- A screen recording in `full`: the slow "breathing" zoom crops the left edge, and the corner mark and chapter label sit over the screen. Coordinates on such a screen are not the file's own: check them on a frame.
- A speaker who is only a small circle over a screen recording: the layouts `right`, `left`, `half` enlarge that circle with the screen around it, so the face is soft and the screen shows in the corners. Stay with `full` and the `pip` layouts there, and put graphics where the screen is calm.
- A working folder made before the track by pieces: its `face.json` has four numbers a point and is smoothed through every scene change, and its `Presenter.tsx` smooths once more, so after a cut the frame lags behind the face. `overlay.py face <W>` names both, and so do `prepare` and `vertical-init`. To mend the folder: keep a copy of your `src/kit/Presenter.tsx`, copy `template/src/kit/Presenter.tsx`, `faceTrack.ts` and `speakerBox.ts` into `src/kit/` and carry your own changes over by hand (the two modules arrive by themselves with any render command when missing); for vertical clips `overlay.py vertical-init <W> --renew` (it replaces the files of the set in `src/vertical/`, never the scenes or `spans.json`: keep a copy first if you changed them); then `overlay.py face <W> --rebuild`. The earlier track stays in `raw/face-before-rebuild.json` (the next ones in `-2`, `-3`), and a rebuild that cannot find the face changes nothing. Never delete `face.json` by hand.
- The same in a folder edited by markers (`rows` in `src/data/time-map.json` is not empty): the scenes read the track in the seconds of the first accepted video, and `public/clips/source.mp4` is already another one. `overlay.py face <W> --rebuild --video <file>` takes that first video: the file `prepare` got at the first round, before any edit by markers (16:9, 30 fps). After one round of markers its working copy is `<W>/raw/rollback/clips/source.mp4`; after more rounds that copy is already a later video, so take the finished video of the first round from the release folder (at another frame rate, bring it to 30 fps first). The video now in `public/clips/` and a video too short to cover the scenes' seconds are refused, and the track being replaced is kept.
- An insert of about a second is not followed: a face that is elsewhere for one or two points of the track and then back where it was counts as a misdetection, and the frame stays in place.
- Inside one piece the frame glides on purpose (about four seconds each way), so that the camera never jerks after the head. A head that moves far and fast within one shot is followed with that delay; only a cut moves the frame at once. A cut between takes where the face stays put is not a piece of its own, and needs none.
- Two faces in the picture: the largest one is followed, and of two faces of about one size the one already followed. A face on a shared screen that is clearly larger than the speaker's circle takes the frame for as long as it is there.

- iCloud: commands "hang" on files marked `compressed,dataless` (`ls -lO`). Work only in `<W>`.
- A video in a hidden browser pane is not decoded: frames come out black. Take work frames from the source videos, not from a pane.
- A page captured right after navigation shows a loading skeleton: wait for it to disappear (the snippet does).
- The site's content security policy may forbid `fetch` to localhost but not a navigation: the capture travels in the `#fragment` of the address.
- `Focus` is white and invisible on a light screen: for light windows write a small ring of your own in the segment (a dark inner ring `0 0 0 3px <ink>` plus a white outer one), as `Focus` does for dark ones.
- A stack of 3D windows: dim windows deeper than the second, otherwise clipped ghosts show; keep windows off the speaker's circle.
- A recogniser loses pieces of long recordings: check the end of `raw/words.txt` by eye.
- A scene that refers to a screen or a frame that is not there fails the render: look at `public/screens` and `public/frames` before the draft.

## Licences

| Part | Licence |
|---|---|
| `tools/`, `template/src`, `examples/` | MIT, like the repository |
| Remotion 4.0.542 (`remotion`, `@remotion/cli`) | Remotion's own licence, **not an open-source one**: free for individuals, companies of up to three employees and non-profits, a company licence is needed beyond that; read remotion.dev/license before you use the result commercially. It is installed from the pinned lockfile, not shipped here |
| Fonts Unbounded, Onest, JetBrains Mono (`template/public/fonts`) | SIL Open Font License 1.1, texts beside the files (`OFL-*.txt`; Unbounded's is from github.com/googlefonts/unbounded) |
| Sounds (`template/public/sfx`) | CC0: the eight synthesised for this project (`pop-soft`, `riser-1s`, `tick`, `whoosh-soft` and four in the role folders) and 103 sounds published as CC0 1.0, renamed by their role. Other sounds: only from sources with a licence you have checked (CC0), then `--sfx` |
| Logos | none shipped: a brand mark is a trademark and a licence for each icon is not confirmed. `add-logos.mjs` fetches a path from the `simple-icons` package (CC0 for the project, "not necessarily for every icon", see its DISCLAIMER) on request: read the brand's guidelines before publishing |
| Music | none shipped; `--music` is yours to license |
| Playwright 1.65.0 (`capture-*`) | Apache-2.0; real Chrome through `channel: "chrome"`, no Playwright browser download |

## When the person says "no questions"

Take everything that is known and create. The design comes as the format's profile says. Decide pace and layouts yourself, keep the wording to "Rules of the frame", bind captions to the words, show the finished video and list the open points once at the end. A check that ended with code 1 is not a finished video: fix it, or put it first in that list. Ask only if something truly blocks, such as no recording or an unreadable video. A missing sign-in does not block: build those scenes on what you have, never type a password, and list it as an open point.

## Files

- `tools/overlay.py` and `tools/overlaylib/`: the command line, one module per job.
- `tools/capture-guide.md`, `capture-receiver.mjs`, `capture-snippet.js`, `capture-render.mjs`: capturing real screens. `tools/add-logos.mjs`: logos on request.
- `template/`: the Remotion project (`src/kit` is the toolbox, `src/scenes` the segments, `src/data` the data), the pinned `package-lock.json`, fonts, the sounds by role with their catalog.
- `vertical.md`: the vertical cut (clips 9:16): order of work, rules of the frame, the call to action, sound, covers. `template/src/vertical/` is its set, `examples/vertical/c1.tsx` a sample scene, `tools/vertical-frames.mjs` the frame audit.
- `brief-template.md`: the brief for scene executors.
- `examples/`: four neutral scenes (`seg-a.tsx`, `layouts-a.ts`), a demo screen and a words file that fit together. `overlay.py example <W>` installs them.
