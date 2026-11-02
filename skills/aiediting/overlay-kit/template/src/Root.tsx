import React from "react";
import { AbsoluteFill, Composition, continueRender, delayRender, staticFile } from "remotion";
import design from "./data/design.json";
import { Frame } from "./kit/Chrome";
import { Presenter, stageAmount } from "./kit/Presenter";
import { SoundTrack } from "./kit/Sound";
import { Stage } from "./kit/Stage";
import { useT } from "./kit/time";
import { C, FPS, H, W } from "./kit/tokens";
import { DURATION } from "./data/layouts";
import { ALL_CUES, SCENES } from "./scenes";

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
      [`700 40px '${display}'`, `500 40px '${display}'`, `600 30px '${text}'`, `500 30px '${text}'`, `400 20px '${mono}'`].map((f) =>
        // Latin + Cyrillic sample, so both unicode-range faces of a family are loaded before the first frame
        document.fonts.load(f, "Az\u042F")
      )
    )
      .catch((e) => console.warn("font not loaded", e)) // a broken font file falls back; it must not stall the render
      .then(() => continueRender(handle));
  }, [handle]);
};

const Full: React.FC = () => {
  useFonts();
  const t = useT();
  return (
    <AbsoluteFill style={{ background: C.deep }}>
      <style>{FONTS}</style>
      <Stage amount={stageAmount(t)} />
      <Presenter />
      {SCENES.filter((s) => t >= s.from && t < s.to).map((s, i) => (
        <AbsoluteFill key={`${s.from}-${i}`}>
          <s.C />
        </AbsoluteFill>
      ))}
      <Frame />
      <SoundTrack cues={ALL_CUES} />
    </AbsoluteFill>
  );
};

export const Root: React.FC = () => (
  <Composition id="Full" component={Full} durationInFrames={Math.round(DURATION * FPS)} fps={FPS} width={W} height={H} />
);
