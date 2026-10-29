# Design

`ae.py stage design`. The design system of this format: font, colours, chapter plates, captions,
graphics. Everything is chosen by eye, on frames of the person's own video.

## Start: their style or the example

One question (`ae.py ask choice --note "стиль: свой или пример"`):

```
Как будем оформлять?
1. Свой стиль — соберём по шагам: шрифт, цвета, плашки, субтитры.
2. Взять за основу пример Chrome & Graphite (графит и хром, шрифты Unbounded и Onest) и поправить под себя.
```

The example → `python "<skillDir>/tools/ae.py" design-example <skill>`: its tokens and fonts go into
`.aiediting-work/<skill>/design/`. Their own → start from the same tokens file and change it with them.
`design/tokens.json` is data: you edit it, by their answers.

## Elements — three variants side by side

For each element the format uses — in this order: font and colours, chapter plate, captions, graphics:

1. `python "<skillDir>/tools/ae.py" samples <skill> --element <chapter|caption|card> --frame <a frame of theirs>`
   — the renderer draws the variants from the draft's `design/` on their frame; they land on the
   dashboard side by side.
2. `ae.py ask choice --note "<элемент>: какой вариант"`; the answer → `ae.py choose <skill> <element> <n>`.
   The choice goes into `design/samples/`, and what makes it different (size, colour, place) into
   `design/tokens.json`.
3. «Ни один» → ask what is wrong, change the tokens by their words, draw again.

A frame with a face and a frame with a screen show different things — use the one the element will
live on (a chapter plate over a screen, captions over a face in a vertical).

## What goes into the skill

`design/` of the draft — tokens, fonts, chosen samples — is copied into the format skill as it is.
Fonts must be files with a licence that allows it (OFL for Unbounded, Onest, JetBrains Mono); a font the
person only has installed on their system stays a name in the tokens, not a file.

Next: `ae.py stage trial`, read `phases/trial.md`.
