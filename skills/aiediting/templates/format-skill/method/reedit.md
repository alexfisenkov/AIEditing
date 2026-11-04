## Re-edit

`run.py edit` makes no video in this format. It agrees the clips with the question `clips` (pick them by «Clips from a finished
video») and writes into the issue folder `отрывки.json`, the stretches of each clip and the call to action, and
`слова-таймкоды.txt`, both in seconds of the whole source. The clips are made on top of them: **read
`<skillDir>/design/overlay-kit/vertical.md` and follow its order of work and its rules of the frame**, with
`python "<skillDir>/design/overlay-kit/tools/overlay.py"` as its command. The clips in `отрывки.json` are already chosen, so
its first step only checks them against the sentence and the length. On this path `params.max_seconds` is a recommendation, not
a limit: a clip may run longer when its thought needs it, and the report says so; never cut a thought to fit.

`<skillDir>/design/sources.md`, when it exists, says where this person's materials live: read it now, before the question below.
A folder older than this kit stops `vertical-check` on the types: give it `tint` in `kit/tokens.ts` and `data/design.json` by the
template, and nothing else there.

**The first question about this video, before `run.py edit`: does the working folder of the long video exist?** Its scenes,
its assets and its clean speech are what a good re-edit is made of. Ask, then it is one of four:

- **The folder exists.** Work in it (`vertical-init` works in a long video's folder, and no new `prepare` is needed), or take its
  scenes into a new folder: `prepare` from its `public/clips/source.mp4`, not from the finished file, so the seconds stay; `--speech`
  with its clean speech; then carry over `src/data/time-map.json`, `src/data/face.json`, the scenes you need with what they import
  from `src/`, and the pictures they use from `public/`. A folder with no `raw/words.txt`:
  `vertical-words "<working folder>" --words "<issue folder>/слова-таймкоды.txt"`. If its time was changed by markers, `vertical-init` warns, and `vertical-words` gives each word
  in file, scene and clip seconds: place scenes by those, not by hand.
- **No folder, a clean speech track.** `prepare --speech "<track>"`. It must be in the seconds of this file: the kit refuses a
  length off by more than 0.35 s, and you check that the words fall in the same places.
- **No folder, only a finished file with nothing under the speech,** as far as they or its project can say. Its own sound is used.
- **No folder, only a finished file with a bed under the speech.** Tell the person now, before any editing, that the hum of the bed
  cannot be taken out and that a clean track would avoid it. Go on only on their word: `vertical-final --hum-accepted "<their reason>"`,
  and name it in your message and with `run.py note`. Without questions nobody can give that word: this skill stops here and says so
  in your list.

Without the folder the scenes of the long video are not there to reuse: you write them anew in the kit from the words and from frames
of the file itself (`overlay.py frames --crop`), so the graphics are the file's own pictures, placed for the tall frame, and
not its original animation. Before the layouts look at the whole file: `overlay.py frames "<the source>" "<working folder>" --overview`.
Where the speaker is not in the frame or is too small to carry a layout, the layout there is `hidden`: nothing promises them that
the speaker moves around in a video that does not show one.

**When `vertical-final` fails on the hum, it is not always a bed.** It decides nothing by itself. With only a finished file, it is a
bed: the last case above. With a clean track, or on a clip of nonstop talk, it is not: such a clip has few quiet places and can trip the
sign. Give the person `.c<N>.failed.mp4` with the question, and on their word after listening, `--hum-accepted "<their reason>"`.
Without questions that clip is not released and goes first in your list; the other clips go on.

Without questions: look for the folder yourself, in what the person named, in `design/sources.md`, beside the source and in
`~/.local/share/overlay-kit/`, and take a clean track when one is there.

A bed under the speech by request is not built on this path. Say «пока нет» and write the wish down with `run.py note`.

These values:

- `prepare "<the source>" "<working folder>" --words "<issue folder>/слова-таймкоды.txt" --design "<skillDir>/design"`, plus
  `--speech` as above and `--logo` with `<skillDir>/design/logo.svg` or `logo.png` when it exists. A design system they named for this
  video replaces the `--design` folder for this run.
- The working folder: `~/.local/share/overlay-kit/<skill name>/<issue folder name>`, an absolute path; or the long video's own folder.
- `vertical-init "<working folder>" --spans "<issue folder>/отрывки.json"`. In a folder that already has its `spans.json`, add
  `--renew`: it takes the new file and renews the kit's own files, and never touches the scenes `c<N>.tsx`.
- After every change: `vertical-check "<working folder>" [c1 c2 …]`. It audits every frame for what overlaps, sits too close,
  leaves the screen empty or leaves the safe zone of `params.safe`. It does not see text inside real screens or judge whether it
  can be read: that is for your eyes.
- `vertical-final "<working folder>" "<issue folder>" [c1 c2 …] --lufs <params.lufs of profile.json, or -14>`, then
  `vertical-sheets "<issue folder>"`.

**What stays and what is new.** The speaker and the graphics stay as they were in the long video: the same person, where the file
shows one, the same scenes, rebuilt for the tall frame, in the same design. Nothing is generated and nothing is redrawn into something else. Text on
screen comes only from what the person says or wrote: the clip's own words, the call to action of `params.cta_parts`. It
comes `params.cta_lead` seconds before the end of the speech and stands `params.cta_tail` seconds after it, so it can be read.
`params.cta_parts: null` means they said no call: the clip ends with the speech.

**Checking, before anything is shown.** Two rounds of review over each clip, by the sheets `vertical-check` makes, with the true
second on every frame; each round by someone who has not seen your verdict, where your environment has parallel agents. Fix what
they find and check again. Then, after `vertical-final`, open the finished file itself and look at frames at full size, at the seams
of the scenes and at the tail: a plate sitting edge to edge on a card shows only there.

**Words at the seams of `drop`: this path has no `verify_words`, so you check them.** Hear each finished clip again,
`python "<skillDir>/tools/run.py" hear "<clip>"`, and read the sentence across every seam: nothing lost, nothing cut in half. A
recogniser is not an ear, so give the person the seconds of each seam when you show the clip.

A clip that has not been through all this is not shown. Say how far this checking went in your message.

**Covers, when `params.covers` is above 0,** are a step of this format and not a favour: that many tall covers per the section
«Covers» of `vertical.md`, each a real frame of the speaker with a short line in the person's own words, in the design, with its
crop bands kept. No command makes them. They go into `<issue folder>/обложки/`. Generating a picture for a cover is closed, as
everywhere here.

Another `run.py edit` into the same issue folder rewrites `отрывки.json`, and it numbers the clips anew: check that the scenes
still belong to their numbers before `vertical-init --renew`. The run is not finished until every clip of `отрывки.json` is in the
issue folder and has passed the checks: say so if you stop earlier. `vertical-final` ends with code 1 when a check of the file
fails, and keeps the failed file under another name: that is a defect to fix, not a result to hand over.

The working folder lies outside the issue folder because rendering from a cloud-synced folder hangs: it is the one place this
step writes elsewhere. Working in the long video's own folder is the same exception, and `vertical-init` adds there only `src/vertical/`
and two lines to `src/kit`: change nothing else of that video. The Node packages and the renderer's browser come on the first run;
those downloads and the pages the person named are the only network this step uses, besides the recogniser.

