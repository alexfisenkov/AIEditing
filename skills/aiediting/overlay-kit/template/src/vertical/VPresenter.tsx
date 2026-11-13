// The speaker in a vertical clip: one video layer that glides between layouts, the face stays in the frame.
import React from "react";
import { OffthreadVideo, Sequence, staticFile, useCurrentFrame } from "remotion";
import face from "../data/face.json";
import timeMap from "../data/time-map.json";
import { Face, MapRow, faceSecond, makeFace, rowCuts } from "../kit/faceTrack";
import { useSpeakerBox } from "../kit/speakerBox";
import { ease, lerp, useT } from "../kit/time";
import { CHROME } from "../kit/tokens";
import { ClipId, FPS, RATE, SPANS, frameToNewTime, spanFrames } from "./clips";
import { VH, VW } from "./safe";

export type VLayout = "full" | "close" | "top" | "low" | "ringLow" | "ringTL" | "ringTR" | "ringBL" | "ringBR" | "hidden";
export type VKey = readonly [number, VLayout];

const W = 1920;
const H = 1080;
const TRANSITION = 0.75;
const INSIDE = 0.01; // the tail after the speech reads the face just before the end of the last span

// The face track is cleaned by a median, smoothed by a Gaussian and read with a spline, never the nearest point, and all
// of it inside one piece of the picture (kit/faceTrack.ts). A clip is spans of the file one after another, so the picture
// jumps at the edges of its spans as well: they are cuts next to those of the track and of the time map.
const ROWS = timeMap.rows as unknown as readonly MapRow[];
const readers = new Map<ClipId, (frame: number) => Face>();
const faceOf = (id: ClipId) => {
  let read = readers.get(id);
  if (!read) {
    const spans = SPANS[id];
    const at = makeFace(face as number[][], [...rowCuts(ROWS), ...spans.flatMap(([a, b]) => [faceSecond(ROWS, a), faceSecond(ROWS, b)])]);
    const second = frameToNewTime(id);
    const end = spans[spans.length - 1][1];
    read = (frame) => {
      const n = second(frame);
      return at(faceSecond(ROWS, n === end ? end - INSIDE : n));
    };
    readers.set(id, read);
  }
  return read;
};

type Rect = { x: number; y: number; w: number; h: number; r: number; s: number; px: number; py: number; ring: number; a: number };

// x, y, width, height, corner radius, share of the face in the frame height, where the face sits in the height
const BOX: Record<Exclude<VLayout, "hidden">, readonly [number, number, number, number, number, number, number]> = {
  full: [0, 0, VW, VH, 0, 0, 0.34],
  close: [0, 0, VW, VH, 0, 0.46, 0.36],
  top: [0, 0, VW, 880, 0, 0.5, 0.56],
  low: [0, 1020, VW, 900, 0, 0.5, 0.42],
  ringLow: [370, 1275, 340, 340, 170, 0.72, 0.45],
  ringTL: [70, 270, 300, 300, 150, 0.72, 0.45],
  ringTR: [640, 270, 300, 300, 150, 0.72, 0.45],
  ringBL: [70, 940, 300, 300, 150, 0.72, 0.45],
  ringBR: [640, 940, 300, 300, 150, 0.72, 0.45],
};

const rectFor = (l: VLayout, t: number, { cx, cy, fh }: Face): Rect => {
  const key = l === "hidden" ? "ringLow" : l;
  const [x, y, w, h, r, share, hold] = BOX[key];
  const breath = key === "full" || key === "close" ? 1 + 0.018 + Math.sin(t / 11) * 0.012 : 1;
  const s = Math.max(((share * h) / (fh * H)) * breath, (w / W) * breath, (h / H) * breath);
  const vw = W * s;
  const vh = H * s;
  const px = Math.min(0, Math.max(w - vw, w / 2 - cx * vw));
  const py = Math.min(0, Math.max(h - vh, h * hold - cy * vh));
  return { x, y, w, h, r, s, px, py, ring: r > 100 ? 1 : 0, a: l === "hidden" ? 0 : 1 };
};

const current = (keys: readonly VKey[], t: number) => {
  let i = 0;
  while (i + 1 < keys.length && keys[i + 1][0] <= t) i++;
  return { now: keys[i][1], prev: i > 0 ? keys[i - 1][1] : keys[0][1], since: keys[i][0] };
};

// Share of the graphite stage: a speaker over the whole frame needs none
export const stageShare = (keys: readonly VKey[], t: number) => {
  const { now, prev, since } = current(keys, t);
  const big = (l: VLayout) => l === "full" || l === "close";
  return lerp(big(prev) ? 0 : 1, big(now) ? 0 : 1, ease(t, since, TRANSITION));
};

// The picture of the speaker: the spans of the source file one after another, at the speed of the clip
const Source: React.FC<{ id: ClipId; w: number; h: number; left: number; top: number }> = ({ id, w, h, left, top }) => {
  const frames = spanFrames(id);
  return (
    <>
      {SPANS[id].map(([a], i) => (
        <Sequence key={a} from={frames[i][0]} durationInFrames={Math.max(1, frames[i][1])} layout="none">
          <OffthreadVideo
            src={staticFile("clips/source.mp4")}
            muted
            startFrom={Math.round(a * FPS)}
            playbackRate={RATE}
            style={{ position: "absolute", left, top, width: w, height: h, maxWidth: "none" }}
          />
        </Sequence>
      ))}
    </>
  );
};

type Props = {
  id: ClipId;
  keys: readonly VKey[];
  alpha?: number; // extra opacity of the whole layer (the call to action fades its own circle with it)
  z?: number;
  markers?: boolean; // markers for the frame audit: where the face, the circle and the band are
};

export const VPresenter: React.FC<Props> = ({ id, keys, alpha: extra = 1, z = 2, markers = true }) => {
  const t = useT();
  const f = faceOf(id)(useCurrentFrame());
  const { now, prev, since } = current(keys, t);
  const p = ease(t, since, TRANSITION);
  const a = rectFor(prev, t, f);
  const b = rectFor(now, t, f);
  const m = (k: keyof Rect) => lerp(a[k], b[k], p);
  const x = m("x");
  const y = m("y");
  const w = m("w");
  const h = m("h");
  const r = m("r");
  const s = m("s");
  const ring = m("ring");
  const alpha = m("a") * extra;
  useSpeakerBox({ x, y, w, h, r, shown: alpha }, markers); // the circle of the call to action is a second layer: only the main one reports
  return (
    <div style={{ position: "absolute", inset: 0, opacity: alpha, zIndex: z }}>
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
      <div style={{ position: "absolute", left: x, top: y, width: w, height: h, borderRadius: r, overflow: "hidden", background: "#000" }}>
        <Source id={id} w={W * s} h={H * s} left={m("px")} top={m("py")} />
      </div>
      {markers && (
        <>
          <div
            data-face
            data-shown={alpha}
            style={{
              position: "absolute",
              left: x + m("px") + f.cx * W * s - f.fh * H * s * 0.48,
              top: y + m("py") + f.cy * H * s - f.fh * H * s * 0.62,
              width: f.fh * H * s * 0.96,
              height: f.fh * H * s * 1.24,
              pointerEvents: "none",
            }}
          />
          {ring > 0.5 && <div data-ring data-shown={alpha} style={{ position: "absolute", left: x, top: y, width: w, height: h, pointerEvents: "none" }} />}
          {ring <= 0.5 && h < VH - 2 && <div data-band data-shown={alpha} style={{ position: "absolute", left: x, top: y, width: w, height: h, pointerEvents: "none" }} />}
        </>
      )}
    </div>
  );
};
