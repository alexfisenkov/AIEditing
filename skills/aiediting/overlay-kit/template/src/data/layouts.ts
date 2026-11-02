// Speaker layouts [second, layout] and the chapters of the video.
// Seconds are seconds of the video in public/clips/source.mp4 (the one passed to `overlay.py prepare`).
// DURATION is set by `prepare`. The layouts of every segment live in layouts-<x>.ts and are collected
// in the generated all-layouts.ts (`overlay.py index`, run automatically by frame/draft/final).
import { ALL_LAYOUTS } from "./all-layouts";
import { Layout, LayoutKey } from "./layout-types";

export type { Layout };

export const DURATION = 60.0;

// Chapter labels sit on the progress strip at the bottom. Write them in the speaker's language; an empty name shows no label.
export const CHAPTERS: readonly { t: number; name: string }[] = [{ t: 0, name: "" }];

export const LAYOUTS: readonly LayoutKey[] = [[0, "full"] as LayoutKey, ...ALL_LAYOUTS].sort((a, b) => a[0] - b[0]);
