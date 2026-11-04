// The frame check of one vertical clip: renders the frames asked for with the audit switched on and writes down what the
// audit found. `overlay.py vertical-check` runs it; run by hand only to look into a finding.
//   node tools-local/vertical-frames.mjs <bundle dir> <out dir> <clip> <step seconds> [from second] [to second]
// <out dir>/<clip>/frames/f-<frame>.jpeg   the frames; the name carries the real frame number of the clip
// <out dir>/<clip>/frames.json             fps, step, the frames asked for
// <out dir>/<clip>/findings.txt, findings.json   what the audit found, as ranges of seconds
import { ensureBrowser, renderFrames, selectComposition } from "@remotion/renderer";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const [bundle, outRoot, id, stepArg = "0.1667", fromArg, toArg] = process.argv.slice(2);
if (!bundle || !outRoot || !id) {
  console.error("usage: vertical-frames.mjs <bundle dir> <out dir> <clip> <step seconds> [from] [to]");
  process.exit(2);
}
const browserExecutable = process.env.OVERLAY_BROWSER || null;
if (!browserExecutable) await ensureBrowser();
const dir = path.join(outRoot, id);
const framesDir = path.join(dir, "frames");
rmSync(framesDir, { recursive: true, force: true });
mkdirSync(framesDir, { recursive: true });

const inputProps = { id, audit: true };
const composition = await selectComposition({ serveUrl: bundle, id, inputProps, logLevel: "error", browserExecutable, timeoutInMilliseconds: 120000 });
const fps = composition.fps;
const nth = Math.max(1, Math.round(Number(stepArg) * fps));
const first = fromArg ? Math.round(Number(fromArg) * fps) : 0;
const last = Math.min(toArg ? Math.round(Number(toArg) * fps) : composition.durationInFrames - 1, composition.durationInFrames - 1);
const frames = [];
for (let f = first; f <= last; f += nth) frames.push(f);

// Short blank stretches are normal (a scene changes): only a circle bare longer than 0.7 s or a band bare longer than 1.5 s counts
const LONG_BLANK = { "ПУСТО кружок": 0.7, "ПУСТО полоса": 1.5 };
const seen = new Map(); // finding -> frames it was seen at
await renderFrames({
  composition,
  serveUrl: bundle,
  inputProps,
  outputDir: framesDir,
  imageFormat: "jpeg",
  jpegQuality: 75,
  frames,
  imageSequencePattern: "f-[frame].[ext]",
  concurrency: Math.max(1, Math.min(8, os.cpus().length - 1)),
  logLevel: "error",
  browserExecutable,
  timeoutInMilliseconds: 120000,
  onStart: () => {},
  onFrameUpdate: () => {},
  onBrowserLog: (log) => {
    if (!log.text.startsWith("SAFE ")) return;
    const [head, ...items] = log.text.slice(5).split("|");
    const frame = Number(head);
    for (const item of items) seen.set(item, [...(seen.get(item) ?? []), frame]);
  },
});

// Ranges of consecutive sampled frames, each finding on its own
const rows = [];
for (const [item, list] of seen) {
  const sorted = [...new Set(list)].sort((x, y) => x - y);
  let start = sorted[0];
  for (let i = 0; i < sorted.length; i++) {
    if (i + 1 < sorted.length && sorted[i + 1] - sorted[i] <= nth * 1.5) continue;
    const from = start / fps;
    const to = (sorted[i] + nth) / fps; // a finding lasts until the next sampled frame
    if (!(item in LONG_BLANK) || to - from > LONG_BLANK[item]) rows.push({ item, from, to: Math.min(to, composition.durationInFrames / fps) });
    start = sorted[i + 1];
  }
}
rows.sort((x, y) => x.from - y.from);
const text = rows.map((r) => `${r.from.toFixed(1)}–${r.to.toFixed(1)} с: ${r.item}`);
writeFileSync(path.join(dir, "findings.txt"), text.join("\n") + (text.length ? "\n" : ""));
writeFileSync(path.join(dir, "findings.json"), JSON.stringify(rows, null, 1));
writeFileSync(path.join(dir, "frames.json"), JSON.stringify({ id, fps, step: nth / fps, frames }, null, 1));
console.log(`${id}: frames ${frames.length}, findings ${rows.length}`);
