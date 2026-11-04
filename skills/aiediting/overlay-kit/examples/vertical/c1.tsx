// Sample vertical clip on made-up content: three scenes, one per layout of the speaker.
// Time is scene seconds: the seconds of the long video's scenes (the seconds of raw/words.txt when the folder has no time map). Frame 1080x1920.
// Rules of the frame: text only inside the safe zone (safe.ts); a caption beside the speaker only in `top` and `low`;
// `full` and `close` carry no text; nothing lies on anything else; a scene leaves 0.3 s before the next one arrives;
// the last caption stands before the call to action comes (it comes `cta_lead` seconds before the speech ends).
import React from "react";
import { Appear, At } from "../kit/Appear";
import { Glass, Pill } from "../kit/Cards";
import { Chrome, Eyebrow, H2, Lead } from "../kit/Type";
import { VKey } from "./VPresenter";

export const keys: readonly VKey[] = [
  [0, "low"], // the hook: text above, the speaker below, the face stays free
  [3.0, "ringLow"], // a card over the whole zone, the speaker is a circle at the bottom
  [6.0, "top"], // the speaker above, one more line below him
];

const Hook: React.FC = () => (
  <At x={70} y={360} w={870}>
    <Appear at={0.2} out={2.6} y={24} dur={0.6} blur={0}>
      <Chrome size={84} weight={800} style={{ lineHeight: 1.1 }}>
        A short headline that says the point
      </Chrome>
    </Appear>
  </At>
);

const POINTS = ["First point", "Second point", "Third point"];
const Card: React.FC = () => (
  <At x={70} y={330} w={870}>
    <Appear at={3.1} out={5.5} y={30} dur={0.6} blur={0}>
      <Glass pad={40}>
        <Eyebrow size={34}>Example</Eyebrow>
        <H2 size={56} style={{ marginTop: 18 }}>
          Three things to keep
        </H2>
        <div style={{ marginTop: 34, display: "flex", flexDirection: "column", gap: 22, alignItems: "flex-start" }}>
          {POINTS.map((p, i) => (
            <Appear key={p} at={3.5 + i * 0.5} out={5.5} y={16} dur={0.5} blur={0}>
              <Pill size={38}>{p}</Pill>
            </Appear>
          ))}
        </div>
      </Glass>
    </Appear>
  </At>
);

const Line: React.FC = () => (
  <At x={70} y={935} w={870}>
    <Appear at={6.3} y={20} dur={0.5} blur={0}>
      <Lead size={44}>One more line under the speaker</Lead>
    </Appear>
    <Appear at={6.8} y={20} dur={0.5} blur={0} style={{ marginTop: 28 }}>
      <Pill size={40} tone="light">
        and the last caption
      </Pill>
    </Appear>
  </At>
);

export const c1 = {
  keys,
  scenes: [
    { from: 0, to: 3.2, C: Hook },
    { from: 3.0, to: 6.1, C: Card },
    { from: 6.0, to: 12.5, C: Line },
  ],
};
