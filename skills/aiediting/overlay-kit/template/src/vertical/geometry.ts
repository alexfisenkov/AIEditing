// Boxes in frame pixels and what the audit asks of them. No imports: a test runs this file on its own.
export type Box = { left: number; right: number; top: number; bottom: number };

// Pixels between neighbouring plates, pictures and captions; less reads as "touching" although nothing overlaps
export const TIGHT = 12;

// Area of the overlap of two boxes
export const crossing = (a: Box, b: Box) =>
  Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));

export const area = (a: Box) => Math.max(1, (a.right - a.left) * (a.bottom - a.top));

// The gap between two boxes: 0 when they touch or overlap
export const distance = (a: Box, b: Box) => Math.max(a.left - b.right, b.left - a.right, a.top - b.bottom, b.top - a.bottom, 0);

export const isTight = (a: Box, b: Box) => distance(a, b) < TIGHT;
