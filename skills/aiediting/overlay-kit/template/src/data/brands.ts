// Monochrome service logos as SVG path data (24x24 viewBox) in brands.json.
// The kit ships none: brand marks are trademarks, and a licence for each one is not confirmed.
// Add the ones the speaker names:  node tools/add-logos.mjs "<W>" claude telegram
// (pulls the path from the simple-icons npm package; check the brand's guidelines before you publish).
import raw from "./brands.json";

export const BRANDS: Record<string, string> = raw;
export type BrandName = string;
