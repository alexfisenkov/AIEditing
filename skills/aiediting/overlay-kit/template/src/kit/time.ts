// Time in the video is SECONDS OF THE PASSED VIDEO (public/clips/source.mp4), the same seconds as raw/words.txt.
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { EASE, FPS } from "./tokens";

export const useT = () => useCurrentFrame() / FPS;

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
