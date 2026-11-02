// The speaker's own mark. Shown only if a logo was passed to `overlay.py prepare --logo FILE`
// (it lands in public/logos/ and design.json "logo" points at it); otherwise both components render nothing.
import React from "react";
import { Img, staticFile } from "remotion";
import design from "../data/design.json";
import { C, FONT, tint } from "./tokens";

const LOGO: string | null = design.logo;

export const LogoMark: React.FC<{ size?: number; style?: React.CSSProperties }> = ({ size = 60, style }) =>
  LOGO ? (
    <Img
      src={staticFile(LOGO)}
      style={{ width: size, height: size, objectFit: "contain", borderRadius: size * 0.2, boxShadow: `0 0 0 1px ${tint(C.silver, 0.35)}`, ...style }}
    />
  ) : null;

// Mark plus an optional text label next to it
export const Logo: React.FC<{ size?: number; label?: string; style?: React.CSSProperties }> = ({ size = 44, label, style }) =>
  LOGO ? (
    <div style={{ display: "flex", alignItems: "center", gap: size * 0.34, ...style }}>
      <LogoMark size={size} />
      {label ? (
        <div style={{ fontFamily: FONT.display, fontWeight: 500, fontSize: size * 0.42, letterSpacing: "0.04em", color: C.white }}>{label}</div>
      ) : null}
    </div>
  ) : null;
