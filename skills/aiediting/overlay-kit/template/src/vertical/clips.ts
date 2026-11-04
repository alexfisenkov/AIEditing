// Clips of the vertical cut. Spans are seconds of the video in public/clips/source.mp4; the data lives in spans.json:
//   rate      speed of the speech against that file (the file's own speed-up is already inside it)
//   cta_lead  seconds before the end of the speech at which the call to action appears
//   cta_tail  seconds the call stays after the speech has ended
//   cta       the words of the call: { lead, before, word, after }; null or empty: the clip has no call (then lead and tail are 0)
// Spans are file seconds. Scenes live in scene seconds: the same as file seconds unless src/data/time-map.json has rows;
// then scene = toOld(file) (src/kit/time.ts), and the spans stay in file seconds.
import data from "./spans.json";

export const FPS = 30;
export const RATE = data.rate;

export type ClipId = string;
export type Span = readonly [number, number];

export const SPANS = data.spans as unknown as Record<ClipId, readonly Span[]>;

type Words = { lead: string; before: string; word: string; after: string };
const raw = data as { cta_lead?: number; cta_tail?: number; cta?: Words | null };
export const CTA: Words = { lead: "", before: "", word: "", after: "", ...(raw.cta ?? {}) };
// A call exists when at least one of its words does
export const HAS_CTA = Object.values(CTA).some((w) => w.trim() !== "");
export const CTA_LEAD = HAS_CTA ? raw.cta_lead ?? 0 : 0;
export const CTA_TAIL = HAS_CTA ? raw.cta_tail ?? 0 : 0;
export const TAIL_SECONDS = CTA_TAIL;

// Boundaries are rounded from the running total, so the error never builds up from span to span
const edges = (id: ClipId) => {
  let sum = 0;
  return [0, ...SPANS[id].map(([a, b]) => Math.round(((sum += (b - a) / RATE)) * FPS))];
};
export const spanFrames = (id: ClipId): readonly (readonly [number, number])[] => {
  const e = edges(id);
  return e.slice(1).map((end, i) => [e[i], end - e[i]] as const);
};
export const speechSeconds = (id: ClipId) => SPANS[id].reduce((n, [a, b]) => n + (b - a), 0) / RATE;
export const speechFrames = (id: ClipId) => Math.round(speechSeconds(id) * FPS);
export const durationFrames = (id: ClipId) => speechFrames(id) + Math.round(CTA_TAIL * FPS);

// Seconds of the clip at which the call to action appears
export const ctaStart = (id: ClipId) => Math.max(0, speechSeconds(id) - CTA_LEAD);

// Second of the source file for a frame of the clip
export const frameToNewTime = (id: ClipId) => (frame: number) => {
  let left = (frame / FPS) * RATE;
  for (const [a, b] of SPANS[id]) {
    if (left < b - a) return a + left;
    left -= b - a;
  }
  const last = SPANS[id][SPANS[id].length - 1];
  return last[1];
};
