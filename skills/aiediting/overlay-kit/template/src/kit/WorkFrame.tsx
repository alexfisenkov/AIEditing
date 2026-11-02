// A real frame taken from another video (the speaker's own work, a lesson, a demo), cut by
// `overlay.py frames`. Light drift, rounded corners, a rim. The frame's aspect comes from src/data/frames.json,
// which `frames` keeps up to date; an unknown name is treated as 16:9.
import React from "react";
import { Img, staticFile } from "remotion";
import frames from "../data/frames.json";
import { R, RIM } from "./tokens";
import { useT } from "./time";

export type FrameName = string;

const ASPECTS = frames as Record<string, number>;

// crop: [x, y, width, height] as shares of the frame: show only that part
export const WorkFrame: React.FC<{
  name: FrameName;
  w: number;
  h: number;
  crop?: readonly [number, number, number, number];
  r?: number;
  drift?: number;
  style?: React.CSSProperties;
}> = ({ name, w, h, crop = [0, 0, 1, 1], r = R.card, drift = 0.03, style }) => {
  const t = useT();
  const [cx, cy, cw, ch] = crop;
  const aspect = 1 / (ASPECTS[name] ?? 16 / 9); // height / width of the stored frame
  const imgW = Math.max(w / cw, h / ch / aspect);
  const imgH = imgW * aspect;
  const dz = 1 + drift + Math.sin(t / 7) * drift * 0.5;
  return (
    <div style={{ width: w, height: h, borderRadius: r, overflow: "hidden", position: "relative", boxShadow: RIM, ...style }}>
      <Img
        src={staticFile(`frames/${name}.jpg`)}
        style={{
          position: "absolute",
          left: -cx * imgW,
          top: -cy * imgH,
          width: imgW,
          height: imgH,
          maxWidth: "none",
          transform: `scale(${dz})`,
          transformOrigin: "50% 50%",
        }}
      />
    </div>
  );
};
