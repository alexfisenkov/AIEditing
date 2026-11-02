// Connector lines and counters: diagrams are drawn in SVG over the 1920x1080 frame.
import React from "react";
import { C, tint } from "./tokens";
import { ease, useT } from "./time";

// Draws a curve from A to B and runs a data pulse along it (pulse=true)
export const Link: React.FC<{
  at: number;
  out?: number;
  from: readonly [number, number];
  to: readonly [number, number];
  bend?: number; // bend in pixels
  dur?: number;
  pulse?: boolean;
  pulseEvery?: number;
  dashed?: boolean;
}> = ({ at, out, from, to, bend = 0, dur = 0.9, pulse = true, pulseEvery = 1.8, dashed }) => {
  const t = useT();
  if (t < at || (out !== undefined && t > out + 0.5)) return null;
  const p = ease(t, at, dur);
  const q = out === undefined ? 0 : ease(t, out, 0.4);
  const mx = (from[0] + to[0]) / 2;
  const my = (from[1] + to[1]) / 2;
  const dx = to[0] - from[0];
  const dy = to[1] - from[1];
  const len = Math.hypot(dx, dy) || 1;
  const cx = mx - (dy / len) * bend;
  const cy = my + (dx / len) * bend;
  const d = `M${from[0]} ${from[1]} Q${cx} ${cy} ${to[0]} ${to[1]}`;
  // A point on the quadratic curve
  const point = (u: number) => [
    (1 - u) ** 2 * from[0] + 2 * (1 - u) * u * cx + u ** 2 * to[0],
    (1 - u) ** 2 * from[1] + 2 * (1 - u) * u * cy + u ** 2 * to[1],
  ];
  const u = ((t - at) % pulseEvery) / pulseEvery;
  const [px, py] = point(u);
  const approx = len * 1.15;
  return (
    <svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0, overflow: "visible", opacity: 1 - q, pointerEvents: "none" }}>
      <path
        d={d}
        fill="none"
        stroke={tint(C.silver, 0.55)}
        strokeWidth={1.6}
        strokeLinecap="round"
        strokeDasharray={dashed ? "8 10" : `${approx * p} ${approx}`}
      />
      {pulse && p >= 1 && !dashed && (
        <circle cx={px} cy={py} r={4.5} fill="#FFFFFF" style={{ filter: "drop-shadow(0 0 8px rgba(255,255,255,.9))" }} />
      )}
    </svg>
  );
};

export const Count: React.FC<{ at: number; to: number; from?: number; dur?: number; suffix?: string; style?: React.CSSProperties }> = ({
  at,
  to,
  from = 0,
  dur = 1.2,
  suffix = "",
  style,
}) => {
  const t = useT();
  const v = Math.round(from + (to - from) * ease(t, at, dur));
  return (
    <span style={{ fontVariantNumeric: "tabular-nums", ...style }}>
      {v}
      {suffix}
    </span>
  );
};
