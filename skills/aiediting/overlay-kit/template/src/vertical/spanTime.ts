// Which second of the file a frame of a vertical clip shows. Pure arithmetic with no imports: clips.ts feeds it spans.json,
// and a test runs it in node.
//
// The video layer plays span k from the whole frame edges[k]. The second of a frame is counted from that same frame, so at
// a joint of two spans the picture of one span never meets the second of the other. Counted from the unrounded running
// total instead, the two disagree for one frame at about every other joint: one frame of the new picture in the old frame.
export type Span = readonly [number, number];

const INSIDE = 0.01; // a frame of a span never reaches the second at which the span ends: the next piece begins there

// Boundaries are rounded from the running total, so the error never builds up from span to span
export const spanEdges = (spans: readonly Span[], fps: number, rate: number) => {
  let sum = 0;
  return [0, ...spans.map(([a, b]) => Math.round((sum += (b - a) / rate) * fps))];
};

// (frame of the clip) => second of the source file. After the last span the second stands at its end.
export const frameSecond = (spans: readonly Span[], fps: number, rate: number) => {
  const edges = spanEdges(spans, fps, rate);
  return (frame: number) => {
    let k = 0;
    while (k < spans.length - 1 && frame >= edges[k + 1]) k++;
    const [a, b] = spans[k];
    if (frame >= edges[k + 1]) return b;
    return Math.min(b - INSIDE, a + ((frame - edges[k]) / fps) * rate);
  };
};
