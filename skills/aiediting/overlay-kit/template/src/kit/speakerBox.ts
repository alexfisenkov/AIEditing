// The speaker's window, told to the face check (`overlay.py face --check`, `vertical-check`) through the browser console.
// Only a render asked for it (input prop faceProbe) prints anything: an ordinary render and the Studio stay silent.
import { useLayoutEffect } from "react";
import { getInputProps, useCurrentFrame } from "remotion";

// Where the speaker's video is on the frame: a box with a corner radius (a circle when the radius is half the box), and
// how visible the layer is. Pixels of the composition.
export type SpeakerBox = { x: number; y: number; w: number; h: number; r: number; shown: number };

export const useSpeakerBox = (box: SpeakerBox, on = true) => {
  const frame = useCurrentFrame();
  useLayoutEffect(() => {
    if (!on || !(getInputProps() as { faceProbe?: boolean }).faceProbe) return;
    const values = [box.x, box.y, box.w, box.h, box.r, box.shown].map((v) => v.toFixed(2));
    console.log(`FACEBOX ${frame}|${values.join("|")}`);
  });
};
