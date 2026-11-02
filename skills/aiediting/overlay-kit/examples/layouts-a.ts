import { LayoutKey } from "./layout-types";

// Sample segment: a made-up talk about a weekly plan (examples/words.txt). A change sits at the start of a phrase;
// the last layout returns to "full" at the end of the segment.
export const LAYOUTS_A: readonly LayoutKey[] = [
  [5.0, "pip"], // "It has three steps": the map of steps, the speaker in the corner
  [13.7, "right"], // "Third, at the end of the week...": a card on the left, the speaker on the right
  [18.6, "left"], // "Here is how it looks in a real tool": a real screen on the right
  [24.7, "full"], // "That is all": the speaker fills the frame, small cards in the corners
];
