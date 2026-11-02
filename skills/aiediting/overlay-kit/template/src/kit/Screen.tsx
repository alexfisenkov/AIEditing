// A browser window with a real screen capture: scroll by keys, push-in, 3D tilt, cursor, highlight.
// Screens are captured 1600 css pixels wide; all page coordinates (scroll, focus, cursor) are in those pixels.
import React from "react";
import { Img, staticFile } from "remotion";
import { C, FONT, R, RIM, SHADOW } from "./tokens";
import { ease, keys, smooth, useT } from "./time";

export type ScreenName = string;

const BAR = 44;

export const Screen: React.FC<{
  name: ScreenName;
  dark?: boolean;
  w: number;
  h: number;
  at: number;
  out?: number;
  // Text of the address chip in the window bar; no default, the chip is hidden without it
  url?: string;
  // [[second, page y], ...]: smooth scroll
  scroll?: readonly (readonly [number, number])[];
  // Content scale relative to the window width and the page's left edge, to zoom into a column of content
  zoom?: number;
  left?: number;
  rotateY?: number;
  rotateX?: number;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}> = ({ name, dark = true, w, h, at, out, url, scroll, zoom = 1, left = 0, rotateY = 0, rotateX = 0, style, children }) => {
  const t = useT();
  if (t < at - 0.02 || (out !== undefined && t > out + 0.6)) return null;
  const pIn = ease(t, at, 1.1);
  const pOut = out === undefined ? 0 : ease(t, out, 0.5);
  const scale = (w / 1600) * zoom;
  const y = scroll ? smooth(t, scroll) : 0;
  const ry = rotateY * (1 - pIn * 0.35) + (1 - pIn) * 10;
  return (
    <div
      style={{
        width: w,
        height: h,
        opacity: Math.min(pIn * 1.4, 1) * (1 - pOut),
        transform: `perspective(2200px) translateY(${(1 - pIn) * 60 - pOut * 20}px) rotateY(${ry}deg) rotateX(${rotateX}deg) scale(${0.94 + 0.06 * pIn})`,
        borderRadius: R.block,
        overflow: "hidden",
        background: dark ? C.deep : C.paper,
        boxShadow: `${RIM}, ${SHADOW}`,
        position: "relative",
        ...style,
      }}
    >
      <div style={{ height: BAR, display: "flex", alignItems: "center", gap: 8, padding: "0 18px", background: dark ? "#1B1C1F" : "#ECEDEF", position: "relative", zIndex: 2 }}>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ width: 11, height: 11, borderRadius: "50%", background: dark ? "#26282B" : "#C7C9CC" }} />
        ))}
        {url ? (
          <div
            style={{
              marginLeft: 16,
              flex: 1,
              maxWidth: 420,
              height: 26,
              borderRadius: 999,
              display: "flex",
              alignItems: "center",
              padding: "0 14px",
              background: dark ? "#26282B" : "#FFFFFF",
              fontFamily: FONT.text,
              fontSize: 14,
              fontWeight: 500,
              color: dark ? C.muted : "#55585E",
            }}
          >
            {url}
          </div>
        ) : null}
      </div>
      <div style={{ position: "absolute", top: BAR, left: 0, right: 0, bottom: 0, overflow: "hidden" }}>
        <Img
          src={staticFile(`screens/${name}-${dark ? "dark" : "light"}.png`)}
          style={{ position: "absolute", left: -left * scale, top: -y * scale, width: 1600 * scale, height: "auto", maxWidth: "none" }}
        />
        {children}
      </div>
    </div>
  );
};

// Cursor: a path by keys in window coordinates, clicks are rings
export const Cursor: React.FC<{
  path: readonly (readonly [number, number, number])[]; // [second, x, y]
  clicks?: readonly number[];
}> = ({ path, clicks = [] }) => {
  const t = useT();
  if (t < path[0][0] || t > path[path.length - 1][0] + 0.6) return null;
  const x = keys(t, path.map((p) => [p[0], p[1]] as const));
  const y = keys(t, path.map((p) => [p[0], p[2]] as const));
  return (
    <div style={{ position: "absolute", left: x, top: y, zIndex: 5 }}>
      {clicks.map((c) => {
        const p = ease(t, c, 0.6);
        if (t < c || p >= 1) return null;
        return (
          <div
            key={c}
            style={{
              position: "absolute",
              left: -30 * p - 2,
              top: -30 * p - 2,
              width: 60 * p,
              height: 60 * p,
              borderRadius: "50%",
              border: "2px solid rgba(255,255,255,.85)",
              opacity: 1 - p,
            }}
          />
        );
      })}
      <svg width="34" height="34" viewBox="0 0 24 24" style={{ filter: "drop-shadow(0 4px 8px rgba(0,0,0,.6))" }}>
        <path d="M4 2l15 10.5-6.6 1.2 4 7-2.9 1.6-4-7L5 20z" fill="#FFFFFF" stroke="#0E0E10" strokeWidth="1.2" strokeLinejoin="round" />
      </svg>
    </div>
  );
};

// A silver highlight frame around a place on the screen (window coordinates)
export const Focus: React.FC<{ at: number; out?: number; x: number; y: number; w: number; h: number; r?: number }> = ({ at, out, x, y, w, h, r = 18 }) => {
  const t = useT();
  if (t < at || (out !== undefined && t > out + 0.4)) return null;
  const p = ease(t, at, 0.7);
  const q = out === undefined ? 0 : ease(t, out, 0.35);
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        height: h,
        borderRadius: r,
        zIndex: 4,
        opacity: p * (1 - q),
        transform: `scale(${1.05 - 0.05 * p})`,
        boxShadow: "0 0 0 2px rgba(255,255,255,.95), 0 0 34px 8px rgba(255,255,255,.28)",
      }}
    />
  );
};
