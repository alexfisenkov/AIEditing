// Shared parts of the vertical scenes: the stage, the speaker's mark, the call to action, the frame audit.
import React, { useMemo } from "react";
import { random, useCurrentFrame } from "remotion";
import { ease, useT } from "../kit/time";
import { BG, C, CHROME, FONT, MARK as TOKEN_MARK, R, RIM, SHADOW, tint } from "../kit/tokens";
import { Logo } from "../kit/Logo";
import { Chrome } from "../kit/Type";
import { ClipId, CTA, FPS, HAS_CTA, ctaStart, speechSeconds } from "./clips";
import { SAFE, VH, VW } from "./safe";
import { VPresenter } from "./VPresenter";

export { SafeAudit } from "./audit";

export const VStage: React.FC<{ amount: number }> = ({ amount }) => {
  const t = useT();
  const dots = useMemo(
    () =>
      new Array(90).fill(0).map((_, i) => ({
        x: random(`vx${i}`) * VW,
        y: random(`vy${i}`) * VH,
        r: 1 + random(`vr${i}`) * 2.2,
        a: 0.1 + random(`va${i}`) * 0.32,
        v: 2 + random(`vv${i}`) * 7,
        ph: random(`vp${i}`) * 6.28,
      })),
    []
  );
  return (
    <div style={{ position: "absolute", inset: 0, background: BG, opacity: amount, zIndex: 0 }}>
      <div style={{ position: "absolute", inset: 0, background: `radial-gradient(900px 900px at 40% 38%, ${tint(C.silver, 0.16)}, transparent 70%)` }} />
      <svg width={VW} height={VH} style={{ position: "absolute", inset: 0 }}>
        {dots.map((d, i) => (
          <circle key={i} cx={d.x + Math.sin(t / 6 + d.ph) * 22} cy={(((d.y - t * d.v) % VH) + VH) % VH} r={d.r} fill={tint(C.silverLight, d.a)} />
        ))}
      </svg>
    </div>
  );
};

// The speaker's mark sits in the top band: it is not text to read, so it is outside the zone
export const VMark: React.FC = () => (
  <div data-outside style={{ position: "absolute", left: SAFE.x0, top: 190, zIndex: 8, filter: "drop-shadow(0 4px 14px rgba(0,0,0,.6))" }}>
    <Logo size={46} />
  </div>
);

// The one frame that highlights a place on a screenshot. It comes from the design ("overlay.mark" in tokens.json).
export const MARK: string = TOKEN_MARK;

// Call to action (optional: without "cta" in spans.json there is none): an opaque curtain over the whole scene and a card in the safe zone. It appears CTA_LEAD seconds before the
// end of the speech and stays CTA_TAIL seconds after it. Its words come from "cta" in spans.json.
const APPEAR = 0.35;
export const VCta: React.FC<{ id: ClipId }> = ({ id }) => {
  const u = useCurrentFrame() / FPS;
  const from = ctaStart(id);
  if (!HAS_CTA || u < from) return null;
  const p = ease(u, from, APPEAR);
  const rows: [string, "lead" | "plain"][] = [[CTA.lead, "lead"], [CTA.before, "plain"]];
  return (
    <>
      <div data-cta style={{ position: "absolute", inset: 0, zIndex: 19, opacity: p, background: C.deep }} />
      <div data-cta-card style={{ position: "absolute", left: SAFE.x0, top: 500, width: SAFE.x1 - SAFE.x0, zIndex: 20, opacity: Math.min(p * 1.3, 1), transform: `translateY(${(1 - p) * 40}px) scale(${0.96 + 0.04 * p})` }}>
        <div style={{ borderRadius: R.block, background: C.card, boxShadow: `${RIM}, ${SHADOW}`, padding: "48px 44px", textAlign: "center" }}>
          {rows.map(([text, kind], i) =>
            text ? (
              <div key={i} style={{ marginTop: i ? 22 : 0, fontFamily: FONT.text, fontWeight: kind === "lead" ? 500 : 600, fontSize: 46, color: kind === "lead" ? C.muted : C.white }}>{text}</div>
            ) : null
          )}
          {CTA.word ? (
            <div style={{ marginTop: 18, display: "flex", justifyContent: "center" }}>
              <div style={{ padding: "18px 48px", borderRadius: R.pill, background: CHROME, fontFamily: FONT.display, fontWeight: 800, fontSize: 92, color: C.ink, boxShadow: `inset 0 1px 1px ${C.white}, 0 16px 40px rgba(0,0,0,.5)` }}>{CTA.word}</div>
            </div>
          ) : null}
          {CTA.after ? <div style={{ marginTop: 22, fontFamily: FONT.text, fontWeight: 600, fontSize: 46, color: C.white }}>{CTA.after}</div> : null}
        </div>
      </div>
    </>
  );
};

// The speaker's circle stays above the curtain while the speech goes on and is gone when it ends: in the silence only the card remains.
export const VCtaRing: React.FC<{ id: ClipId }> = ({ id }) => {
  const u = useCurrentFrame() / FPS;
  const from = ctaStart(id);
  const end = speechSeconds(id);
  if (!HAS_CTA || u < from || u >= end - 1 / FPS) return null;
  const alpha = Math.min(ease(u, from, APPEAR), Math.max(0, Math.min(1, (end - u) / 0.3)));
  return <VPresenter id={id} keys={[[0, "ringLow"]]} alpha={alpha} z={21} markers={false} />;
};

export const Big: React.FC<{ size?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ size = 92, style, children }) => (
  <Chrome size={size} style={style}>
    {children}
  </Chrome>
);
