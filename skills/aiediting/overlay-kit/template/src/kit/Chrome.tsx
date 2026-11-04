// The permanent frame of the video: the mark in the corner and a thin progress strip with chapters at the bottom.
import React from "react";
import { CHAPTERS, DURATION } from "../data/layouts";
import { C, FONT } from "./tokens";
import { ease, toNew, useT } from "./time";
import { Logo } from "./Logo";

export const Frame: React.FC = () => {
  const t = useT();
  const show = ease(t, 1.2, 1) * (1 - ease(t, DURATION - Math.min(7.5, DURATION * 0.1), 0.7));
  const idx = CHAPTERS.findIndex((c, i) => t >= c.t && (i + 1 === CHAPTERS.length || t < CHAPTERS[i + 1].t));
  const ch = CHAPTERS[Math.max(0, idx)];
  const label = ease(t, ch.t + 0.1, 0.8);
  const x0 = 60;
  const width = 1800;
  return (
    <div style={{ position: "absolute", inset: 0, opacity: show, pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: 44, top: 34, filter: "drop-shadow(0 4px 14px rgba(0,0,0,.55))" }}>
        <Logo size={40} />
      </div>
      {/* Progress strip: fills with time, chapter marks */}
      <div style={{ position: "absolute", left: x0, top: 1048, width, height: 2, background: "rgba(255,255,255,.2)", borderRadius: 2 }}>
        <div style={{ width: `${(toNew(t) / DURATION) * 100}%`, height: 2, background: C.white, borderRadius: 2, boxShadow: "0 0 10px rgba(255,255,255,.75)" }} />
        {CHAPTERS.map((c) => (
          <div
            key={c.t}
            style={{
              position: "absolute",
              left: (toNew(c.t) / DURATION) * width - 3,
              top: -2,
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: t >= c.t ? C.white : "rgba(255,255,255,.4)",
            }}
          />
        ))}
      </div>
      <div
        style={{
          position: "absolute",
          left: x0 + (toNew(ch.t) / DURATION) * width,
          top: 1012,
          opacity: label,
          transform: `translateX(${(1 - label) * -14}px)`,
          fontFamily: FONT.text,
          fontWeight: 600,
          fontSize: 19,
          color: C.white,
          textShadow: "0 2px 10px rgba(0,0,0,.75)",
          whiteSpace: "nowrap",
        }}
      >
        {ch.name}
      </div>
    </div>
  );
};
