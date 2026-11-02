// Surfaces: graphite glass with a sweep along the edge, a pill, a chrome token, a service logo.
import React from "react";
import { BRANDS, BrandName } from "../data/brands";
import { CHROME, C, FONT, GLASS, R, RIM, SHADOW, tint } from "./tokens";
import { ease, useT } from "./time";

export const Glass: React.FC<{
  at?: number;
  pad?: number;
  r?: number;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}> = ({ at, pad = 32, r = R.card, style, children }) => {
  const t = useT();
  const sweep = at === undefined ? 1 : ease(t, at + 0.2, 1.4);
  return (
    <div style={{ position: "relative", borderRadius: r, background: GLASS, boxShadow: `${RIM}, ${SHADOW}`, padding: pad, overflow: "hidden", ...style }}>
      {sweep < 1 && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: `${-45 + sweep * 150}%`,
            width: "45%",
            height: 1,
            background: "linear-gradient(90deg,transparent,rgba(255,255,255,.85),transparent)",
          }}
        />
      )}
      {children}
    </div>
  );
};

export const Pill: React.FC<{ tone?: "dark" | "light" | "ok"; size?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({
  tone = "dark",
  size: asked = 26,
  style,
  children,
}) => {
  // Meaningful text must read on a phone: in a messenger the frame shrinks 2-5 times
  const size = Math.max(asked, 26);
  return (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 10,
      whiteSpace: "nowrap",
      padding: `${size * 0.42}px ${size * 0.9}px`,
      borderRadius: R.pill,
      fontFamily: FONT.text,
      fontWeight: 600,
      fontSize: size,
      color: tone === "light" ? C.ink : C.white,
      background: tone === "light" ? CHROME : tone === "ok" ? C.ok : tint(C.graphiteSoft, 0.92),
      boxShadow: tone === "light" ? "inset 0 1px 1px #fff, 0 10px 26px rgba(0,0,0,.45)" : RIM,
      ...style,
    }}
  >
    {children}
  </div>
  );
};

// A chrome circle with a digit or an icon
export const Token: React.FC<{ size?: number; style?: React.CSSProperties; children?: React.ReactNode }> = ({ size = 64, style, children }) => (
  <div
    style={{
      width: size,
      height: size,
      flex: "none",
      borderRadius: "50%",
      background: CHROME,
      boxShadow: "inset 0 1px 1px #fff, 0 10px 26px rgba(0,0,0,.5)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: FONT.display,
      fontWeight: 700,
      fontSize: size * 0.4,
      color: C.ink,
      ...style,
    }}
  >
    {children}
  </div>
);

// Monochrome service logo on a graphite circle with a silver rim.
// A name that is not in src/data/brands.json falls back to its first letters, so a scene never breaks on a missing logo.
export const Brand: React.FC<{ name: BrandName; size?: number; chrome?: boolean; style?: React.CSSProperties }> = ({ name, size = 96, chrome, style }) => (
  <div
    style={{
      width: size,
      height: size,
      flex: "none",
      borderRadius: "50%",
      background: chrome ? CHROME : `linear-gradient(165deg,${C.graphiteSoft},${C.deep})`,
      boxShadow: chrome ? "inset 0 1px 1px #fff, 0 14px 34px rgba(0,0,0,.55)" : `${RIM}, 0 14px 34px rgba(0,0,0,.5)`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: FONT.display,
      fontWeight: 700,
      fontSize: size * 0.3,
      color: chrome ? C.ink : C.white,
      ...style,
    }}
  >
    {BRANDS[name] ? (
      <svg viewBox="0 0 24 24" width={size * 0.54} height={size * 0.54} fill={chrome ? C.ink : C.white}>
        <path d={BRANDS[name]} />
      </svg>
    ) : (
      name.slice(0, 2).toUpperCase()
    )}
  </div>
);

// A text mark where a logo is not available
export const TextMark: React.FC<{ size?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ size = 96, style, children }) => (
  <div
    style={{
      width: size,
      height: size,
      flex: "none",
      borderRadius: "50%",
      background: `linear-gradient(165deg,${C.graphiteSoft},${C.deep})`,
      boxShadow: `${RIM}, 0 14px 34px rgba(0,0,0,.5)`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: FONT.display,
      fontWeight: 700,
      fontSize: size * 0.3,
      color: C.white,
      ...style,
    }}
  >
    {children}
  </div>
);
