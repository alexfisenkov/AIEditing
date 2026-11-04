// The speaker: one continuous video layer, no cuts. Glides between layouts, the face stays in the middle of the frame.
import React from "react";
import { OffthreadVideo, staticFile } from "remotion";
import face from "../data/face.json";
import { LAYOUTS, Layout } from "../data/layouts";
import { C, CHROME, H, W, tint } from "./tokens";
import { ease, lerp, useT } from "./time";

const TRANSITION = 0.85;

// The camera follows the face without steps: the 0.5 s track is cleaned by a median, smoothed by a Gaussian
// and read with a spline between points. Never read the nearest point: that makes the frame walk in visible steps.
const STEP = 0.5;
const track = (col: number, sigmaSec: number) => {
  const raw = (face as number[][]).map((p) => p[col]);
  const med = raw.map((_, i) => {
    const w = raw.slice(Math.max(0, i - 2), i + 3).sort((a, b) => a - b);
    return w[w.length >> 1];
  });
  const sigma = sigmaSec / STEP;
  const radius = Math.ceil(sigma * 3);
  const kernel = Array.from({ length: radius * 2 + 1 }, (_, k) => Math.exp(-((k - radius) ** 2) / (2 * sigma * sigma)));
  return med.map((_, i) => {
    let sum = 0;
    let weight = 0;
    for (let k = -radius; k <= radius; k++) {
      const j = i + k;
      if (j < 0 || j >= med.length) continue;
      sum += med[j] * kernel[k + radius];
      weight += kernel[k + radius];
    }
    return sum / weight;
  });
};
const CX = track(1, 2);
const CY = track(2, 2);
const FH = track(3, 4);

const spline = (a: number[], t: number) => {
  const x = Math.max(0, Math.min(a.length - 1.001, t / STEP));
  const i = Math.floor(x);
  const u = x - i;
  const p0 = a[Math.max(0, i - 1)];
  const p1 = a[i];
  const p2 = a[i + 1];
  const p3 = a[Math.min(a.length - 1, i + 2)];
  return 0.5 * (2 * p1 + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u * u * u);
};

const faceAt = (t: number) => ({ cx: spline(CX, t), cy: spline(CY, t), fh: spline(FH, t) });

type Rect = { x: number; y: number; w: number; h: number; r: number; s: number; px: number; py: number; ring: number };

const rectFor = (l: Layout, t: number): Rect => {
  const { cx, cy, fh } = faceAt(t);
  if (l === "full" || l === "close") {
    // A calm breathing push-in; close is nearer to the face
    const base = l === "close" ? 1.22 : 1.0;
    const s = base + 0.018 + Math.sin(t / 11) * 0.018;
    const vw = W * s;
    const vh = H * s;
    const px = Math.min(0, Math.max(W - vw, W / 2 - cx * vw + (l === "close" ? 0 : (0.5 - cx) * 0)));
    const py = Math.min(0, Math.max(H - vh, H * 0.46 - cy * vh));
    return { x: 0, y: 0, w: W, h: H, r: 0, s, px, py, ring: 0 };
  }
  const box: Record<Exclude<Layout, "full" | "close">, [number, number, number, number, number, number]> = {
    // x, y, width, height, corner radius, share of the face in the frame height
    right: [1168, 70, 690, 900, 26, 0.5],
    left: [62, 70, 690, 900, 26, 0.5],
    half: [960, 0, 960, 1080, 0, 0.5],
    pip: [1542, 682, 318, 318, 159, 0.72],
    pipL: [60, 682, 318, 318, 159, 0.72],
    pipTop: [1542, 80, 318, 318, 159, 0.72],
  };
  const [x, y, w, h, r, share] = box[l as keyof typeof box];
  const s = Math.max((share * h) / (fh * H), w / W, h / H);
  const vw = W * s;
  const vh = H * s;
  const px = Math.min(0, Math.max(w - vw, w / 2 - cx * vw));
  const py = Math.min(0, Math.max(h - vh, h * 0.45 - cy * vh));
  return { x, y, w, h, r, s, px, py, ring: r > 100 ? 1 : 0 };
};

export const currentLayout = (t: number) => {
  let i = 0;
  while (i + 1 < LAYOUTS.length && LAYOUTS[i + 1][0] <= t) i++;
  return { i, now: LAYOUTS[i][1], prev: i > 0 ? LAYOUTS[i - 1][1] : LAYOUTS[0][1], since: LAYOUTS[i][0] };
};

// 0: the speaker fills the frame, 1: the stage with graphics
export const stageAmount = (t: number) => {
  const { now, prev, since } = currentLayout(t);
  const isFull = (l: Layout) => l === "full" || l === "close";
  return lerp(isFull(prev) ? 0 : 1, isFull(now) ? 0 : 1, ease(t, since, TRANSITION));
};

export const Presenter: React.FC = () => {
  const t = useT();
  const { now, prev, since } = currentLayout(t);
  const p = ease(t, since, TRANSITION);
  const a = rectFor(prev, t);
  const b = rectFor(now, t);
  const m = (k: keyof Rect) => lerp(a[k], b[k], p);
  const x = m("x");
  const y = m("y");
  const w = m("w");
  const h = m("h");
  const r = m("r");
  const s = m("s");
  const ring = m("ring");
  const rim = Math.min(1, (W - w) / 300);
  return (
    <>
      {ring > 0.02 && (
        <div
          style={{
            position: "absolute",
            left: x - 5,
            top: y - 5,
            width: w + 10,
            height: h + 10,
            borderRadius: r + 5,
            background: CHROME,
            opacity: ring,
            boxShadow: "0 24px 60px rgba(0,0,0,.6)",
          }}
        />
      )}
      <div
        style={{
          position: "absolute",
          left: x,
          top: y,
          width: w,
          height: h,
          borderRadius: r,
          overflow: "hidden",
          boxShadow: rim > 0 ? `0 0 0 1px ${tint(C.silver, 0.28 * rim)}, 0 40px 90px rgba(0,0,0,${0.55 * rim})` : undefined,
          background: "#000",
        }}
      >
        <OffthreadVideo
          src={staticFile("clips/source.mp4")}
          muted
          style={{ position: "absolute", left: m("px"), top: m("py"), width: W * s, height: H * s, maxWidth: "none" }}
        />
      </div>
    </>
  );
};
