// The face track, read without steps and without gliding through a change of the picture.
// Pure arithmetic with no imports: Presenter and VPresenter read the face through it, and a test runs it in node.
//
// A point of src/data/face.json is [t, cx, cy, h, since]. `since` is the second at which the point's piece of the picture
// began: a scene change or a hard cut that `prepare` found. More cuts come from the caller: the edges of the time map's rows
// (edits by markers) and the edges of a vertical clip's spans. The median, the Gaussian and the spline all stay inside one
// piece. Smoothed through a cut, the frame glides from the old face to the new one and cuts the speaker's face for seconds.
export type FacePoint = readonly number[];
export type MapRow = readonly [number, number, number, number, number]; // new start, new end, old start, old end, lead
export type Face = { cx: number; cy: number; fh: number };

export const STEP = 0.5; // seconds between the points of the track
const NEAR = 1e-3; // a cut this close after a second already holds it: seconds are rounded on their way here
const INSIDE = 0.01; // how far before its end a held row is read, to stay in its own piece

// Cuts the track knows itself: where `since` changes
export const trackCuts = (points: readonly FacePoint[]) => [...new Set(points.map((p) => p[4] ?? 0))].filter((s) => s > 0);

// Cuts of an edit by markers, in scene seconds: the picture jumps at both edges of every row
export const rowCuts = (rows: readonly MapRow[]) => rows.flatMap((r) => [r[2], r[3]]);

// The scene second at which the face is read for a second of the file. It is toOld of kit/time.ts, except that the held end
// of a row stays inside the row: the next piece starts at that very second, and its face is another one.
export const faceSecond = (rows: readonly MapRow[], n: number) => {
  if (!rows.length) return n;
  let a = 0;
  let b = rows.length - 1;
  while (a < b) {
    const m = (a + b + 1) >> 1;
    if (rows[m][0] <= n) a = m;
    else b = m - 1;
  }
  const r = rows[a];
  return Math.max(r[2], Math.min(r[3] - INSIDE, r[2] + Math.max(0, n - r[0] - r[4])));
};

const gaussian = (sigma: number) => {
  const radius = Math.ceil(sigma * 3);
  return Array.from({ length: radius * 2 + 1 }, (_, k) => Math.exp(-((k - radius) ** 2) / (2 * sigma * sigma)));
};

// (second) => the face at it. `cuts` are seconds, added to the track's own.
export const makeFace = (points: readonly FacePoint[], cuts: readonly number[] = []) => {
  const last = points.length - 1;
  const own = trackCuts(points).sort((a, b) => a - b);
  const bounds = [...new Set([...own, ...cuts])].filter((c) => c > 0).sort((a, b) => a - b);
  // How many of the sorted cuts lie at a second or before it: the number of its piece
  const count = (list: readonly number[], t: number) => {
    let a = 0;
    let b = list.length;
    while (a < b) {
      const m = (a + b) >> 1;
      if (list[m] <= t + NEAR) a = m + 1;
      else b = m;
    }
    return a;
  };
  const pieceAt = (t: number) => count(bounds, t);
  // For every point, the first and the last point of its piece; for every piece that has points, the same pair
  const piece = points.map((_, i) => pieceAt(i * STEP));
  const from = points.map((_, i) => i);
  const to = points.map((_, i) => i);
  for (let i = 1; i <= last; i++) if (piece[i] === piece[i - 1]) from[i] = from[i - 1];
  for (let i = last - 1; i >= 0; i--) if (piece[i] === piece[i + 1]) to[i] = to[i + 1];
  const range = new Map<number, readonly [number, number]>();
  piece.forEach((p, i) => range.set(p, [from[i], to[i]]));

  // Cleaned by a median and smoothed by a Gaussian, both only over the points of the same piece
  const column = (col: number, sigmaSec: number) => {
    const raw = points.map((p) => p[col]);
    const med = raw.map((_, i) => {
      const w = raw.slice(Math.max(from[i], i - 2), Math.min(to[i], i + 2) + 1).sort((a, b) => a - b);
      return w[w.length >> 1];
    });
    const kernel = gaussian(sigmaSec / STEP);
    const radius = kernel.length >> 1;
    return med.map((_, i) => {
      let sum = 0;
      let weight = 0;
      for (let j = Math.max(from[i], i - radius); j <= Math.min(to[i], i + radius); j++) {
        sum += med[j] * kernel[j - i + radius];
        weight += kernel[j - i + radius];
      }
      return sum / weight;
    });
  };
  const CX = column(1, 2);
  const CY = column(2, 2);
  const FH = column(3, 4);

  // A spline between the points of one piece: before its first point and after its last one the value holds.
  // Never read the nearest point: that makes the frame walk in visible steps.
  const spline = (a: readonly number[], t: number, lo: number, hi: number) => {
    const x = Math.max(lo, Math.min(hi, t / STEP));
    const i = Math.min(Math.floor(x), Math.max(lo, hi - 1));
    const u = x - i;
    const at = (k: number) => a[Math.max(lo, Math.min(hi, k))];
    const p0 = at(i - 1);
    const p1 = at(i);
    const p2 = at(i + 1);
    const p3 = at(i + 2);
    return 0.5 * (2 * p1 + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u * u * u);
  };

  // A piece shorter than the step may hold no point. Then the nearest point of the same piece of the track itself stands
  // in for it (the same face by the detector), not simply the nearest one: that may belong to the take next door.
  const ownPiece = points.map((_, i) => count(own, i * STEP));
  const standIn = (t: number): readonly [number, number] => {
    const p = count(own, t);
    const first = ownPiece.indexOf(p);
    const near = Math.max(0, Math.min(last, Math.round(t / STEP)));
    const i = first < 0 ? near : Math.max(first, Math.min(ownPiece.lastIndexOf(p), near));
    return [i, i];
  };

  return (t: number): Face => {
    const [lo, hi] = range.get(pieceAt(t)) ?? standIn(t);
    return { cx: spline(CX, t, lo, hi), cy: spline(CY, t, lo, hi), fh: spline(FH, t, lo, hi) };
  };
};
