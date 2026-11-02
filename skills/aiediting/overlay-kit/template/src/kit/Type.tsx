// Typography: chrome headline with a running shine, lead, eyebrow, technical caption.
import React from "react";
import { C, FONT, SHINE } from "./tokens";
import { useT } from "./time";

export const Chrome: React.FC<{
  size?: number;
  weight?: number;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ size = 88, weight = 700, style, children }) => {
  const t = useT();
  const pos = ((t % 9) / 9) * 260 - 80; // chromeShine, 9 s
  return (
    <div
      style={{
        fontFamily: FONT.display,
        fontWeight: weight,
        fontSize: size,
        lineHeight: 1.08,
        letterSpacing: "-0.015em",
        backgroundImage: SHINE,
        backgroundSize: "220% 100%",
        backgroundPosition: `${-pos}% 0`,
        WebkitBackgroundClip: "text",
        backgroundClip: "text",
        color: "transparent",
        paddingBottom: "0.12em",
        ...style,
      }}
    >
      {children}
    </div>
  );
};

export const H2: React.FC<{ size?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ size = 46, style, children }) => (
  <div style={{ fontFamily: FONT.display, fontWeight: 600, fontSize: size, lineHeight: 1.15, letterSpacing: "-0.01em", color: C.white, ...style }}>
    {children}
  </div>
);

export const Lead: React.FC<{ size?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ size = 30, style, children }) => (
  <div style={{ fontFamily: FONT.text, fontWeight: 500, fontSize: size, lineHeight: 1.35, color: C.muted, ...style }}>{children}</div>
);

export const Eyebrow: React.FC<{ size?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ size = 18, style, children }) => (
  <div style={{ fontFamily: FONT.display, fontWeight: 500, fontSize: size, letterSpacing: "0.22em", textTransform: "uppercase", color: C.faint, ...style }}>
    {children}
  </div>
);

export const Mono: React.FC<{ size?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ size = 22, style, children }) => (
  <div style={{ fontFamily: FONT.mono, fontWeight: 400, fontSize: size, color: C.muted, ...style }}>{children}</div>
);
