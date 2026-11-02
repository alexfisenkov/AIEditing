// The stage under the graphics: theme background, silver glow, slow particles.
import React, { useMemo } from "react";
import { random } from "remotion";
import { BG, C, H, W, tint } from "./tokens";
import { useT } from "./time";

export const Stage: React.FC<{ amount: number }> = ({ amount }) => {
  const t = useT();
  const dots = useMemo(
    () =>
      new Array(70).fill(0).map((_, i) => ({
        x: random(`x${i}`) * W,
        y: random(`y${i}`) * H,
        r: 1 + random(`r${i}`) * 2.2,
        a: 0.1 + random(`a${i}`) * 0.32,
        v: 2 + random(`v${i}`) * 7,
        ph: random(`p${i}`) * 6.28,
      })),
    []
  );
  if (amount <= 0.001) return null;
  return (
    <div style={{ position: "absolute", inset: 0, background: BG, opacity: amount }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(1100px 720px at 34% 42%, ${tint(C.silver, 0.16)}, transparent 70%)`,
        }}
      />
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
        {dots.map((d, i) => (
          <circle
            key={i}
            cx={d.x + Math.sin(t / 6 + d.ph) * 22}
            cy={((d.y - t * d.v) % H + H) % H}
            r={d.r}
            fill={tint(C.silver, d.a * (0.7 + 0.3 * Math.sin(t / 2 + d.ph)))}
          />
        ))}
      </svg>
    </div>
  );
};
