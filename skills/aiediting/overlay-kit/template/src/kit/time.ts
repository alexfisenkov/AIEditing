// Time in the video is SECONDS OF THE PASSED VIDEO (public/clips/source.mp4), the same seconds as raw/words.txt.
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { EASE, FPS } from "./tokens";

import timeMap from "../data/time-map.json";

// Marker edits remove speech while scenes stay in the seconds of the accepted cut. Row: new start, new end, old start, old end, lead.
// An empty map means no edits. tools: правка-нарезки.py (see README).
const ROWS = timeMap.rows as unknown as readonly (readonly [number, number, number, number, number])[];

export const toOld = (n: number) => {
  if (!ROWS.length) return n;
  let a = 0;
  let b = ROWS.length - 1;
  while (a < b) {
    const m = (a + b + 1) >> 1;
    if (ROWS[m][0] <= n) a = m;
    else b = m - 1;
  }
  const r = ROWS[a];
  return Math.min(r[3], r[2] + Math.max(0, n - r[0] - r[4]));
};

export const toNewExact = (o: number): number | null => {
  if (!ROWS.length) return o;
  for (const r of ROWS) {
    if (o >= r[2] && o < r[3]) return r[0] + r[4] + (o - r[2]);
  }
  return null;
};

export const toNew = (o: number) => {
  const e = toNewExact(o);
  if (e !== null) return e;
  const next = ROWS.find((r) => r[2] >= o);
  return next ? next[0] : ROWS[ROWS.length - 1][1];
};

export const useT = () => toOld(useCurrentFrame() / FPS);

// 0 to 1 from moment a over dur seconds with the signature ease-out
export const ease = (t: number, a: number, dur = 0.7, fn = EASE) =>
  interpolate(t, [a, a + dur], [0, 1], { easing: fn, extrapolateLeft: "clamp", extrapolateRight: "clamp" });

// By keys [[t, v], ...]
export const keys = (t: number, pts: readonly (readonly [number, number])[]) =>
  interpolate(t, pts.map((p) => p[0]), pts.map((p) => p[1]), {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

// Smooth scroll without a jerk at the start: ease in and out
export const smooth = (t: number, pts: readonly (readonly [number, number])[]) =>
  interpolate(t, pts.map((p) => p[0]), pts.map((p) => p[1]), {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

export const lerp = (a: number, b: number, p: number) => a + (b - a) * p;
