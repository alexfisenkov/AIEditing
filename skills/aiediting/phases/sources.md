# Sources

`ae.py stage sources`. The interview's examples are made on the person's own footage, so the footage
comes first. Ask for **1–3 source videos** of this format — paths on their computer:

```
Пришлите 1–3 исходника этого формата — путь к файлу на компьютере.
Лучше разные: с лицом, с показом экрана, вертикальный, если такие бывают.
```

`ae.py ask question --note "исходники для <формат>"` before it goes out. Never copy the sources
anywhere; the workshop keeps only frames and trial pieces in `.aiediting-work/`.

## Frames and layout

For each path: `python "<skillDir>/tools/ae.py" frames "<path>" --n 6`, then
`python "<skillDir>/tools/ae.py" layout <s1>`. The frames and the layout guess appear on the dashboard.
Tell the person in one or two lines what was seen, by source:

- «лицо целиком» (face_full), «экран + лицо в окне» (screen_face_window) with where the window is,
  «раздельные дорожки» (separate_tracks), «вертикаль» (vertical), «только экран» (screen_only);
- low confidence → say «не уверен» and ask.

Two recordings of one session (camera and screen apart) → `ae.py layout <s1> --with-source <s2>`.
The person corrects → `ae.py layout <s1> --set kind=<kind> --set face=[x,y,w,h]` (values as they gave
them; JSON when it parses). Their word wins over the guess.

## A finished video

The format «нарезка» starts from one video that is already edited, with its graphics in the picture. Ask for that one file
and do not ask for others. Frames are for you and the person; the layout guess is not: over finished graphics it sees a
screen and a face and would crop them, so `ae.py layout` is not run and the frame is whatever `params.layout` says. Ask,
in one message: where it comes from and whether it is finished; where its project lies, with its scenes, assets and clean
speech, because the design it was made in, how much it was already sped up and whether a bed lies under the speech are there.
No project and only this one file → say what that closes off: a bed under the speech stays in the sound.

## Missing kinds

The interview will need an example of a kind of footage the person has not sent (a vertical shot for
the vertical layout, a screen recording for the «экран + лицо» question) → ask for one such source,
once, naming why. No such footage → that question is asked in words, without an example, and you say so
(«покажу словами — такого исходника нет»). Never take an example from anywhere but their videos.

Next: `ae.py stage interview`, read `phases/interview.md`.
