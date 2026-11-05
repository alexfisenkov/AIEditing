// Sample segment: four scenes on made-up content, showing the devices of the system.
// Time is seconds of the video; every appearance is bound to the word that causes it (see examples/words.txt).
// On-screen text belongs to the speaker's language and to what was said or what a real screen shows.
import React from "react";
import { Appear, At } from "../kit/Appear";
import { Glass, Pill, TextMark, Token } from "../kit/Cards";
import { Count, Link } from "../kit/Lines";
import { Cursor, Focus, Screen } from "../kit/Screen";
import { Cue } from "../kit/Sound";
import { Chrome, Eyebrow, H2, Lead } from "../kit/Type";
import { C, FONT, RIM } from "../kit/tokens";
import { ease, keys, useT } from "../kit/time";
import { Scene } from "./types";

// ───────── shared devices ─────────

const Txt: React.FC<{ size?: number; color?: string; weight?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({
  size = 28,
  color = C.white,
  weight = 600,
  style,
  children,
}) => <div style={{ fontFamily: FONT.text, fontSize: size, fontWeight: weight, color, lineHeight: 1.25, ...style }}>{children}</div>;

// Thin line icons, stroke 1.8, silver: never stock icons, never colour
const GLYPHS = {
  check: <path d="M5 12.5l4.5 4.5L19 7" />,
  spark: <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" />,
  board: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2.5" />
      <path d="M9 4v16M15 4v16" />
    </>
  ),
} as const;

const Ico: React.FC<{ g: keyof typeof GLYPHS; size?: number; color?: string; sw?: number }> = ({ g, size = 28, color = C.silver, sw = 1.8 }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" style={{ flex: "none" }}>
    {GLYPHS[g]}
  </svg>
);

// A soft dark scrim under text while the speaker fills the frame: readable on any background
const Scrim: React.FC<{ side: "left" | "right"; at: number; out: number; w?: number }> = ({ side, at, out, w = 820 }) => {
  const t = useT();
  const op = ease(t, at, 0.8) * (1 - ease(t, out, 0.5));
  if (op <= 0.01) return null;
  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        bottom: 0,
        [side]: 0,
        width: w,
        opacity: op,
        background: `linear-gradient(${side === "left" ? 90 : 270}deg,rgba(14,14,16,.62),rgba(14,14,16,.3) 60%,transparent)`,
      }}
    />
  );
};

// ───────── Scene 1 · 5.0-13.7 · three steps (speaker in the corner, a map on the stage) ─────────

type Step = { x: number; label: string; on: number };
const STEPS: readonly Step[] = [
  { x: 230, label: "Collect", on: 7.0 }, // "First, you collect..."
  { x: 740, label: "Pick three", on: 10.6 }, // "Second, you pick..."
  { x: 1250, label: "Check", on: 1e9 }, // lit by the next scene
];
const S1_END = 13.6;

const StepNode: React.FC<{ i: number }> = ({ i }) => {
  const t = useT();
  const s = STEPS[i];
  const next = i + 1 < STEPS.length ? STEPS[i + 1].on : 1e9;
  const state = t >= next ? 2 : t >= s.on ? 1 : 0; // 0 ahead, 1 now, 2 done
  const lit = state === 1 ? ease(t, s.on, 0.7) : 0;
  const pulse = state === 1 ? 1 + Math.sin(t * 3.2) * 0.025 : 1;
  const face: React.CSSProperties =
    state === 0
      ? { background: `linear-gradient(165deg,${C.graphiteSoft},${C.deep})`, boxShadow: RIM, color: C.muted }
      : { boxShadow: `inset 0 1px 1px #fff, 0 10px 26px rgba(0,0,0,.5), 0 0 0 ${7 * lit}px rgba(255,255,255,${0.15 * lit}), 0 0 ${46 * lit}px rgba(255,255,255,${0.42 * lit})` };
  return (
    <At x={s.x - 170} y={400} w={340} z={2}>
      <Appear at={5.6 + i * 0.35} out={S1_END}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", transform: `scale(${pulse})` }}>
          <Token size={128} style={face}>
            {state === 2 ? <Ico g="check" size={64} color={C.ink} sw={2.4} /> : i + 1}
          </Token>
          <Txt size={40} weight={state === 1 ? 700 : 600} color={state === 1 ? C.white : state === 2 ? C.muted : C.faint} style={{ marginTop: 20, textAlign: "center" }}>
            {s.label}
          </Txt>
        </div>
      </Appear>
    </At>
  );
};

const S1: React.FC = () => {
  const t = useT();
  return (
    <>
      <At x={90} y={130} w={1200}>
        <Appear at={5.2} out={S1_END}>
          <Eyebrow size={20}>Weekly plan</Eyebrow>
        </Appear>
        <Appear at={5.5} out={S1_END} style={{ marginTop: 18 }}>
          <Chrome size={96}>Three steps</Chrome>
        </Appear>
      </At>
      {STEPS.slice(0, -1).map((s, i) => (
        <Link key={i} at={5.9 + i * 0.35} out={S1_END} from={[s.x + 80, 464]} to={[STEPS[i + 1].x - 80, 464]} dur={0.7} pulse={t >= s.on} pulseEvery={2.2} />
      ))}
      {STEPS.map((_, i) => (
        <StepNode key={i} i={i} />
      ))}
      <At x={230 - 170} y={690} w={340}>
        <Appear at={8.44} out={S1_END} y={20}>
          <Pill size={32}>
            <Ico g="spark" size={32} />
            one place
          </Pill>
        </Appear>
      </At>
      <At x={740 - 150} y={690} w={300}>
        <Appear at={12.04} out={S1_END} y={20}>
          <Pill size={32}>only three</Pill>
        </Appear>
      </At>
    </>
  );
};

// ───────── Scene 2 · 13.7-18.6 · a card and a counter (speaker on the right) ─────────
// The stage is full when the layout change ends and the graphic stands in its middle: what the words bring later is already in place,
// and takes its detail on the word. A condition in the speech stays in the headline.

const S2: React.FC = () => (
  <>
    <At x={90} y={150} w={1000}>
      <Appear at={13.9} out={18.4}>
        <Glass at={13.9} pad={52} style={{ width: 1000 }}>
          <Eyebrow>Step 3</Eyebrow>
          <H2 size={72} style={{ marginTop: 20 }}>
            Check what is done
          </H2>
          <Lead size={42} style={{ marginTop: 22 }}>
            At the end of the week
          </Lead>
        </Glass>
      </Appear>
    </At>
    <At x={90} y={530} w={1000}>
      <Appear at={14.2} out={18.4} y={20}>
        <div style={{ display: "flex", alignItems: "center", gap: 34 }}>
          <Token size={170}>
            <Count at={16.7} to={3} dur={1.0} />
          </Token>
          <Txt size={64} weight={700}>
            of 3 done
          </Txt>
        </div>
      </Appear>
    </At>
    <At x={90} y={760} w={600}>
      <Appear at={17.76} out={18.4} y={20}>
        <Pill tone="ok" size={36}>
          <Ico g="check" size={32} color={C.white} sw={2.4} />
          Done
        </Pill>
      </Appear>
    </At>
  </>
);

// ───────── Scene 3 · 18.6-24.7 · a real screen with a cursor and a highlight (speaker on the left) ─────────

const ZOOM = 1.1; // window width 1060 / 1600 css px, times zoom
const LEFT = 150; // css px of the page hidden at the left edge of the window
const SC = (1060 / 1600) * ZOOM;
const SCROLL: readonly (readonly [number, number])[] = [[19.0, 0], [21.5, 0], [23.0, 300], [24.6, 300]];

const S3Screen: React.FC = () => {
  const t = useT();
  const row = (pageY: number) => (pageY - keys(t, SCROLL)) * SC; // page y -> y in the window's content area
  return (
    <Screen name="demo" dark w={1060} h={776} at={19.0} out={24.5} zoom={ZOOM} left={LEFT} scroll={SCROLL} rotateY={-4}>
      <Focus at={20.2} out={22.8} x={(360 - LEFT) * SC} y={row(200)} w={1200 * SC} h={160 * SC} r={14} />
      <Cursor
        path={[[19.4, 800, 500], [20.6, (1400 - LEFT) * SC, row(200) + 28 * SC], [23.4, (1400 - LEFT) * SC, row(580) + 28 * SC]]}
        clicks={[20.7, 23.64]}
      />
    </Screen>
  );
};

const S3: React.FC = () => (
  <>
    <At x={800} y={84} w={1000}>
      <Appear at={19.0} out={24.5}>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <Token size={64}>
            <Ico g="board" size={34} color={C.ink} sw={2} />
          </Token>
          <H2 size={60}>The board</H2>
        </div>
      </Appear>
    </At>
    <At x={800} y={172}>
      <S3Screen />
    </At>
  </>
);

// ───────── Scene 4 · 24.7-28 · the speaker fills the frame, small cards in the corners ─────────

const S4: React.FC = () => (
  <>
    <Scrim side="left" at={24.9} out={27.6} w={760} />
    <At x={90} y={700} w={640}>
      <Appear at={25.0} out={27.7}>
        <Glass at={25.0} pad={32}>
          <Eyebrow>This week</Eyebrow>
          <H2 size={40} style={{ marginTop: 14 }}>
            Try it
          </H2>
        </Glass>
      </Appear>
    </At>
    <At x={1380} y={150}>
      <Appear at={26.2} out={27.7} x={30} y={0}>
        <TextMark size={96}>3</TextMark>
      </Appear>
    </At>
  </>
);

// ───────── registry ─────────

export const scenes: Scene[] = [
  { from: 5.0, to: 13.7, C: S1 },
  { from: 13.7, to: 18.6, C: S2 },
  { from: 18.6, to: 24.7, C: S3 },
  { from: 24.7, to: 28.0, C: S4 },
];

// Sound: one event, one sound, for the whole video. A layout change is whoosh-soft; leaving and zooming are silent.
export const cues: Cue[] = [
  [5.0, "whoosh-soft"], [5.2, "switch"], [7.0, "tick"], [8.44, "pop-soft"], [10.6, "tick"], [12.04, "pop-soft"],
  [13.7, "whoosh-soft"], [13.9, "mouse-click"], [16.7, "tick"], [17.76, "ding"],
  [18.6, "whoosh-soft"], [19.0, "shutter-modern"], [20.7, "mouse-click"], [23.64, "mouse-click"],
  [24.7, "whoosh-soft"], [25.0, "switch"],
];
