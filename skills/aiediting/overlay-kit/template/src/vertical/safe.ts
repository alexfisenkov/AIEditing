// Vertical frame 1080x1920 and the safe zone of text. Reels, Shorts and TikTok cover the top, the bottom and the right edge
// with their own buttons. Text and everything meant to be read stays inside SAFE. The speaker, the stage and pictures may cross it.
import data from "./spans.json";

export const VW = 1080;
export const VH = 1920;

export type Zone = { readonly x0: number; readonly x1: number; readonly y0: number; readonly y1: number };

// The preset is chosen by "safe" in spans.json. Add a platform here, not in a scene.
export const SAFE_PRESETS: Record<string, Zone> = {
  reels: { x0: 70, x1: 940, y0: 270, y1: 1240 },
};

const asked = (data as { safe?: string }).safe ?? "reels";
export const SAFE: Zone = SAFE_PRESETS[asked] ?? SAFE_PRESETS.reels;
export const SAFE_W = SAFE.x1 - SAFE.x0;
export const SAFE_H = SAFE.y1 - SAFE.y0;

// Covers: the profile grid crops a 1080x1920 cover to 3:4 and to 1:1. What must stay visible lives inside these bands.
export const COVER_BANDS = {
  "3:4": { y0: 240, y1: 1680 },
  "1:1": { y0: 420, y1: 1500 },
} as const;

// Smallest sizes on a phone
export const MIN_TEXT = 34;

// Texts that may be smaller than MIN_TEXT (a web address under a screen, say): list them as "small_ok" in spans.json
export const SMALL_OK: readonly string[] = (data as { small_ok?: string[] }).small_ok ?? [];
