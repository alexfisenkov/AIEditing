// Sound: the speech untouched, a quiet pad under it (only if one was passed), service sounds in one fixed language.
// Which files exist is data: src/data/sfx.json, written by `overlay.py prepare` (four CC0 sounds ship with the kit,
// `--sfx DIR` adds or replaces files by name). A cue whose file is missing falls back to a sibling sound or is skipped,
// so a scene never fails on a missing file. Levels follow the usual practice for talking-head edits.
import React from "react";
import { Audio, Sequence, staticFile } from "remotion";
import sfx from "../data/sfx.json";
import { FPS } from "./tokens";
import { DURATION } from "../data/layouts";

export const VOL = {
  "whoosh-soft": 0.2, // layout change, a big movement
  "mouse-click": 0.15, // a card or an item appears
  switch: 0.15, // a conclusion line appears
  "shutter-modern": 0.15, // a screen or a frame appears
  "page-turn": 0.15, // a section changes
  ding: 0.15, // a tick, "it worked"
  "pop-soft": 0.15, // a small appearance
  tick: 0.12, // counters, steps
  "riser-1s": 0.2, // build-up, at most two per video
} as const;
export type Sfx = keyof typeof VOL;
export type Cue = readonly [number, Sfx];

// Used when the named file is not in sfx.json (the kit ships only four CC0 sounds)
const FALLBACK: Record<Sfx, Sfx> = {
  "whoosh-soft": "whoosh-soft",
  "mouse-click": "tick",
  switch: "pop-soft",
  "shutter-modern": "whoosh-soft",
  "page-turn": "whoosh-soft",
  ding: "pop-soft",
  "pop-soft": "pop-soft",
  tick: "tick",
  "riser-1s": "riser-1s",
};

const FILES = sfx.files as Record<string, string>;
const MUSIC = sfx.music as string | null;

const fileFor = (name: Sfx): string | null => FILES[name] ?? FILES[FALLBACK[name]] ?? null;

export const SoundTrack: React.FC<{ cues: readonly Cue[] }> = ({ cues }) => (
  <>
    <Audio src={staticFile("clips/speech.wav")} />
    {MUSIC ? (
      <Audio
        src={staticFile(MUSIC)}
        loop
        loopVolumeCurveBehavior="extend"
        volume={(f) => {
          const s = f / FPS;
          const fade = Math.min(1, s / 3, (DURATION - s) / 3);
          return 0.055 * Math.max(0, fade);
        }}
      />
    ) : null}
    {cues.map(([t, name], i) => {
      const file = fileFor(name);
      if (!file) return null;
      return (
        <Sequence key={i} from={Math.round(t * FPS)} durationInFrames={FPS * 4} layout="none">
          <Audio src={staticFile(file)} volume={VOL[name]} />
        </Sequence>
      );
    })}
  </>
);
