// Vertical clips: every composition is one clip. The picture is rendered here; the sound is mixed afterwards from the clean
// speech (`overlay.py vertical-final`), so the composition is silent.
import React from "react";
import { AbsoluteFill, Composition, continueRender, delayRender, staticFile } from "remotion";
import design from "../data/design.json";
import { setFrameMap, useT } from "../kit/time";
import { C } from "../kit/tokens";
import { ClipId, SPANS, durationFrames, FPS, frameToNewTime } from "./clips";
import { CLIPS } from "./index-clips";
import { VH, VW } from "./safe";
import { SafeAudit, VCta, VCtaRing, VMark, VStage } from "./VKit";
import { stageShare, VPresenter } from "./VPresenter";

// @font-face rules come from design.json (written by `overlay.py prepare` from the design's tokens.json)
type FontFace = { family: string; src: string; format: string; weight: string; range: string | null };
const FONTS = (design.fonts as FontFace[])
  .map(
    (f) =>
      `@font-face{font-family:'${f.family}';src:url('${staticFile(f.src)}') format('${f.format}');font-weight:${f.weight};${
        f.range ? `unicode-range:${f.range};` : ""
      }}`
  )
  .join("\n");

const useFonts = () => {
  const [handle] = React.useState(() => delayRender("fonts"));
  React.useEffect(() => {
    const { display, text, mono } = design.families;
    Promise.all(
      [`700 40px '${display}'`, `800 40px '${display}'`, `600 30px '${text}'`, `500 30px '${text}'`, `400 20px '${mono}'`].map((f) =>
        document.fonts.load(f, "Az\u042F")
      )
    )
      .catch((e) => console.warn("font not loaded", e))
      .then(() => continueRender(handle));
  }, [handle]);
};

const Clip: React.FC<{ id: ClipId; audit: boolean }> = ({ id, audit }) => {
  setFrameMap(frameToNewTime(id));
  useFonts();
  const t = useT();
  const { keys, scenes } = CLIPS[id];
  return (
    <AbsoluteFill style={{ background: C.deep }}>
      <style>{FONTS}</style>
      <VStage amount={stageShare(keys, t)} />
      <VPresenter id={id} keys={keys} />
      <SafeAudit on={audit}>
        <div style={{ position: "absolute", inset: 0, zIndex: 5 }}>
          {scenes
            .filter((s) => t >= s.from && t < s.to)
            .map((s) => (
              <AbsoluteFill key={s.from}>
                <s.C />
              </AbsoluteFill>
            ))}
        </div>
        <VCta id={id} />
      </SafeAudit>
      <VCtaRing id={id} />
      <VMark />
    </AbsoluteFill>
  );
};

// A scene file without an entry in spans.json (or the other way round) is reported by `vertical-check`, not drawn
export const VRoot: React.FC = () => (
  <>
    {Object.keys(CLIPS)
      .filter((id) => SPANS[id])
      .map((id) => (
        <Composition key={id} id={id} component={Clip as React.FC<any>} durationInFrames={durationFrames(id)} fps={FPS} width={VW} height={VH} defaultProps={{ id, audit: false }} />
      ))}
  </>
);
