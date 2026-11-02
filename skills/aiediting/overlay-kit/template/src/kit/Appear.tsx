// Appearing out of blur, and leaving. The main motion device of the system: no jumps.
import React from "react";
import { ease, useT } from "./time";

export const Appear: React.FC<{
  at: number;
  out?: number;
  dur?: number;
  y?: number;
  x?: number;
  blur?: number;
  scale?: number;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ at, out, dur = 0.8, y = 28, x = 0, blur = 14, scale = 1, style, children }) => {
  const t = useT();
  if (t < at - 0.02) return null;
  if (out !== undefined && t > out + 0.45) return null;
  const pIn = ease(t, at, dur);
  const pOut = out === undefined ? 0 : ease(t, out, 0.42);
  const opacity = Math.min(pIn * 1.25, 1) * (1 - pOut);
  const b = (1 - pIn) * blur + pOut * blur * 0.6;
  return (
    <div
      style={{
        opacity,
        transform: `translate(${(1 - pIn) * x}px,${(1 - pIn) * y - pOut * 14}px) scale(${scale + (1 - scale) * pIn})`,
        filter: b > 0.05 ? `blur(${b}px)` : undefined,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

// An absolutely positioned block in frame coordinates (1920x1080)
export const At: React.FC<{
  x: number;
  y: number;
  w?: number;
  h?: number;
  z?: number;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ x, y, w, h, z, style, children }) => (
  <div style={{ position: "absolute", left: x, top: y, width: w, height: h, zIndex: z, ...style }}>{children}</div>
);
