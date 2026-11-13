// Sound: the speech untouched, a quiet pad under it (only if one was passed), service sounds in one fixed language.
// Which files exist is data: src/data/sfx.json, written by `overlay.py prepare`. A cue is either an old name
// (`[second, "pop-soft"]`, the four synthesised sounds at the top of public/sfx) or a role
// (`{ role: "whoosh", at: second }`): the role's first sound — the person's own before the kit's — starts `peak_ms`
// early, so its loudest moment lands on `at`; `n` takes another sound of the role, `vol` another level.
// A missing file falls back to a sibling sound or role, or is skipped, so a scene never fails on a missing file.
// An ordinary render carries all of it; a render with the input prop `stem` carries one part only — "speech", "sfx" or
// "music" — the stems `overlay.py timeline` lays under the picture.
import React from "react";
import { Audio, Sequence, getInputProps, staticFile } from "remotion";
import sfx from "../data/sfx.json";
import { FPS } from "./tokens";
import { toNewExact } from "./time";
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

// Roles by the strength of the movement: soft < ordinary < big; the hierarchy of levels follows it.
export const ROLE_VOL = {
  "whoosh-soft": 0.2, // a small movement, a layout change
  "whoosh": 0.22, // a block flies in or out
  "whoosh-big": 0.25, // a whole-frame change, at most a few per video
  "drop": 0.15, // something lands in place
  "rise": 0.2, // build-up that ends on the event
  "reverse": 0.18, // back in time, a rewind
  "hit": 0.25, // the strongest accent: a number, a result
  "sub": 0.22, // a low thump under a big reveal
  "ui-appear": 0.15, // a window or panel opens
  "tick": 0.12, // counters, steps, list items
  "tap": 0.12, // a light touch on an element
  "shutter": 0.15, // a screen or a frame appears
  "notify": 0.15, // a message, a notification
  "done": 0.15, // "it worked"
  "error": 0.15, // a calm "not like this"
  "sparkle": 0.12, // a highlight, a shine
  "typing": 0.1, // text being written
  "transition": 0.2, // a section changes
  "glitch": 0.15, // a technical hiccup on purpose
  "ding": 0.15, // a bell: a point is made
  "pop": 0.15, // a small appearance
  "click": 0.15, // a card or an item appears
  "ambience": 0.05, // a room tone under a silent stretch
} as const;
export type Role = keyof typeof ROLE_VOL;
export type RoleCue = { readonly role: Role; readonly at: number; readonly n?: number; readonly vol?: number };
export type Cue = readonly [number, Sfx] | RoleCue;

// Used when the named file is not in sfx.json
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

// Used when a role has no sound on disk (a sibling of the same strength), followed at most three steps
const ROLE_FALLBACK: Record<Role, Role | null> = {
  "whoosh-soft": "whoosh", "whoosh": "whoosh-soft", "whoosh-big": "whoosh", "drop": "pop", "rise": null,
  "reverse": "whoosh", "hit": "sub", "sub": "hit", "ui-appear": "pop", "tick": "click", "tap": "click",
  "shutter": "click", "notify": "ding", "done": "ding", "error": "glitch", "sparkle": "ding", "typing": "click",
  "transition": "whoosh", "glitch": null, "ding": "pop", "pop": "click", "click": "tick", "ambience": null,
};

type RoleSound = { readonly file: string; readonly dur_ms: number; readonly peak_ms: number; readonly level_db: number };

const FILES = sfx.files as Record<string, string>;
const MUSIC = sfx.music as string | null;
// a folder prepared by an older kit has no roles: every role cue is then skipped
const ROLES = ((sfx as { roles?: Record<string, readonly RoleSound[]> }).roles ?? {}) as Record<string, readonly RoleSound[]>;

const fileFor = (name: Sfx): string | null => FILES[name] ?? FILES[FALLBACK[name]] ?? null;

export const soundFor = (cue: RoleCue): RoleSound | null => {
  let role: Role | null = cue.role;
  for (let step = 0; role !== null && step < 4; step++) {
    const list = ROLES[role] ?? [];
    if (list.length) return list[Math.abs(Math.floor(cue.n ?? 0)) % list.length];
    role = ROLE_FALLBACK[role];
  }
  return null;
};

// Files are levelled to about -3 dBFS; a quieter or louder one is brought to that, within 0.5x–2x
const levelOf = (s: RoleSound) => Math.min(2, Math.max(0.5, Math.pow(10, (-3 - s.level_db) / 20)));

const RoleSequence: React.FC<{ cue: RoleCue }> = ({ cue }) => {
  const sound = soundFor(cue);
  const at = toNewExact(cue.at);
  if (!sound || at === null) return null;
  return (
    <Sequence from={Math.round((at - sound.peak_ms / 1000) * FPS)} durationInFrames={Math.max(1, Math.ceil((sound.dur_ms / 1000) * FPS) + 2)} layout="none">
      <Audio src={staticFile(sound.file)} volume={(cue.vol ?? ROLE_VOL[cue.role]) * levelOf(sound)} />
    </Sequence>
  );
};

export type Stem = "speech" | "sfx" | "music";
const STEMS: readonly Stem[] = ["speech", "sfx", "music"];

// null: the whole sound; an unknown value is treated as none, so a mistyped prop never silences a render
export const stemOf = (props: unknown): Stem | null => {
  const asked = (props as { stem?: unknown } | null)?.stem;
  return STEMS.find((s) => s === asked) ?? null;
};

export const SoundTrack: React.FC<{ cues: readonly Cue[] }> = ({ cues }) => {
  const stem = stemOf(getInputProps());
  const on = (part: Stem) => stem === null || stem === part;
  return (
    <>
      {on("speech") ? <Audio src={staticFile("clips/speech.wav")} /> : null}
      {MUSIC && on("music") ? (
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
      {(on("sfx") ? cues : []).map((cue, i) => {
        if ("role" in cue) return <RoleSequence key={i} cue={cue} />;
        const [t, name] = cue;
        const file = fileFor(name);
        if (!file) return null;
        return (
          <Sequence key={i} from={Math.round((toNewExact(t) ?? -9999) * FPS)} durationInFrames={FPS * 4} layout="none">
            <Audio src={staticFile(file)} volume={VOL[name]} />
          </Sequence>
        );
      })}
    </>
  );
};
