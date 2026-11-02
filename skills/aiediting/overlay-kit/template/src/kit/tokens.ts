// Design tokens for the video. The values come as data: tools/overlay.py (prepare) writes
// src/data/design.json from the design folder's tokens.json. Do not hard-code new colours elsewhere.
import { Easing } from "remotion";
import design from "../data/design.json";

export const FPS = 30;
export const W = 1920;
export const H = 1080;

export const C = design.C;

export const CHROME = design.CHROME;
export const BG = design.BG;
export const GLASS = design.GLASS;
export const HAIR = design.HAIR;

export const FONT = design.FONT;

export const R = design.R;

export const RIM = design.RIM;
export const SHADOW = design.SHADOW;
export const SHINE = design.SHINE;

// A token colour with transparency: tint(C.silver, 0.2). A colour not written as #RRGGBB is used as it is.
export const tint = (color: string, alpha: number): string => {
  const m = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(color);
  return m ? `rgba(${parseInt(m[1], 16)},${parseInt(m[2], 16)},${parseInt(m[3], 16)},${alpha})` : color;
};

export const EASE = Easing.bezier(0.16, 1, 0.3, 1);
export const POP = Easing.bezier(0.34, 1.56, 0.64, 1);
